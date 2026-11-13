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
        profile = (await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.id == profile_id))).scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        # Check preliminary eligibility if target is CONTROLLED_PRODUCTION
        if target_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
            is_eligible, reasons = RuleLearningService.check_production_eligibility(profile)
            if not is_eligible:
                raise ValueError("Cannot submit promotion request: " + "; ".join(reasons))

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
                "verified_tp_count": profile.verified_tp_count,
                "verified_fp_count": profile.verified_fp_count,
                "empirical_accuracy": profile.empirical_accuracy,
                "fp_precision": profile.fp_precision,
                "wilson_lower_bound": profile.wilson_lower_bound,
                "tp_recall": profile.tp_recall,
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
        Processes a formal promotion decision. If approved, transitions the rule lifecycle
        stage and establishes a default ProductionAutomationPolicy.
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

        # Record approval entity
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

        profile = (await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.id == req.profile_id))).scalar_one_or_none()

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

            # If promoted to CONTROLLED_PRODUCTION, ensure policy exists
            if req.requested_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION:
                pol_stmt = select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
                pol = (await db.execute(pol_stmt)).scalar_one_or_none()
                if not pol:
                    pol = ProductionAutomationPolicy(
                        profile_id=profile.id,
                        rule_id=profile.rule_identifier,
                        customer=profile.customer,
                        is_enabled=True,
                        allowed_verdicts=["FALSE_POSITIVE"],
                        min_trust_score=8,
                        min_fp_precision=0.98,
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
            "requested_stage": req.requested_stage,
            "approver": approver_id,
            "action": norm_action,
            "approved_at": approval.approved_at.isoformat()
        }

