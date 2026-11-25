"""
AIS 2.6f — Ground Truth Certification API Router

Provides dedicated, strictly blind endpoints for Human Ground Truth Certification
inside `/api/ground-truth` without contaminating Operational Human Review Queues or
AI Training Memory (`LearningRecord` / RAG).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_admin, require_analyst
from app.database import get_db
from app.models.user import User
from app.schemas.ground_truth import (
    AdditionalEvidenceInput,
    CohortSummaryResponse,
    GroundTruthAdjudicateRequest,
    GroundTruthDetailResponse,
    GroundTruthQueueResponse,
    GroundTruthReopenRequest,
    GroundTruthReviewSubmitRequest,
)
from app.services.blind_review_guard import FROZEN_AIS_2_6E_COHORT_ID
from app.services.ground_truth_certification_service import GroundTruthCertificationService

router = APIRouter(prefix="/ground-truth", tags=["Ground Truth Certification"])


@router.get("/cohorts", response_model=List[CohortSummaryResponse])
async def list_benchmark_cohorts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await GroundTruthCertificationService.list_cohorts(db, current_user)


@router.post("/cohorts/{cohort_key}/ensure", response_model=CohortSummaryResponse)
async def ensure_benchmark_cohort(
    cohort_key: str = FROZEN_AIS_2_6E_COHORT_ID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if cohort_key != FROZEN_AIS_2_6E_COHORT_ID:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_key} is not configured for auto-seeding.")
    await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db)
    cohorts = await GroundTruthCertificationService.list_cohorts(db, current_user)
    for c in cohorts:
        if c.cohort_key == cohort_key:
            return c
    raise HTTPException(status_code=404, detail=f"Cohort {cohort_key} not found.")


@router.get("/cohorts/{cohort_key}/queue", response_model=GroundTruthQueueResponse)
async def get_ground_truth_cohort_queue(
    cohort_key: str,
    priority_only: Optional[bool] = Query(None),
    certification_status: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    exposure_risk_only: Optional[bool] = Query(None),
    my_pending_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return await GroundTruthCertificationService.get_cohort_queue(
            db=db,
            cohort_key=cohort_key,
            current_user=current_user,
            priority_only=priority_only,
            certification_status=certification_status,
            vendor=vendor,
            customer=customer,
            exposure_risk_only=exposure_risk_only,
            my_pending_only=my_pending_only,
            search=search,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get(
    "/cohorts/{cohort_key}/incidents/{incident_id}",
    response_model=GroundTruthDetailResponse,
)
async def get_ground_truth_incident_detail(
    cohort_key: str,
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return await GroundTruthCertificationService.get_incident_detail(
            db=db,
            cohort_key=cohort_key,
            incident_identifier=incident_id,
            current_user=current_user,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/cohorts/{cohort_key}/incidents/{incident_id}/evidence", response_model=Dict[str, Any])
async def attach_ground_truth_evidence(
    cohort_key: str,
    incident_id: str,
    req: AdditionalEvidenceInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    try:
        return await GroundTruthCertificationService.attach_additional_evidence(
            db=db,
            cohort_key=cohort_key,
            incident_identifier=incident_id,
            req=req,
            current_user=current_user,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/cohorts/{cohort_key}/incidents/{incident_id}/review", response_model=Dict[str, Any])
async def submit_ground_truth_review(
    cohort_key: str,
    incident_id: str,
    req: GroundTruthReviewSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    try:
        return await GroundTruthCertificationService.submit_or_save_review(
            db=db,
            cohort_key=cohort_key,
            incident_identifier=incident_id,
            req=req,
            current_user=current_user,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/cohorts/{cohort_key}/incidents/{incident_id}/adjudicate", response_model=Dict[str, Any])
async def adjudicate_ground_truth_conflict(
    cohort_key: str,
    incident_id: str,
    req: GroundTruthAdjudicateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await GroundTruthCertificationService.adjudicate_conflict(
            db=db,
            cohort_key=cohort_key,
            incident_identifier=incident_id,
            req=req,
            current_user=current_user,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/cohorts/{cohort_key}/reviews/reopen", response_model=Dict[str, Any])
async def reopen_ground_truth_review(
    cohort_key: str,
    req: GroundTruthReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await GroundTruthCertificationService.reopen_and_revise_review(
            db=db,
            cohort_key=cohort_key,
            req=req,
            current_user=current_user,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get(
    "/cohorts/{cohort_key}/incidents/{incident_id}/post-certification-comparison",
    response_model=Dict[str, Any],
)
async def get_post_certification_comparison(
    cohort_key: str,
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await GroundTruthCertificationService.get_post_certification_comparison(
            db=db,
            cohort_key=cohort_key,
            incident_identifier=incident_id,
            current_user=current_user,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/cohorts/{cohort_key}/audit", response_model=Dict[str, Any])
async def get_ground_truth_audit(
    cohort_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return await GroundTruthCertificationService.get_audit_readiness(
            db=db, cohort_key=cohort_key, current_user=current_user
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
