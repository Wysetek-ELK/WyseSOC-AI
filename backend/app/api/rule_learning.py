import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_
from pydantic import BaseModel, Field, field_validator

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.rule_learning import RuleLearningProfile, RuleLearningStateHistory
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.production_governance import (
    RulePromotionRequest,
    ProductionAutomationPolicy,
    IncidentAutomationAudit
)
from app.services.rule_learning_service import RuleLearningService
from app.services.analyst_review_service import AnalystReviewService
from app.services.promotion_service import PromotionService
from app.services.automation_governor import AutomationGovernor

logger = logging.getLogger("ai_verdict.api.rule_learning")

router = APIRouter(tags=["Rule-Based Learning & Production Governance"])


# Pydantic Request / Response Schemas
class TransitionStageRequest(BaseModel):
    new_stage: Optional[str] = Field(None, description="Target lifecycle stage")
    target_stage: Optional[str] = Field(None, description="Target lifecycle stage alias")
    stage: Optional[str] = Field(None, description="Target lifecycle stage alias")
    reason: Optional[str] = Field("State transition requested by user", description="Justification for transition")
    customer: Optional[str] = Field(None, description="Optional customer tenant scope")


class SubmitReviewRequest(BaseModel):
    analyst_verdict: str = Field(..., description="TRUE_POSITIVE, FALSE_POSITIVE, or INSUFFICIENT_EVIDENCE")
    analyst_notes: Optional[str] = Field("", description="Supporting rationale")
    verdict_reason: Optional[str] = Field(None, description="Alias for analyst_notes")
    notes: Optional[str] = Field(None, description="Alias for analyst_notes")
    correction_reason: Optional[str] = Field(None, description="Correction category if overturning AI")
    evidence_references: Optional[Union[List[str], str]] = Field(default_factory=list, description="List of cited evidence IDs")
    blind_mode_active: bool = Field(True, description="Whether AI verdict was hidden during assessment")

    @field_validator("analyst_verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: Any) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("analyst_verdict is required and must be a non-empty string")
        v_clean = v.upper().strip().replace(" ", "_").replace("-", "_")
        # Reject derived comparison outcomes
        if v_clean in ("AGREE_TP", "AGREE_FP", "MISSED_TP", "CRITICAL_MISSED_TP", "FALSE_ALARM", "AI_FALSE_ALARM", "AGREEMENT_TP", "AGREEMENT_FP"):
            raise ValueError(
                f"'{v}' is a derived post-comparison outcome and cannot be submitted as an independent analyst verdict. "
                "Allowed values are strictly: TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE."
            )
        if v_clean in ("TP", "TRUE_POSITIVE", "TRUEPOSITIVE", "MALICIOUS"):
            return "TRUE_POSITIVE"
        if v_clean in ("FP", "FALSE_POSITIVE", "FALSEPOSITIVE", "BENIGN"):
            return "FALSE_POSITIVE"
        if v_clean in ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT", "INCONCLUSIVE", "ABSTAIN", "REQUIRES_ATTENTION", "UNKNOWN", "UNCERTAIN"):
            return "INSUFFICIENT_EVIDENCE"
        if v_clean not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "INSUFFICIENT_EVIDENCE"):
            raise ValueError(
                f"Invalid analyst verdict '{v}'. Allowed values are strictly: TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE, INCONCLUSIVE."
            )
        return v_clean

    @field_validator("evidence_references", mode="before")
    @classmethod
    def normalize_evidence_refs(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            if not v.strip():
                return []
            return [x.strip() for x in v.split(",") if x.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


class AdjudicateReviewRequest(BaseModel):
    final_verdict: str = Field(..., description="Binding determination: TRUE_POSITIVE, FALSE_POSITIVE, or INSUFFICIENT_EVIDENCE")
    rationale: str = Field(..., description="Adjudication rationale")


class CreatePromotionRequest(BaseModel):
    profile_id: Optional[str] = Field(None, description="Profile ID or Rule ID")
    rule_id: Optional[str] = Field(None, description="Alternative Rule ID alias")
    target_stage: Optional[str] = Field(None, description="Requested stage (e.g. SUPERVISED_PILOT, CONTROLLED_PRODUCTION)")
    stage: Optional[str] = Field(None, description="Alternative target stage field")
    justification: Optional[str] = Field("Qualified via evaluation benchmarks", description="Operational justification")
    evaluation_run_id: Optional[str] = Field(None, description="Simulation run ID proving readiness")


class DecidePromotionRequest(BaseModel):
    request_id: Optional[str] = Field(None, description="Promotion request ID (optional if provided in query)")
    action: str = Field(..., description="APPROVED or REJECTED")
    decision_notes: str = Field("", description="Reviewer notes")
    signature: str = Field("", description="Cryptographic signature string")


class EmergencyDisableRequest(BaseModel):
    reason: str = Field(..., description="Reason for engaging global emergency kill-switch")


class UpdateAutomationPolicyRequest(BaseModel):
    customer: Optional[str] = Field("DEFAULT", description="Tenant scope")
    is_enabled: Optional[bool] = Field(None, description="Enable or disable automated FP closure")
    min_trust_score: Optional[int] = Field(None, ge=7, le=10)
    min_fp_precision: Optional[float] = Field(None, ge=0.99, le=1.0)
    daily_closure_limit: Optional[int] = Field(None, ge=1, le=500)
    emergency_disable: Optional[bool] = Field(None, description="Engage or clear rule-scoped emergency disable")
    reason: Optional[str] = Field("", description="Audit reason for policy update")


class ExecuteAutomationDecisionRequest(BaseModel):
    customer: Optional[str] = Field(None, description="Optional customer tenant scope")
    dry_run: bool = Field(True, description="Dry-run simulation mode (default True; never executes live FortiSIEM closure)")
    global_kill_switch: bool = Field(False, description="Optional kill-switch simulation override")


def _serialize_profile_detail(
    profile: RuleLearningProfile,
    is_eligible: bool,
    reasons: List[str],
    full_meta: Optional[Dict[str, Any]] = None,
    policy: Optional[ProductionAutomationPolicy] = None,
) -> Dict[str, Any]:
    err_dist = profile.error_distribution or {}
    eligible_evals = int((profile.ai_correct_count or 0) + (profile.ai_incorrect_count or 0))
    total_decisive_plus_abs = eligible_evals + int(profile.abstention_count or 0)
    abstention_rate = round(float(profile.abstention_count or 0) / float(total_decisive_plus_abs), 4) if total_decisive_plus_abs > 0 else 0.0
    coverage = round(float(eligible_evals) / float(total_decisive_plus_abs), 4) if total_decisive_plus_abs > 0 else 0.0
    false_alarm_cnt = int(err_dist.get("ai_false_alarm", 0))
    agreed_fp = int(err_dist.get("agreement_fp", 0))
    false_alarm_rate = round(float(false_alarm_cnt) / float(false_alarm_cnt + agreed_fp), 4) if (false_alarm_cnt + agreed_fp) > 0 else 0.0

    confusion_matrix = {
        "agreed_fp": agreed_fp,
        "critical_missed_tp": int(err_dist.get("critical_missed_tp", 0)),
        "ai_false_alarm": false_alarm_cnt,
        "agreed_tp": int(err_dist.get("agreement_tp", 0)),
        "abstained_resolved": int(err_dist.get("analyst_resolved_abstention", 0)),
        "disputed": int(err_dist.get("disputed", 0)),
        "initial_benchmarks": int(err_dist.get("analyst_only_initial_benchmark", 0)),
    }

    payload: Dict[str, Any] = {
        "id": profile.id,
        "rule_id": profile.rule_id,
        "rule_identifier": profile.rule_identifier,
        "customer": profile.customer,
        "primary_archetype": profile.primary_archetype,
        "lifecycle_stage": profile.lifecycle_stage,
        "active_model_identifier": profile.active_model_identifier,
        "total_incidents_processed": profile.total_incidents_processed,
        "total_analyst_reviews": profile.total_analyst_reviews,
        "eligible_evaluations": eligible_evals,
        "verified_tp_count": profile.verified_tp_count,
        "verified_fp_count": profile.verified_fp_count,
        "ai_correct_count": profile.ai_correct_count,
        "ai_incorrect_count": profile.ai_incorrect_count,
        "abstention_count": profile.abstention_count,
        "abstention_rate": abstention_rate,
        "coverage": coverage,
        "false_alarm_rate": false_alarm_rate,
        "validation_failure_count": profile.validation_failure_count,
        "empirical_accuracy": profile.empirical_accuracy,
        "fp_precision": profile.fp_precision,
        "wilson_lower_bound": profile.wilson_lower_bound,
        "tp_recall": profile.tp_recall,
        "is_production_eligible": is_eligible,
        "eligibility_reasons": reasons,
        "error_distribution": profile.error_distribution,
        "confusion_matrix": confusion_matrix,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }
    if full_meta:
        payload["readiness_governance"] = full_meta
    if policy:
        payload["automation_policy"] = {
            "policy_id": policy.id,
            "is_enabled": policy.is_enabled,
            "emergency_disable": policy.emergency_disable,
            "allowed_verdicts": policy.allowed_verdicts,
            "min_trust_score": policy.min_trust_score,
            "min_fp_precision": policy.min_fp_precision,
            "daily_closure_limit": policy.daily_closure_limit,
            "current_day_closure_count": policy.current_day_closure_count,
        }
    return payload


# Endpoints

@router.get("/learning/rules", response_model=Dict[str, Any])
async def list_rule_learning_profiles(
    lifecycle_stage: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lists detection rule learning profiles with performance metrics and production eligibility.
    Pure read operation adhering to HTTP GET safety standards.
    """
    stmt = select(RuleLearningProfile).order_by(desc(RuleLearningProfile.total_analyst_reviews))
    if lifecycle_stage:
        stmt = stmt.where(RuleLearningProfile.lifecycle_stage == lifecycle_stage.upper().strip())
    if customer and customer.upper() != "ALL":
        stmt = stmt.where(RuleLearningProfile.customer == customer)

    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    profiles = res.scalars().all()

    items = []
    for p in profiles:
        is_eligible, reasons = RuleLearningService.check_production_eligibility(p)
        items.append({
            "id": p.id,
            "rule_id": p.rule_id,
            "rule_identifier": p.rule_identifier,
            "customer": p.customer,
            "primary_archetype": p.primary_archetype,
            "lifecycle_stage": p.lifecycle_stage,
            "total_incidents_processed": p.total_incidents_processed,
            "total_analyst_reviews": p.total_analyst_reviews,
            "eligible_evaluations": int((p.ai_correct_count or 0) + (p.ai_incorrect_count or 0)),
            "verified_tp_count": p.verified_tp_count,
            "verified_fp_count": p.verified_fp_count,
            "empirical_accuracy": p.empirical_accuracy,
            "fp_precision": p.fp_precision,
            "wilson_lower_bound": p.wilson_lower_bound,
            "tp_recall": p.tp_recall,
            "active_model_identifier": p.active_model_identifier,
            "is_production_eligible": is_eligible,
            "eligibility_reasons": reasons,
            "last_evaluated_at": p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
        })

    return {
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
    }


@router.get("/learning/rules/{rule_id}", response_model=Dict[str, Any])
async def get_rule_learning_profile(
    rule_id: str,
    customer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves detailed learning profile, confusion metrics, governance gates, and automation policy for a rule.
    Pure read operation adhering to HTTP GET safety standards.
    """
    target_customer = customer or "DEFAULT"
    profile = await RuleLearningService.get_profile(db=db, rule_id=rule_id, customer=target_customer)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No learning profile found for rule '{rule_id}' in tenant scope '{target_customer}'. Please click 'Initialize Learning Profile' or call POST /api/learning/rules/{rule_id}/initialize."
        )

    is_eligible, reasons, full_meta = await RuleLearningService.evaluate_full_production_readiness(db, profile)
    pol_res = await db.execute(select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id))
    policy = pol_res.scalar_one_or_none()
    return _serialize_profile_detail(profile, is_eligible, reasons, full_meta, policy)


@router.post("/learning/rules/{rule_id}/evaluate-accuracy", response_model=Dict[str, Any])
async def evaluate_rule_accuracy(
    rule_id: str,
    customer: Optional[str] = Query(None),
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Authoritative evaluation endpoint. Triggers exact empirical accuracy recalculation
    and reconciliation across all verified analyst determinations and matched AI decisions.
    """
    target_customer = customer or "DEFAULT"
    result = await RuleLearningService.evaluate_rule_accuracy(
        db=db,
        rule_id=rule_id,
        customer=target_customer,
        version_id=version_id,
    )
    return result


@router.get("/learning/rules/{rule_id}/history", response_model=Dict[str, Any])
async def get_rule_learning_history(
    rule_id: str,
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns immutable lifecycle state transition history for a rule learning profile."""
    profile = await RuleLearningService.get_profile(db=db, rule_id=rule_id, customer=customer or "DEFAULT")
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile for rule '{rule_id}' not found.")

    hist_res = await db.execute(
        select(RuleLearningStateHistory)
        .where(RuleLearningStateHistory.profile_id == profile.id)
        .order_by(desc(RuleLearningStateHistory.transitioned_at))
        .limit(limit)
    )
    rows = hist_res.scalars().all()
    return {
        "profile_id": profile.id,
        "rule_id": profile.rule_id,
        "rule_identifier": profile.rule_identifier,
        "items": [
            {
                "id": h.id,
                "previous_stage": h.previous_stage,
                "new_stage": h.new_stage,
                "transition_reason": h.transition_reason,
                "triggered_by_user_id": h.triggered_by_user_id,
                "metrics_snapshot": h.metrics_snapshot or {},
                "transitioned_at": h.transitioned_at.isoformat() if h.transitioned_at else None,
            }
            for h in rows
        ],
    }


@router.post("/learning/rules/{rule_id}/initialize", response_model=Dict[str, Any])
async def initialize_rule_learning_profile(
    rule_id: str,
    customer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Explicit, authenticated, idempotent initialization of a rule's learning profile.
    Initializes the profile in LEARNING state with zero verified reviews and auto-closure disabled.
    """
    target_customer = customer or "DEFAULT"
    profile = await RuleLearningService.get_or_create_profile(db=db, rule_id=rule_id, customer=target_customer)
    is_eligible, reasons, full_meta = await RuleLearningService.evaluate_full_production_readiness(db, profile)
    pol_res = await db.execute(select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id))
    policy = pol_res.scalar_one_or_none()
    return _serialize_profile_detail(profile, is_eligible, reasons, full_meta, policy)


@router.post("/learning/rules/initialize-all", response_model=Dict[str, Any])
async def initialize_all_rule_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Explicit, authenticated bulk initialization of learning profiles for all active detection rules
    across all customer tenants.
    """
    profiles = await RuleLearningService.ensure_all_rules_initialized(db)
    return {
        "status": "success",
        "initialized_count": len(profiles),
        "message": f"Successfully ensured learning profiles for {len(profiles)} detection rule scopes."
    }


@router.post("/learning/rules/{rule_id}/suggest-prompt-improvement", response_model=Dict[str, Any])
async def suggest_prompt_improvement(
    rule_id: str,
    customer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Creates a controlled DRAFT candidate prompt version from verified analyst error patterns.
    Never modifies the active approved production prompt.
    """
    try:
        res = await RuleLearningService.propose_prompt_improvement_draft(
            db=db,
            rule_id=rule_id,
            customer=customer or "DEFAULT",
            user_id=current_user.id,
        )
        await db.commit()
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/learning/rules/{rule_id}/transition", response_model=Dict[str, Any])
async def transition_rule_stage(
    rule_id: str,
    payload: TransitionStageRequest,
    customer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Transitions rule lifecycle state (e.g. LEARNING -> VALIDATION -> SUPERVISED_PILOT or SUSPENDED).
    Direct transition to CONTROLLED_PRODUCTION is blocked here and MUST go through dual-key
    Administrator promotion approval (/api/governance/promotion/request -> /decide).
    """
    target_stage = (payload.new_stage or payload.target_stage or payload.stage or "").upper().strip()
    if not target_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_stage (or target_stage) is required."
        )

    if target_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct transition to CONTROLLED_PRODUCTION is prohibited. Submit a formal promotion request (/api/governance/promotion/request) for dual-control Administrator approval."
        )

    eff_customer = customer or payload.customer or "DEFAULT"
    profile = await RuleLearningService.get_or_create_profile(db=db, rule_id=rule_id, customer=eff_customer)
    try:
        updated = await RuleLearningService.transition_lifecycle_stage(
            db=db,
            profile=profile,
            new_stage=target_stage,
            reason=payload.reason or "State transition requested by user",
            user_id=current_user.username
        )
        resp_body = {
            "status": "SUCCESS",
            "rule_identifier": updated.rule_identifier,
            "customer": updated.customer,
            "new_stage": updated.lifecycle_stage,
        }
        await db.commit()
        return resp_body
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reviews/pending", response_model=Dict[str, Any])
async def get_pending_analyst_reviews(
    rule_id: Optional[str] = Query(None, description="Optional rule identifier or UUID filter"),
    customer: Optional[str] = Query(None, description="Optional customer tenant filter"),
    include_reviewed: bool = Query(False, description="Include already-reviewed incidents"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches the double-blind review queue. AI verdicts are strictly masked to eliminate bias.
    """
    effective_customer = customer or (getattr(current_user, "customer", None) if getattr(current_user, "role", "") not in ("Administrator", "SuperAdmin", "SOC_Manager") else None)
    total, items = await AnalystReviewService.get_pending_reviews(
        db=db,
        customer=effective_customer,
        rule_id=rule_id,
        limit=limit,
        offset=offset,
        reviewer_id=current_user.username,
        include_reviewed=include_reviewed,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "blind_mode_active": True,
    }


@router.post("/reviews/{incident_id}/submit", response_model=Dict[str, Any])
async def submit_analyst_review(
    incident_id: str,
    payload: SubmitReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Submits independent analyst determination, reveals stored AI verdict,
    evaluates agreement, updates verified ground truth, and recalibrates rule profile.
    """
    effective_notes = payload.analyst_notes or payload.verdict_reason or payload.notes or ""
    try:
        res = await AnalystReviewService.submit_analyst_review(
            db=db,
            incident_id=incident_id,
            reviewer_id=current_user.username,
            analyst_verdict=payload.analyst_verdict.upper().strip(),
            analyst_notes=effective_notes,
            correction_reason=payload.correction_reason,
            evidence_references=payload.evidence_references if isinstance(payload.evidence_references, list) else [],
            blind_mode_active=payload.blind_mode_active,
            customer=getattr(current_user, "customer", None)
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        elif "access denied" in err_msg.lower() or "unauthorized" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.post("/reviews/{review_id}/adjudicate", response_model=Dict[str, Any])
async def adjudicate_review(
    review_id: str,
    payload: AdjudicateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Binding Senior Analyst / L2 Manager dispute adjudication.
    """
    if current_user.role not in ("Administrator", "SOC_Manager", "Senior_Analyst"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Senior Analysts or SOC Managers can adjudicate reviews."
        )

    try:
        res = await AnalystReviewService.adjudicate_review(
            db=db,
            review_id=review_id,
            adjudicator_id=current_user.username,
            final_verdict=payload.final_verdict.upper().strip(),
            rationale=payload.rationale
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/governance/promotion/requests", response_model=Dict[str, Any])
async def list_promotion_requests(
    rule_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lists formal rule promotion requests and dual-key approval records."""
    items = await PromotionService.list_promotion_requests(
        db=db,
        rule_id=rule_id,
        status_filter=status_filter,
        customer=customer,
        limit=limit,
    )
    return {"items": items, "count": len(items)}


@router.post("/governance/promotion/request", response_model=Dict[str, Any])
async def request_rule_promotion(
    payload: CreatePromotionRequest,
    profile_id: Optional[str] = Query(None, description="Profile ID or Rule ID query parameter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Submits formal request to promote a rule to a higher lifecycle stage.
    Accepts profile_id / rule_id via query parameter or JSON request body.
    """
    target_profile_id = profile_id or payload.profile_id or payload.rule_id
    if not target_profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="profile_id must be provided in query parameters or request body."
        )

    target_stage = (payload.target_stage or payload.stage or "").upper().strip()
    if not target_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_stage is required."
        )

    try:
        req = await PromotionService.create_promotion_request(
            db=db,
            profile_id=target_profile_id,
            target_stage=target_stage,
            requester_id=current_user.username,
            justification=payload.justification or "Qualified via evaluation benchmarks",
            evaluation_run_id=payload.evaluation_run_id
        )
        resp_body = {
            "request_id": req.id,
            "rule_id": req.rule_id,
            "profile_id": req.profile_id,
            "customer": req.customer,
            "requested_stage": req.requested_stage,
            "status": req.status,
            "supporting_metrics": req.supporting_metrics,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        }
        await db.commit()
        return resp_body
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.post("/governance/promotion/decide", response_model=Dict[str, Any])
async def decide_rule_promotion(
    payload: DecidePromotionRequest,
    request_id: Optional[str] = Query(None, description="Promotion request ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Dual-key sign-off approving or rejecting a rule promotion request.
    Enforces strict separation of duties (requester != approver).
    """
    if current_user.role not in ("Administrator", "SOC_Manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SOC Managers or Administrators can approve promotion requests."
        )

    target_req_id = request_id or payload.request_id
    if not target_req_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="request_id is required.")

    try:
        res = await PromotionService.decide_promotion_request(
            db=db,
            request_id=target_req_id,
            approver_id=current_user.username,
            action=payload.action.upper().strip(),
            decision_notes=payload.decision_notes,
            signature=payload.signature
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        err_msg = str(e)
        if "separation of duties" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.get("/governance/automation/policy/{rule_id}", response_model=Dict[str, Any])
async def get_automation_policy(
    rule_id: str,
    customer: str = Query("DEFAULT"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns rule/tenant-scoped ProductionAutomationPolicy state."""
    profile = await RuleLearningService.get_profile(db=db, rule_id=rule_id, customer=customer)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile for rule '{rule_id}' not found.")

    pol = (await db.execute(
        select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
    )).scalar_one_or_none()
    if not pol:
        return {
            "profile_id": profile.id,
            "rule_id": profile.rule_identifier,
            "customer": profile.customer,
            "lifecycle_stage": profile.lifecycle_stage,
            "is_enabled": False,
            "emergency_disable": False,
            "allowed_verdicts": ["FALSE_POSITIVE"],
            "min_trust_score": 8,
            "min_fp_precision": 0.99,
            "daily_closure_limit": 50,
            "current_day_closure_count": 0,
        }
    return {
        "policy_id": pol.id,
        "profile_id": pol.profile_id,
        "rule_id": pol.rule_id,
        "customer": pol.customer,
        "lifecycle_stage": profile.lifecycle_stage,
        "is_enabled": pol.is_enabled,
        "emergency_disable": pol.emergency_disable,
        "allowed_verdicts": pol.allowed_verdicts,
        "min_trust_score": pol.min_trust_score,
        "min_fp_precision": pol.min_fp_precision,
        "daily_closure_limit": pol.daily_closure_limit,
        "current_day_closure_count": pol.current_day_closure_count,
    }


@router.put("/governance/automation/policy/{rule_id}", response_model=Dict[str, Any])
async def update_automation_policy(
    rule_id: str,
    payload: UpdateAutomationPolicyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Administrator-only: Explicitly enable/disable or tune rule/tenant-scoped FP automation.
    Enabling requires CONTROLLED_PRODUCTION stage and passing all production readiness checks.
    """
    if current_user.role not in ("Administrator", "SOC_Manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Administrators or SOC Managers may modify automation policies.")

    try:
        res = await PromotionService.update_automation_policy(
            db=db,
            rule_id=rule_id,
            customer=payload.customer or "DEFAULT",
            admin_user_id=current_user.username,
            is_enabled=payload.is_enabled,
            min_trust_score=payload.min_trust_score,
            min_fp_precision=payload.min_fp_precision,
            daily_closure_limit=payload.daily_closure_limit,
            emergency_disable=payload.emergency_disable,
            reason=payload.reason or "",
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/governance/automation/decide/{incident_id}", response_model=Dict[str, Any])
async def execute_governed_automation_decision(
    incident_id: str,
    payload: Optional[ExecuteAutomationDecisionRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    """
    Executes governed incident automation decision (dry_run=True by default).
    Live closure (dry_run=False) requires Administrator/SOC_Manager role AND all 12 safety barriers.
    """
    req = payload or ExecuteAutomationDecisionRequest()
    if not req.dry_run and current_user.role not in ("Administrator", "SOC_Manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Administrators or SOC Managers may invoke non-dry-run FortiSIEM write-back."
        )
    try:
        res = await AutomationGovernor.execute_governed_incident_decision(
            db=db,
            incident_id=incident_id,
            customer=req.customer,
            dry_run=req.dry_run,
            global_kill_switch=req.global_kill_switch,
        )
        await db.commit()
        return res
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/governance/automation/audits", response_model=Dict[str, Any])
async def list_automation_audits(
    rule_id: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns immutable IncidentAutomationAudit decision history."""
    stmt = select(IncidentAutomationAudit).order_by(desc(IncidentAutomationAudit.executed_at))
    if rule_id:
        clean = str(rule_id).strip()
        _, aliases = await AnalystReviewService._resolve_rule_aliases(db, clean)
        stmt = stmt.where(IncidentAutomationAudit.rule_id.in_(aliases or [clean]))
    if customer and customer.upper() not in ("ALL", "GLOBAL"):
        stmt = stmt.where(IncidentAutomationAudit.customer == customer)

    rows = (await db.execute(stmt.limit(limit))).scalars().all()
    return {
        "items": [
            {
                "audit_id": r.id,
                "incident_id": r.incident_id,
                "rule_id": r.rule_id,
                "customer": r.customer,
                "action_type": r.action_type,
                "siem_target": r.siem_target,
                "siem_response_code": r.siem_response_code,
                "siem_transaction_id": r.siem_transaction_id,
                "execution_status": r.execution_status,
                "safety_checks_passed": r.safety_checks_passed or {},
                "closure_summary": r.closure_summary,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post("/governance/automation/emergency-disable", response_model=Dict[str, Any])
async def emergency_disable_all_automation(
    payload: EmergencyDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Emergency kill-switch: Immediately halts all automated incident closures and commits durably.
    """
    if current_user.role not in ("Administrator", "SOC_Manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    stmt = select(ProductionAutomationPolicy)
    res = await db.execute(stmt)
    policies = res.scalars().all()
    count = 0
    for p in policies:
        p.emergency_disable = True
        p.is_enabled = False
        db.add(p)
        count += 1

    await db.commit()
    logger.critical(f"EMERGENCY KILL-SWITCH ENGAGED by {current_user.username}: {payload.reason}")
    return {
        "status": "EMERGENCY_KILL_SWITCH_ACTIVE",
        "policies_disabled": count,
        "reason": payload.reason,
        "triggered_by": current_user.username
    }
