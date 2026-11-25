"""
FastAPI Route Handlers for AIS 2.0 AI Evaluation Tracking & Controlled Inference.
Provides:
- GET /api/ais/rules/{rule_uuid}/evaluation-status
- GET /api/ais/incidents/{incident_id}/evaluation-history
- POST /api/ais/rules/{rule_uuid}/evaluate-missing-batch
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.api.deps import get_current_active_user, require_admin, require_analyst
from app.models.user import User
from app.services.ais_evaluation_service import AisEvaluationService
from app.services.ai_verdict_service import LocalLLMUnavailableError

logger = logging.getLogger("ai_verdict.api.ais_evaluation")

router = APIRouter(prefix="/ais", tags=["AIS 2.0 AI Evaluation Tracking"])


class EvaluateMissingBatchRequest(BaseModel):
    version_id: Optional[str] = Field(None, description="Optional target policy version ID")
    version_number: Optional[int] = Field(None, description="Optional target policy version number")
    customer: Optional[str] = Field(None, description="Optional tenant scope")
    incident_ids: Optional[List[str]] = Field(None, description="Optional explicit incident IDs to evaluate")
    max_concurrency: int = Field(2, ge=1, le=4, description="Maximum concurrent inference requests")
    confirm_execution: bool = Field(False, description="Must be true to execute real GPU inference")


@router.get("/rules/{rule_uuid}/evaluation-status", response_model=Dict[str, Any])
async def get_rule_evaluation_status(
    rule_uuid: str,
    policy_version_id: Optional[str] = Query(None, description="Target policy version UUID"),
    policy_version_number: Optional[int] = Query(None, description="Target policy version number"),
    version_id: Optional[str] = Query(None, description="Alias for policy_version_id"),
    version_number: Optional[int] = Query(None, description="Alias for policy_version_number"),
    customer: Optional[str] = Query(None, description="Customer tenant filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by canonical status"),
    search: Optional[str] = Query(None, description="Search query by incident ID or title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Page size"),
    blind_review: bool = Query(False, description="Enforce blind masking of AI verdicts for reviewers"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Authoritative evaluation status endpoint for a rule population.
    Computes canonical status from durable stored execution records under the selected policy version.
    Enforces server-side tenant isolation and double-blind masking for unreviewed incidents.
    """
    target_v_id = policy_version_id or version_id
    target_v_num = policy_version_number if policy_version_number is not None else version_number
    user_role = getattr(current_user, "role", "")
    is_admin_user = user_role in ("Administrator", "SuperAdmin", "SOC_Manager") or getattr(current_user, "is_superuser", False)

    if is_admin_user:
        target_customer = customer if (customer and customer.upper() not in ("ALL", "GLOBAL", "DEFAULT", "")) else None
    else:
        target_customer = getattr(current_user, "customer", None) or customer or "DEFAULT"

    try:
        res = await AisEvaluationService.get_rule_evaluation_tracking_overview(
            db=db,
            rule_uuid=rule_uuid,
            customer=target_customer,
            version_id=target_v_id,
            version_number=target_v_num,
            status_filter=status_filter,
            search_query=search,
            page=page,
            page_size=page_size,
            current_user=current_user,
            blind_review=blind_review,
        )
        return res
    except ValueError as ve:
        err = str(ve)
        if "not found" in err.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    except Exception as exc:
        logger.error(f"Failed to get evaluation status for rule {rule_uuid}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve evaluation tracking data: {str(exc)}"
        )


@router.get("/incidents/{incident_id}/evaluation-history", response_model=Dict[str, Any])
async def get_incident_evaluation_history(
    incident_id: str,
    blind_review: bool = Query(False, description="Enforce blind masking of AI verdict history"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves full chronological history of all AI evaluation attempts across all policy versions
    for an incident. Masks sensitive AI verdict details for pending blind analysts.
    """
    try:
        res = await AisEvaluationService.get_incident_evaluation_history(
            db=db,
            incident_id=incident_id,
            current_user=current_user,
            blind_review=blind_review,
        )
        return res
    except ValueError as ve:
        err = str(ve)
        if "not found" in err.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)
        if "access denied" in err.lower() or "tenant" in err.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    except Exception as exc:
        logger.error(f"Failed to get evaluation history for incident {incident_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve evaluation history: {str(exc)}"
        )


@router.post("/rules/{rule_uuid}/evaluate-missing-batch", response_model=Dict[str, Any])
async def evaluate_missing_incidents_batch(
    rule_uuid: str,
    payload: Optional[EvaluateMissingBatchRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Administrator-only: Orchestrates controlled, explicitly confirmed inference batch
    for incidents currently lacking AI evaluation under the selected policy version.
    """
    req = payload or EvaluateMissingBatchRequest()
    target_customer = req.customer or getattr(current_user, "customer", "DEFAULT") or "DEFAULT"

    try:
        res = await AisEvaluationService.execute_controlled_missing_batch(
            db=db,
            rule_uuid=rule_uuid,
            customer=target_customer,
            version_id=req.version_id,
            version_number=req.version_number,
            selected_incident_ids=req.incident_ids,
            max_concurrency=req.max_concurrency,
            confirm_execution=req.confirm_execution,
            admin_user=current_user,
        )
        return res
    except LocalLLMUnavailableError as llm_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Server 2 Local LLM is offline or unreachable: {str(llm_err)}"
        )
    except ValueError as ve:
        err = str(ve)
        if "not found" in err.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    except Exception as exc:
        logger.error(f"Controlled missing batch failed for rule {rule_uuid}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Controlled inference batch failed: {str(exc)}"
        )
