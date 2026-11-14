import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field, field_validator

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule_learning import RuleLearningProfile
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
        if v_clean in ("TP", "TRUE_POSITIVE", "TRUEPOSITIVE", "MALICIOUS"):
            return "TRUE_POSITIVE"
        if v_clean in ("FP", "FALSE_POSITIVE", "FALSEPOSITIVE", "BENIGN"):
            return "FALSE_POSITIVE"
        if v_clean in ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT", "ABSTAIN", "REQUIRES_ATTENTION", "UNKNOWN", "UNCERTAIN"):
            return "INSUFFICIENT_EVIDENCE"
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
    action: str = Field(..., description="APPROVED or REJECTED")
    decision_notes: str = Field("", description="Reviewer notes")
    signature: str = Field("", description="Cryptographic signature string")


class EmergencyDisableRequest(BaseModel):
    reason: str = Field(..., description="Reason for engaging global emergency kill-switch")


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
    Retrieves detailed learning profile, confusion metrics, and state history for a rule.
    Pure read operation adhering to HTTP GET safety standards.
    """
    target_customer = customer or "DEFAULT"
    profile = await RuleLearningService.get_profile(db=db, rule_id=rule_id, customer=target_customer)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No learning profile found for rule '{rule_id}' in tenant scope '{target_customer}'. Please click 'Initialize Learning Profile' or call POST /api/learning/rules/{rule_id}/initialize."
        )

    is_eligible, reasons = RuleLearningService.check_production_eligibility(profile)
    err_dist = profile.error_distribution or {}
    confusion_matrix = {
        "agreed_fp": err_dist.get("agreement_fp", 0),
        "critical_missed_tp": err_dist.get("critical_missed_tp", 0),
        "ai_false_alarm": err_dist.get("ai_false_alarm", 0),
        "agreed_tp": err_dist.get("agreement_tp", 0),
        "abstained_resolved": err_dist.get("analyst_resolved_abstention", 0),
        "disputed": err_dist.get("disputed", 0),
        "initial_benchmarks": err_dist.get("analyst_only_initial_benchmark", 0),
    }

    return {
        "id": profile.id,
        "rule_id": profile.rule_id,
        "rule_identifier": profile.rule_identifier,
        "customer": profile.customer,
        "primary_archetype": profile.primary_archetype,
        "lifecycle_stage": profile.lifecycle_stage,
        "total_incidents_processed": profile.total_incidents_processed,
        "total_analyst_reviews": profile.total_analyst_reviews,
        "verified_tp_count": profile.verified_tp_count,
        "verified_fp_count": profile.verified_fp_count,
        "ai_correct_count": profile.ai_correct_count,
        "ai_incorrect_count": profile.ai_incorrect_count,
        "abstention_count": profile.abstention_count,
        "validation_failure_count": profile.validation_failure_count,
        "empirical_accuracy": profile.empirical_accuracy,
        "fp_precision": profile.fp_precision,
        "wilson_lower_bound": profile.wilson_lower_bound,
        "tp_recall": profile.tp_recall,
        "is_production_eligible": is_eligible,
        "eligibility_reasons": reasons,
        "error_distribution": profile.error_distribution,
        "confusion_matrix": confusion_matrix,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
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
    If the profile already exists, returns the existing profile safely.
    """
    target_customer = customer or "DEFAULT"
    profile = await RuleLearningService.get_or_create_profile(db=db, rule_id=rule_id, customer=target_customer)
    is_eligible, reasons = RuleLearningService.check_production_eligibility(profile)
    err_dist = profile.error_distribution or {}
    confusion_matrix = {
        "agreed_fp": err_dist.get("agreement_fp", 0),
        "critical_missed_tp": err_dist.get("critical_missed_tp", 0),
        "ai_false_alarm": err_dist.get("ai_false_alarm", 0),
        "agreed_tp": err_dist.get("agreement_tp", 0),
        "abstained_resolved": err_dist.get("analyst_resolved_abstention", 0),
        "disputed": err_dist.get("disputed", 0),
        "initial_benchmarks": err_dist.get("analyst_only_initial_benchmark", 0),
    }

    return {
        "id": profile.id,
        "rule_id": profile.rule_id,
        "rule_identifier": profile.rule_identifier,
        "customer": profile.customer,
        "primary_archetype": profile.primary_archetype,
        "lifecycle_stage": profile.lifecycle_stage,
        "total_incidents_processed": profile.total_incidents_processed,
        "total_analyst_reviews": profile.total_analyst_reviews,
        "verified_tp_count": profile.verified_tp_count,
        "verified_fp_count": profile.verified_fp_count,
        "ai_correct_count": profile.ai_correct_count,
        "ai_incorrect_count": profile.ai_incorrect_count,
        "abstention_count": profile.abstention_count,
        "validation_failure_count": profile.validation_failure_count,
        "empirical_accuracy": profile.empirical_accuracy,
        "fp_precision": profile.fp_precision,
        "wilson_lower_bound": profile.wilson_lower_bound,
        "tp_recall": profile.tp_recall,
        "is_production_eligible": is_eligible,
        "eligibility_reasons": reasons,
        "error_distribution": profile.error_distribution,
        "confusion_matrix": confusion_matrix,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


@router.post("/learning/rules/initialize-all", response_model=Dict[str, Any])
async def initialize_all_rule_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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


@router.post("/learning/rules/{rule_id}/transition", response_model=Dict[str, Any])
async def transition_rule_stage(
    rule_id: str,
    payload: TransitionStageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transitions rule lifecycle state (e.g. suspend or advance to pilot).
    Supports flexible field mapping (new_stage, target_stage, stage).
    """
    target_stage = (payload.new_stage or payload.target_stage or payload.stage or "").upper().strip()
    if not target_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_stage (or target_stage) is required."
        )

    profile = await RuleLearningService.get_or_create_profile(db=db, rule_id=rule_id)
    try:
        updated = await RuleLearningService.transition_lifecycle_stage(
            db=db,
            profile=profile,
            new_stage=target_stage,
            reason=payload.reason or "State transition requested by user",
            user_id=current_user.username
        )
        return {
            "status": "SUCCESS",
            "rule_identifier": updated.rule_identifier,
            "new_stage": updated.lifecycle_stage,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reviews/pending", response_model=Dict[str, Any])
async def get_pending_analyst_reviews(
    rule_id: Optional[str] = Query(None, description="Optional rule identifier filter"),
    customer: Optional[str] = Query(None, description="Optional customer tenant filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches the double-blind review queue. AI verdicts are masked to eliminate bias.
    """
    effective_customer = customer or (getattr(current_user, "customer", None) if getattr(current_user, "role", "") not in ("Administrator", "SuperAdmin", "SOC_Manager") else None)
    total, items = await AnalystReviewService.get_pending_reviews(
        db=db,
        customer=effective_customer,
        rule_id=rule_id,
        limit=limit,
        offset=offset
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
    current_user: User = Depends(get_current_active_user)
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
        return res
    except ValueError as e:
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
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/governance/promotion/request", response_model=Dict[str, Any])
async def request_rule_promotion(
    payload: CreatePromotionRequest,
    profile_id: Optional[str] = Query(None, description="Profile ID or Rule ID query parameter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
        return {
            "request_id": req.id,
            "rule_id": req.rule_id,
            "profile_id": req.profile_id,
            "requested_stage": req.requested_stage,
            "status": req.status,
            "created_at": req.created_at.isoformat()
        }
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.post("/governance/promotion/decide", response_model=Dict[str, Any])
async def decide_rule_promotion(
    request_id: str,
    payload: DecidePromotionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Dual-key sign-off approving or rejecting a rule promotion request.
    """
    if current_user.role not in ("Administrator", "SOC_Manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SOC Managers or Administrators can approve promotion requests."
        )

    try:
        res = await PromotionService.decide_promotion_request(
            db=db,
            request_id=request_id,
            approver_id=current_user.username,
            action=payload.action.upper().strip(),
            decision_notes=payload.decision_notes,
            signature=payload.signature
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/governance/automation/emergency-disable", response_model=Dict[str, Any])
async def emergency_disable_all_automation(
    payload: EmergencyDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Emergency kill-switch: Immediately halts all automated incident closures.
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

    await db.flush()
    logger.critical(f"EMERGENCY KILL-SWITCH ENGAGED by {current_user.username}: {payload.reason}")
    return {
        "status": "EMERGENCY_KILL_SWITCH_ACTIVE",
        "policies_disabled": count,
        "reason": payload.reason,
        "triggered_by": current_user.username
    }

