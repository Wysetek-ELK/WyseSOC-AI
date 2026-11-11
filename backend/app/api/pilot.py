import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_admin, require_analyst
from app.database import get_db
from app.models.audit import AuditLog
from app.models.pilot import PilotEvaluationRecord
from app.models.user import User
from app.schemas.pilot import (
    PilotActivateRequest,
    PilotBatchRunRequest,
    PilotConfigHistoryItem,
    PilotConfigResponse,
    PilotConfigUpdateRequest,
    PilotEvaluationResponse,
    PilotFeedbackRequest,
    PilotLifecycleActionRequest,
    PilotRollbackRequest,
    PilotSupervisorVerifyRequest,
)
from app.services.historical_eligibility_service import HistoricalEligibilityService
from app.services.pilot_service import PilotService
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine

router = APIRouter(prefix="/pilot", tags=["Controlled SOC Pilot"])


@router.get("/config", response_model=PilotConfigResponse)
async def get_pilot_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read current controlled SOC pilot configuration (accessible to all authenticated roles, read-only)."""
    svc = PilotService(db)
    cfg = await svc.get_or_create_config()
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.put("/config", response_model=PilotConfigResponse)
async def update_pilot_config(
    req: PilotConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update SOC pilot configuration (Administrator / SOC Lead only)."""
    svc = PilotService(db)
    cfg = await svc.update_config(req, actor=current_user.username)
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.post("/activate", response_model=PilotConfigResponse)
async def activate_pilot(
    req: PilotActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Activate SOC pilot in SHADOW or ANALYST_ASSISTED mode (Administrator / SOC Lead only)."""
    svc = PilotService(db)
    cfg = await svc.activate_pilot(req, actor=current_user.username)
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.post("/pause", response_model=PilotConfigResponse)
async def pause_pilot(
    req: PilotLifecycleActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Pause active SOC pilot execution without altering historical data or verdicts."""
    svc = PilotService(db)
    cfg = await svc.pause_pilot(req.reason, actor=current_user.username)
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.post("/resume", response_model=PilotConfigResponse)
async def resume_pilot(
    req: PilotLifecycleActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Resume a paused SOC pilot."""
    svc = PilotService(db)
    try:
        cfg = await svc.resume_pilot(req.reason, actor=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.post("/disable", response_model=PilotConfigResponse)
async def disable_pilot(
    req: PilotLifecycleActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Safely disable SOC pilot while preserving all analyst decisions, verdicts, and audit logs."""
    svc = PilotService(db)
    cfg = await svc.disable_pilot(req.reason, actor=current_user.username)
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.post("/rollback", response_model=PilotConfigResponse)
async def rollback_pilot(
    req: PilotRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Roll back SOC pilot configuration to an earlier version safely."""
    svc = PilotService(db)
    try:
        cfg = await svc.rollback_config(req.target_version, req.reason, actor=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PilotConfigResponse(**svc._config_to_snapshot(cfg), created_by=cfg.created_by, updated_by=cfg.updated_by, created_at=cfg.created_at, updated_at=cfg.updated_at)


@router.get("/history", response_model=List[PilotConfigHistoryItem])
async def get_pilot_history(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Immutable version history of pilot configuration & lifecycle changes."""
    svc = PilotService(db)
    rows = await svc.get_history(limit=limit)
    return [
        PilotConfigHistoryItem(
            id=r.id,
            pilot_id=r.pilot_id,
            version_number=r.version_number,
            action=r.action,
            mode=r.mode,
            is_paused=r.is_paused,
            config_snapshot=r.config_snapshot or {},
            change_reason=r.change_reason,
            changed_by=r.changed_by,
            changed_at=r.changed_at,
        )
        for r in rows
    ]


@router.get("/audit")
async def get_pilot_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read-only tamper-evident audit log entries for SOC Pilot lifecycle and feedback actions."""
    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.resource_type.in_(["PILOT_CONFIG", "PILOT_EVALUATION"]) | AuditLog.action.like("PILOT_%"))
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    items = []
    for log in res.scalars().all():
        items.append(
            {
                "id": log.id,
                "action": log.action,
                "username": log.username,
                "entity_type": log.resource_type,
                "entity_id": log.resource_id,
                "details": log.details or {},
                "signature": log.signature,
                "created_at": log.created_at.isoformat(),
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/evaluate/{incident_id}")
async def run_pilot_single_incident(
    incident_id: str,
    source_type: str = Query("LIVE", pattern="^(LIVE|HISTORICAL)$"),
    allow_simulated: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Execute controlled pilot evaluation for a single incident (Analyst/Admin only)."""
    svc = PilotService(db)
    try:
        return await svc.evaluate_incident_for_pilot(
            incident_id=incident_id,
            source_type=source_type,
            actor=current_user.username,
            allow_simulated=(allow_simulated and source_type != "LIVE"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run-batch")
async def run_pilot_batch(
    req: PilotBatchRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Execute controlled pilot evaluation batch honoring scope, budgets, and safety limits."""
    svc = PilotService(db)
    return await svc.run_pilot_batch(req, actor=current_user.username)


def _to_eval_response(r: PilotEvaluationRecord) -> PilotEvaluationResponse:
    eff_t, hist_t, _, _ = VerdictTrustworthinessEngine.cap_uncalibrated_trust_score(
        r.trust_score, is_calibrated=bool(r.is_calibrated)
    )
    return PilotEvaluationResponse(
        id=r.id,
        pilot_id=r.pilot_id,
        pilot_version=r.pilot_version,
        incident_id=r.incident_id,
        incident_db_id=r.incident_db_id,
        rule_id=r.rule_id,
        archetype=r.archetype,
        severity=r.severity,
        execution_mode=r.execution_mode,
        source_type=r.source_type,
        eligibility_status=r.eligibility_status,
        proposed_verdict=r.proposed_verdict,
        validated_verdict=r.validated_verdict,
        validation_status=r.validation_status,
        abstention_reason=r.abstention_reason,
        trust_score=eff_t,
        historical_trust_score=hist_t,
        raw_trust_score=r.raw_trust_score,
        is_calibrated=r.is_calibrated,
        evidence_completeness=r.evidence_completeness,
        grounding_ratio=r.grounding_ratio,
        supporting_evidence=r.supporting_evidence or [],
        contradictory_evidence=r.contradictory_evidence or [],
        missing_evidence=r.missing_evidence or [],
        policy_version_id=r.policy_version_id,
        policy_version_number=r.policy_version_number,
        policy_digest=r.policy_digest,
        model_identifier=r.model_identifier,
        is_simulated=r.is_simulated,
        latency_ms=r.latency_ms,
        prompt_tokens=r.prompt_tokens,
        completion_tokens=r.completion_tokens,
        total_tokens=r.total_tokens,
        evidence_snapshot_hash=r.evidence_snapshot_hash,
        error_message=r.error_message,
        analyst_feedback_action=r.analyst_feedback_action,
        analyst_decision=r.analyst_decision,
        analyst_override_reason=r.analyst_override_reason,
        analyst_user=r.analyst_user,
        analyst_decided_at=r.analyst_decided_at,
        supervisor_verified=r.supervisor_verified,
        supervisor_user=r.supervisor_user,
        supervisor_verified_at=r.supervisor_verified_at,
        created_at=r.created_at,
    )


@router.get("/evaluations", response_model=List[PilotEvaluationResponse])
async def list_pilot_evaluations(
    mode: Optional[str] = Query(None),
    include_simulated: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List pilot evaluation records with normalized uncalibrated trust display & preserved provenance."""
    q = select(PilotEvaluationRecord).order_by(desc(PilotEvaluationRecord.created_at)).limit(limit)
    if mode:
        q = q.where(PilotEvaluationRecord.execution_mode == mode.upper())
    if not include_simulated:
        q = q.where(PilotEvaluationRecord.is_simulated == False)
    res = await db.execute(q)
    return [_to_eval_response(r) for r in res.scalars().all()]


@router.post("/evaluations/{evaluation_id}/feedback", response_model=PilotEvaluationResponse)
async def submit_pilot_analyst_feedback(
    evaluation_id: str,
    req: PilotFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """Record analyst acceptance/override/dispute without overwriting AI recommendation."""
    svc = PilotService(db)
    try:
        r = await svc.record_analyst_feedback(evaluation_id, req, analyst_username=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _to_eval_response(r)


@router.post("/evaluations/{evaluation_id}/supervisor-verify", response_model=PilotEvaluationResponse)
async def supervisor_verify_pilot_feedback(
    evaluation_id: str,
    req: PilotSupervisorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Independent supervisor verification gate (Administrator only; blocks self-verification)."""
    svc = PilotService(db)
    try:
        r = await svc.supervisor_verify_feedback(evaluation_id, req, supervisor_username=current_user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_eval_response(r)


@router.get("/metrics")
async def get_pilot_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Operational, verdict reliability, and empirical accuracy metrics for the SOC Pilot (read-only accessible)."""
    svc = PilotService(db)
    return await svc.get_pilot_metrics()


@router.get("/eligibility-report")
async def get_pilot_eligibility_report(
    rule_id: Optional[str] = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Exportable historical corpus eligibility report (G8 & calibration readiness)."""
    svc = HistoricalEligibilityService(db)
    report = await svc.generate_report(rule_id=rule_id)
    if format == "csv":
        return Response(
            content=svc.to_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=historical_eligibility_report.csv"},
        )
    return report
