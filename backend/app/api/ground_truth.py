"""
AIS 2.6f — Ground Truth Certification API Router

Provides dedicated, strictly blind endpoints for Human Ground Truth Certification
inside `/api/ground-truth` without contaminating Operational Human Review Queues or
AI Training Memory (`LearningRecord` / RAG).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
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
    GroundTruthUnlockRequest,
)
from app.services.blind_review_guard import AIS_3_0_HOLDOUT_COHORT_ID, FROZEN_AIS_2_6E_COHORT_ID
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
    if cohort_key == FROZEN_AIS_2_6E_COHORT_ID:
        await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db)
    elif cohort_key == AIS_3_0_HOLDOUT_COHORT_ID:
        await GroundTruthCertificationService.ensure_ais_3_0_holdout_cohort(db)
    else:
        raise HTTPException(status_code=404, detail=f"Cohort {cohort_key} is not configured for auto-seeding.")
    cohorts = await GroundTruthCertificationService.list_cohorts(db, current_user)
    for c in cohorts:
        if c.cohort_key == cohort_key:
            return c
    raise HTTPException(status_code=404, detail=f"Cohort {cohort_key} not found.")


@router.get("/holdout-readiness", response_model=Dict[str, Any])
async def get_holdout_readiness(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns GT-2/GT-3 certification progress and AIS 3.0 multi-rule holdout preparation summary."""
    return await GroundTruthCertificationService.get_holdout_eligibility_summary(db, current_user)


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


# =========================================================================
# AIS 3.1: FROZEN HOLDOUT MANIFEST, TOKEN AUDIT, CHECKPOINTED RUNNER & EVALUATION
# =========================================================================

@router.get("/ais31/cohorts/{cohort_key}/manifest", response_model=Dict[str, Any])
async def ais31_get_frozen_manifest(
    cohort_key: str,
    include_ground_truth: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: builds immutable versioned manifest for a frozen cohort."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.build_frozen_manifest(
            db=db, cohort_key=cohort_key, include_ground_truth=include_ground_truth
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/cohorts/{cohort_key}/token-audit", response_model=Dict[str, Any])
async def ais31_audit_token_budgets(
    cohort_key: str,
    max_context_tokens: int = Query(8192, ge=1024, le=131072),
    max_completion_tokens: int = Query(768, ge=64, le=4096),
    target_input_budget: int = Query(7424, ge=512, le=65536),
    verify_remote_tokenize: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: verifies wire token budget & evidence completeness across all cohort members."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.audit_token_budgets(
            db=db,
            cohort_key=cohort_key,
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
            verify_remote_tokenize=verify_remote_tokenize,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/ais31/cohorts/{cohort_key}/runs", response_model=Dict[str, Any])
async def ais31_execute_benchmark_step(
    cohort_key: str,
    run_type: str = Query("FULL_HOLDOUT_100", pattern="^(PILOT_5|FULL_HOLDOUT_100|CUSTOM)$"),
    run_key: Optional[str] = Query(None),
    batch_size: int = Query(5, ge=1, le=20),
    offset: int = Query(0, ge=0),
    incident_ids: Optional[str] = Query(None, description="Comma-separated FortiSIEM IDs"),
    max_context_tokens: int = Query(8192, ge=1024, le=131072),
    max_completion_tokens: int = Query(768, ge=64, le=4096),
    target_input_budget: int = Query(7424, ge=512, le=65536),
    timeout_seconds: float = Query(180.0, ge=10.0, le=300.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Administrator-only: creates or idempotently resumes an AIS 3.1 live GPU benchmark run,
    processing up to `batch_size` pending incidents per request to avoid reverse-proxy timeouts.
    """
    from app.models.analyst_feedback import BenchmarkCohort, BenchmarkCohortItem
    from app.models.ais31_benchmark import AIS31BenchmarkResult
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        run = await AIS31BenchmarkService.create_or_resume_run(
            db=db,
            cohort_key=cohort_key,
            run_type=run_type,
            created_by_user=current_user.username,
            run_key=run_key,
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except RuntimeError as re_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re_err))

    if incident_ids:
        target_fids = [x.strip() for x in incident_ids.split(",") if x.strip()]
    else:
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one()
        all_items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()
        done_fids = {
            row[0]
            for row in (
                await db.execute(
                    select(AIS31BenchmarkResult.fortisiem_incident_id).where(
                        AIS31BenchmarkResult.run_id == run.id,
                        AIS31BenchmarkResult.execution_status.in_(["COMPLETED", "QUARANTINED"]),
                    )
                )
            ).all()
        }
        pending_fids = [it.fortisiem_incident_id for it in all_items if it.fortisiem_incident_id not in done_fids]
        target_fids = pending_fids[offset : offset + batch_size]

    return await AIS31BenchmarkService.execute_run(
        db=db,
        run_id=run.id,
        target_fids=target_fids,
        timeout_seconds=timeout_seconds,
    )


@router.get("/ais31/runs/{run_id}/evaluate", response_model=Dict[str, Any])
async def ais31_evaluate_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: post-run comparison against locked human ground truth."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.evaluate_run_against_ground_truth(db=db, run_id=run_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/runs/{run_id}/wire-prompt/{incident_id}", response_model=Dict[str, Any])
async def ais31_get_wire_prompt(
    run_id: str,
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: returns exact outbound wire prompt & raw vLLM response for an executed benchmark item."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.get_wire_prompt_capture(
            db=db, run_id=run_id, fortisiem_incident_id=incident_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/latest-summary", response_model=Dict[str, Any])
async def ais31_get_latest_cohort_summary(
    cohort_key: str = Query("AIS_3_0_INDEPENDENT_HOLDOUT_100"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns non-leaky aggregate benchmark status & metrics for the latest completed/partial run."""
    from app.models.ais31_benchmark import AIS31BenchmarkRun
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    latest = (
        await db.execute(
            select(AIS31BenchmarkRun)
            .where(AIS31BenchmarkRun.cohort_key == cohort_key)
            .order_by(AIS31BenchmarkRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not latest:
        return {"has_run": False, "cohort_key": cohort_key}

    eval_data = await AIS31BenchmarkService.evaluate_run_against_ground_truth(db=db, run_id=latest.id)
    return {
        "has_run": True,
        "run_id": latest.id,
        "run_key": latest.run_key,
        "run_type": latest.run_type,
        "status": latest.status,
        "benchmark_grade": latest.benchmark_grade,
        "expected_model": latest.expected_model,
        "actual_model_returned": latest.actual_model_returned,
        "raw_llm_metrics": eval_data["raw_llm_metrics"],
        "application_metrics": eval_data["application_metrics"],
        "subpopulations": eval_data["subpopulations"],
        "validator_telemetry": eval_data["validator_telemetry"],
        "baselines": eval_data["baselines"],
    }


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


@router.post("/cohorts/{cohort_key}/incidents/{incident_id}/review/unlock", response_model=Dict[str, Any])
async def unlock_ground_truth_review(
    cohort_key: str,
    incident_id: str,
    req: GroundTruthUnlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    try:
        return await GroundTruthCertificationService.unlock_review(
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


@router.get("/ais27/runtime-verify", response_model=Dict[str, Any])
async def ais27_verify_gpu_runtime(
    current_user: User = Depends(require_admin),
):
    """Administrator-only: probes Server 2 vLLM metadata endpoints (zero inference)."""
    from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner

    return await AIS27BenchmarkRunner.verify_gpu_runtime()


@router.post("/ais27/tokenize-verify", response_model=Dict[str, Any])
async def ais27_verify_tokenize(
    timeout_seconds: float = Query(10.0, ge=2.0, le=60.0),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: verifies Server 2 /tokenize endpoint across small, medium, and near-limit payloads."""
    from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner

    return await AIS27BenchmarkRunner.verify_tokenize(timeout_seconds=timeout_seconds)


@router.post("/ais27/smoke-test", response_model=Dict[str, Any])
async def ais27_run_smoke_test(
    timeout_seconds: float = Query(90.0, ge=5.0, le=120.0),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: dispatches 1 controlled non-benchmark connectivity smoke test."""
    from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner

    return await AIS27BenchmarkRunner.run_smoke_test(timeout_seconds=timeout_seconds)


@router.post("/ais27/cohorts/{cohort_key}/incidents/{incident_id}/run", response_model=Dict[str, Any])
async def ais27_run_single_incident(
    cohort_key: str,
    incident_id: str,
    mode: str = Query("ALL", pattern="^(ALL|A|B)$"),
    max_context_tokens: int = Query(8192, ge=1024, le=131072),
    max_completion_tokens: int = Query(768, ge=64, le=4096),
    target_input_budget: int = Query(7424, ge=512, le=65536),
    timeout_seconds: float = Query(180.0, ge=5.0, le=300.0),
    temperature: float = Query(0.0, ge=0.0, le=1.0),
    neutral_prompt_version: str = Query("V2", pattern="^(V1|V2)$"),
    include_complete_rule_def: bool = Query(True),
    include_evidence_intelligence: bool = Query(True),
    use_candidate_policy: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Administrator-only: executes isolated Mode A + Mode B live GPU inference and Mode C
    deterministic validation for a single frozen cohort incident without mutating DB state
    or accessing ground truth labels.
    """
    from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner

    try:
        return await AIS27BenchmarkRunner.run_single_incident_three_mode(
            db=db,
            cohort_key=cohort_key,
            fortisiem_incident_id=incident_id,
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            mode=mode,
            neutral_prompt_version=neutral_prompt_version,
            include_complete_rule_def=include_complete_rule_def,
            include_evidence_intelligence=include_evidence_intelligence,
            use_candidate_policy=use_candidate_policy,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# =========================================================================
# AIS 3.1: FROZEN HOLDOUT MANIFEST, TOKEN AUDIT, CHECKPOINTED RUNNER & EVALUATION
# =========================================================================

@router.get("/ais31/cohorts/{cohort_key}/manifest", response_model=Dict[str, Any])
async def ais31_get_frozen_manifest(
    cohort_key: str,
    include_ground_truth: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: builds immutable versioned manifest for a frozen cohort."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.build_frozen_manifest(
            db=db, cohort_key=cohort_key, include_ground_truth=include_ground_truth
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/cohorts/{cohort_key}/token-audit", response_model=Dict[str, Any])
async def ais31_audit_token_budgets(
    cohort_key: str,
    max_context_tokens: int = Query(8192, ge=1024, le=131072),
    max_completion_tokens: int = Query(768, ge=64, le=4096),
    target_input_budget: int = Query(7424, ge=512, le=65536),
    verify_remote_tokenize: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: verifies wire token budget & evidence completeness across all cohort members."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.audit_token_budgets(
            db=db,
            cohort_key=cohort_key,
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
            verify_remote_tokenize=verify_remote_tokenize,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/ais31/cohorts/{cohort_key}/runs", response_model=Dict[str, Any])
async def ais31_execute_benchmark_step(
    cohort_key: str,
    run_type: str = Query("FULL_HOLDOUT_100", pattern="^(PILOT_5|FULL_HOLDOUT_100|CUSTOM)$"),
    run_key: Optional[str] = Query(None),
    batch_size: int = Query(5, ge=1, le=20),
    offset: int = Query(0, ge=0),
    incident_ids: Optional[str] = Query(None, description="Comma-separated FortiSIEM IDs"),
    max_context_tokens: int = Query(8192, ge=1024, le=131072),
    max_completion_tokens: int = Query(768, ge=64, le=4096),
    target_input_budget: int = Query(7424, ge=512, le=65536),
    timeout_seconds: float = Query(180.0, ge=10.0, le=300.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Administrator-only: creates or idempotently resumes an AIS 3.1 live GPU benchmark run,
    processing up to `batch_size` pending incidents per request to avoid reverse-proxy timeouts.
    """
    from app.models.analyst_feedback import BenchmarkCohort, BenchmarkCohortItem
    from app.models.ais31_benchmark import AIS31BenchmarkResult
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        run = await AIS31BenchmarkService.create_or_resume_run(
            db=db,
            cohort_key=cohort_key,
            run_type=run_type,
            created_by_user=current_user.username,
            run_key=run_key,
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except RuntimeError as re_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re_err))

    if incident_ids:
        target_fids = [x.strip() for x in incident_ids.split(",") if x.strip()]
    else:
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one()
        all_items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()
        done_fids = {
            row[0]
            for row in (
                await db.execute(
                    select(AIS31BenchmarkResult.fortisiem_incident_id).where(
                        AIS31BenchmarkResult.run_id == run.id,
                        AIS31BenchmarkResult.execution_status.in_(["COMPLETED", "QUARANTINED"]),
                    )
                )
            ).all()
        }
        pending_fids = [it.fortisiem_incident_id for it in all_items if it.fortisiem_incident_id not in done_fids]
        target_fids = pending_fids[offset : offset + batch_size]

    return await AIS31BenchmarkService.execute_run(
        db=db,
        run_id=run.id,
        target_fids=target_fids,
        timeout_seconds=timeout_seconds,
    )


@router.get("/ais31/runs/{run_id}/evaluate", response_model=Dict[str, Any])
async def ais31_evaluate_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: post-run comparison against locked human ground truth."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.evaluate_run_against_ground_truth(db=db, run_id=run_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/runs/{run_id}/wire-prompt/{incident_id}", response_model=Dict[str, Any])
async def ais31_get_wire_prompt(
    run_id: str,
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Administrator-only: returns exact outbound wire prompt & raw vLLM response for an executed benchmark item."""
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    try:
        return await AIS31BenchmarkService.get_wire_prompt_capture(
            db=db, run_id=run_id, fortisiem_incident_id=incident_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais31/latest-summary", response_model=Dict[str, Any])
async def ais31_get_latest_cohort_summary(
    cohort_key: str = Query("AIS_3_0_INDEPENDENT_HOLDOUT_100"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns non-leaky aggregate benchmark status & metrics for the latest completed/partial run."""
    from app.models.ais31_benchmark import AIS31BenchmarkRun
    from app.services.ais31_benchmark_service import AIS31BenchmarkService

    latest = (
        await db.execute(
            select(AIS31BenchmarkRun)
            .where(AIS31BenchmarkRun.cohort_key == cohort_key)
            .order_by(AIS31BenchmarkRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not latest:
        return {"has_run": False, "cohort_key": cohort_key}

    eval_data = await AIS31BenchmarkService.evaluate_run_against_ground_truth(db=db, run_id=latest.id)
    return {
        "has_run": True,
        "run_id": latest.id,
        "run_key": latest.run_key,
        "run_type": latest.run_type,
        "status": latest.status,
        "benchmark_grade": latest.benchmark_grade,
        "expected_model": latest.expected_model,
        "actual_model_returned": latest.actual_model_returned,
        "raw_llm_metrics": eval_data["raw_llm_metrics"],
        "application_metrics": eval_data["application_metrics"],
        "subpopulations": eval_data["subpopulations"],
        "validator_telemetry": eval_data["validator_telemetry"],
        "baselines": eval_data["baselines"],
    }
