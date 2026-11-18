import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_learning import RuleLearningProfile
from app.models.production_governance import (
    RulePromotionRequest,
    RulePromotionApproval,
    ProductionAutomationPolicy
)
from app.services.rule_learning_service import RuleLearningService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.promotion")


class PromotionService:
    """
    Governs formal rule lifecycle promotion requests and dual-key approval sign-offs.
    """

    @classmethod
    async def create_promotion_request(
        cls,
        db: AsyncSession,
        profile_id: str,
        target_stage: str,
        requester_id: str,
        justification: str,
        evaluation_run_id: Optional[str] = None
    ) -> RulePromotionRequest:
        """
        Creates a formal promotion request if the profile meets stage prerequisites.
        """
        from sqlalchemy import or_

        clean_id = str(profile_id or "").strip()
        # 1. Resolve profile by profile.id, rule_id, or rule_identifier
        stmt = select(RuleLearningProfile).where(
            or_(
                RuleLearningProfile.id == clean_id,
                RuleLearningProfile.rule_id == clean_id,
                RuleLearningProfile.rule_identifier == clean_id
            )
        )
        profile = (await db.execute(stmt)).scalars().first()
        if not profile:
            # Fallback: attempt get_or_create_profile by rule identifier
            try:
                profile = await RuleLearningService.get_or_create_profile(db=db, rule_id=clean_id)
            except Exception:
                profile = None

        if not profile:
            raise ValueError(f"Profile or Rule '{profile_id}' not found")

        # 2. Check prerequisites for SUPERVISED_PILOT
        if target_stage == RuleLearningService.STAGE_SUPERVISED_PILOT:
            if profile.total_analyst_reviews < RuleLearningService.MIN_PILOT_SAMPLES:
                raise ValueError(
                    f"Cannot submit promotion request to SUPERVISED_PILOT: Requires at least {RuleLearningService.MIN_PILOT_SAMPLES} verified reviews (current: {profile.total_analyst_reviews})."
                )

        # 3. Check prerequisites for CONTROLLED_PRODUCTION (full empirical + G1-G8 + disputes + approved policy)
        full_meta: Dict[str, Any] = {}
        if target_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
            is_eligible, reasons, full_meta = await RuleLearningService.evaluate_full_production_readiness(db, profile)
            if not is_eligible:
                raise ValueError("Cannot submit promotion request: " + "; ".join(reasons))

        # 4. Prevent duplicate pending promotion requests
        pending_stmt = select(RulePromotionRequest).where(
            and_(
                RulePromotionRequest.profile_id == profile.id,
                RulePromotionRequest.requested_stage == target_stage,
                RulePromotionRequest.status == "PENDING"
            )
        )
        existing_req = (await db.execute(pending_stmt)).scalars().first()
        if existing_req:
            raise ValueError(f"A promotion request for {target_stage} is already pending (ID: {existing_req.id})")

        req = RulePromotionRequest(
            profile_id=profile.id,
            rule_id=profile.rule_identifier,
            customer=profile.customer,
            requested_stage=target_stage,
            current_stage=profile.lifecycle_stage,
            requester_user_id=requester_id,
            status="PENDING",
            evaluation_run_id=evaluation_run_id,
            supporting_metrics={
                "total_reviews": profile.total_analyst_reviews,
                "eligible_evaluations": int((profile.ai_correct_count or 0) + (profile.ai_incorrect_count or 0)),
                "verified_tp_count": profile.verified_tp_count,
                "verified_fp_count": profile.verified_fp_count,
                "empirical_accuracy": profile.empirical_accuracy,
                "fp_precision": profile.fp_precision,
                "wilson_lower_bound": profile.wilson_lower_bound,
                "tp_recall": profile.tp_recall,
                "confusion_matrix": dict(profile.error_distribution or {}),
                "active_model_identifier": profile.active_model_identifier,
                "approved_prompt_version_id": full_meta.get("approved_prompt_version_id"),
                "approved_prompt_version_number": full_meta.get("approved_prompt_version_number"),
                "g1_g8_passed": full_meta.get("g1_g8_passed"),
                "gates_passed_count": full_meta.get("gates_passed_count"),
                "critical_missed_tp_count": full_meta.get("critical_missed_tp_count", 0),
                "unresolved_disputes": full_meta.get("unresolved_disputes", 0),
            },
            justification=justification,
        )
        db.add(req)
        await db.flush()
        return req

    @classmethod
    async def decide_promotion_request(
        cls,
        db: AsyncSession,
        request_id: str,
        approver_id: str,
        action: str,  # APPROVED or REJECTED
        decision_notes: str = "",
        signature: str = ""
    ) -> Dict[str, Any]:
        """
        Processes a formal promotion decision with strict separation of duties
        (requester != approver). Transitions lifecycle stage on approval while keeping
        automatic FP closure disabled until explicitly enabled per rule/tenant.
        """
        stmt = select(RulePromotionRequest).where(RulePromotionRequest.id == request_id)
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise ValueError(f"Promotion request {request_id} not found")

        if req.status != "PENDING":
            raise ValueError(f"Promotion request is already {req.status}")

        norm_action = action.upper().strip()
        if norm_action not in ("APPROVED", "REJECTED"):
            raise ValueError(f"Invalid decision action: {action}")

        # Enforce Separation of Duties on approval (requester cannot self-approve)
        if norm_action == "APPROVED" and str(req.requester_user_id or "").strip().lower() == str(approver_id or "").strip().lower():
            raise ValueError(
                f"Separation of duties violation: requester '{req.requester_user_id}' cannot self-approve promotion request '{req.id}'. A different Administrator or SOC Manager must approve."
            )

        profile = (await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.id == req.profile_id))).scalar_one_or_none()

        # Re-verify full eligibility at approval time before mutating status
        if norm_action == "APPROVED" and profile and req.requested_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
            is_elig, reasons, _ = await RuleLearningService.evaluate_full_production_readiness(db, profile)
            if not is_elig:
                raise ValueError("Rule no longer satisfies CONTROLLED_PRODUCTION requirements at approval time: " + "; ".join(reasons))

        # Record immutable approval entity
        approval = RulePromotionApproval(
            request_id=req.id,
            approver_user_id=approver_id,
            action=norm_action,
            decision_notes=decision_notes,
            approval_signature=signature or f"SIG-{approver_id}-{utc_now().strftime('%Y%m%d%H%M%S')}",
            approved_at=utc_now()
        )
        db.add(approval)
        req.status = norm_action
        db.add(req)

        if norm_action == "APPROVED" and profile:
            # Transition lifecycle state
            await RuleLearningService.transition_lifecycle_stage(
                db=db,
                profile=profile,
                new_stage=req.requested_stage,
                reason=f"Promotion approved by {approver_id}: {decision_notes}",
                user_id=approver_id,
                bypass_eligibility_check=False
            )

            # Ensure scoped ProductionAutomationPolicy exists (strictly disabled until explicit admin enablement!)
            if req.requested_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
                pol_stmt = select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
                pol = (await db.execute(pol_stmt)).scalar_one_or_none()
                if not pol:
                    pol = ProductionAutomationPolicy(
                        profile_id=profile.id,
                        rule_id=profile.rule_identifier,
                        customer=profile.customer,
                        is_enabled=False,
                        allowed_verdicts=["FALSE_POSITIVE"],
                        min_trust_score=8,
                        min_fp_precision=0.99,
                        daily_closure_limit=50,
                        emergency_disable=False
                    )
                    db.add(pol)
                    await db.flush()

        await db.flush()
        return {
            "request_id": req.id,
            "status": req.status,
            "rule_id": req.rule_id,
            "customer": req.customer,
            "requested_stage": req.requested_stage,
            "approver": approver_id,
            "action": norm_action,
            "automation_auto_enabled": False,
            "approved_at": approval.approved_at.isoformat()
        }

    @classmethod
    async def list_promotion_requests(
        cls,
        db: AsyncSession,
        rule_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        customer: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists formal promotion requests and associated approval records."""
        from sqlalchemy import or_, desc

        stmt = select(RulePromotionRequest).order_by(desc(RulePromotionRequest.created_at))
        if rule_id:
            clean = str(rule_id).strip()
            prof_res = await db.execute(
                select(RuleLearningProfile.id, RuleLearningProfile.rule_identifier).where(
                    or_(
                        RuleLearningProfile.id == clean,
                        RuleLearningProfile.rule_id == clean,
                        RuleLearningProfile.rule_identifier == clean,
                    )
                )
            )
            prof_rows = prof_res.all()
            prof_ids = [r[0] for r in prof_rows]
            rule_idents = list({clean} | {r[1] for r in prof_rows if r[1]})
            if prof_ids:
                stmt = stmt.where(or_(RulePromotionRequest.profile_id.in_(prof_ids), RulePromotionRequest.rule_id.in_(rule_idents)))
            else:
                stmt = stmt.where(RulePromotionRequest.rule_id == clean)
        if status_filter:
            stmt = stmt.where(RulePromotionRequest.status == status_filter.upper().strip())
        if customer and customer.upper() not in ("ALL", "GLOBAL"):
            stmt = stmt.where(RulePromotionRequest.customer == customer)

        reqs = (await db.execute(stmt.limit(limit))).scalars().all()
        items: List[Dict[str, Any]] = []
        for req in reqs:
            app_res = await db.execute(
                select(RulePromotionApproval).where(RulePromotionApproval.request_id == req.id)
            )
            approvals = [
                {
                    "approval_id": a.id,
                    "approver_user_id": a.approver_user_id,
                    "action": a.action,
                    "decision_notes": a.decision_notes,
                    "approval_signature": a.approval_signature,
                    "approved_at": a.approved_at.isoformat() if a.approved_at else None,
                }
                for a in app_res.scalars().all()
            ]
            items.append({
                "request_id": req.id,
                "profile_id": req.profile_id,
                "rule_id": req.rule_id,
                "customer": req.customer,
                "current_stage": req.current_stage,
                "requested_stage": req.requested_stage,
                "requester_user_id": req.requester_user_id,
                "status": req.status,
                "evaluation_run_id": req.evaluation_run_id,
                "supporting_metrics": req.supporting_metrics or {},
                "justification": req.justification,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "approvals": approvals,
            })
        return items

    @classmethod
    async def update_automation_policy(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str,
        admin_user_id: str,
        is_enabled: Optional[bool] = None,
        min_trust_score: Optional[int] = None,
        min_fp_precision: Optional[float] = None,
        daily_closure_limit: Optional[int] = None,
        emergency_disable: Optional[bool] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Administrator-only rule/tenant-scoped ProductionAutomationPolicy management.
        Enabling automation strictly requires CONTROLLED_PRODUCTION or MONITORING stage,
        passing production readiness checks, and no active emergency disable.
        """
        profile = await RuleLearningService.get_profile(db=db, rule_id=rule_id, customer=customer)
        if not profile:
            raise ValueError(f"Learning profile not found for rule '{rule_id}' in tenant '{customer}'.")

        pol_stmt = select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
        pol = (await db.execute(pol_stmt)).scalar_one_or_none()
        if not pol:
            pol = ProductionAutomationPolicy(
                profile_id=profile.id,
                rule_id=profile.rule_identifier,
                customer=profile.customer,
                is_enabled=False,
                allowed_verdicts=["FALSE_POSITIVE"],
                min_trust_score=8,
                min_fp_precision=0.99,
                daily_closure_limit=50,
                emergency_disable=False,
            )
            db.add(pol)
            await db.flush()

        if emergency_disable is not None:
            pol.emergency_disable = bool(emergency_disable)
            if pol.emergency_disable:
                pol.is_enabled = False

        if min_trust_score is not None:
            pol.min_trust_score = max(7, min(10, int(min_trust_score)))
        if min_fp_precision is not None:
            pol.min_fp_precision = max(0.99, min(1.0, float(min_fp_precision)))
        if daily_closure_limit is not None:
            pol.daily_closure_limit = max(1, min(500, int(daily_closure_limit)))

        if is_enabled is True:
            if pol.emergency_disable:
                raise ValueError("Cannot enable automation while emergency_disable is active for this rule. Clear emergency disable first.")
            if profile.lifecycle_stage not in (
                RuleLearningService.STAGE_CONTROLLED_PRODUCTION,
                RuleLearningService.STAGE_MONITORING,
            ):
                raise ValueError(
                    f"Cannot enable production automation while rule is in '{profile.lifecycle_stage}'. "
                    "Complete formal Administrator promotion to CONTROLLED_PRODUCTION first."
                )
            elig, reasons, _ = await RuleLearningService.evaluate_full_production_readiness(db, profile)
            if not elig:
                raise ValueError("Cannot enable production automation; readiness checks failed: " + "; ".join(reasons))
            pol.is_enabled = True
        elif is_enabled is False:
            pol.is_enabled = False

        db.add(pol)
        await db.flush()
        logger.info(
            f"Automation policy updated by {admin_user_id} for rule={profile.rule_identifier} [{profile.customer}]: "
            f"is_enabled={pol.is_enabled}, emergency_disable={pol.emergency_disable}, reason={reason}"
        )
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
            "updated_by": admin_user_id,
        }

