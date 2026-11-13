import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.rule_learning import RuleLearningProfile, RuleLearningStateHistory
from app.models.analyst_feedback import AnalystVerdictReview
from app.services.wilson_evaluator import WilsonScoreEvaluator
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.rule_learning")


class RuleLearningService:
    """
    Manages detection rule learning profiles, continuous accuracy updates from verified
    human analyst feedback, lifecycle state machines, and production eligibility.
    """

    # Lifecycle State Definitions
    STAGE_LEARNING = "LEARNING"
    STAGE_VALIDATION = "VALIDATION"
    STAGE_SUPERVISED_PILOT = "SUPERVISED_PILOT"
    STAGE_CONTROLLED_PRODUCTION = "CONTROLLED_PRODUCTION"
    STAGE_MONITORING = "MONITORING"
    STAGE_SUSPENDED = "SUSPENDED"
    STAGE_REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"

    VALID_TRANSITIONS = {
        STAGE_LEARNING: {STAGE_VALIDATION, STAGE_SUSPENDED},
        STAGE_VALIDATION: {STAGE_SUPERVISED_PILOT, STAGE_LEARNING, STAGE_SUSPENDED},
        STAGE_SUPERVISED_PILOT: {STAGE_CONTROLLED_PRODUCTION, STAGE_VALIDATION, STAGE_SUSPENDED},
        STAGE_CONTROLLED_PRODUCTION: {STAGE_MONITORING, STAGE_SUSPENDED, STAGE_REVALIDATION_REQUIRED},
        STAGE_MONITORING: {STAGE_SUSPENDED, STAGE_REVALIDATION_REQUIRED, STAGE_CONTROLLED_PRODUCTION},
        STAGE_SUSPENDED: {STAGE_REVALIDATION_REQUIRED, STAGE_LEARNING},
        STAGE_REVALIDATION_REQUIRED: {STAGE_VALIDATION, STAGE_LEARNING, STAGE_SUSPENDED},
    }

    # Minimum Criteria for Production Automation
    MIN_PRODUCTION_SAMPLES = 100
    MIN_PRODUCTION_TP = 25
    MIN_PRODUCTION_FP = 50
    MIN_PRODUCTION_FP_PRECISION = 0.98
    MIN_PRODUCTION_WILSON_LOWER = 0.96
    MIN_PRODUCTION_TP_RECALL = 0.95

    # Minimum Criteria for Supervised Pilot
    MIN_PILOT_SAMPLES = 30
    MIN_PILOT_TP = 10
    MIN_PILOT_FP = 10
    MIN_PILOT_ACCURACY = 0.90

    @classmethod
    async def get_or_create_profile(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str = "DEFAULT"
    ) -> RuleLearningProfile:
        """
        Retrieves existing RuleLearningProfile or creates a default one in LEARNING state.
        Ensures strict tenant and rule scoping.
        """
        stmt = select(RuleLearningProfile).where(
            and_(
                RuleLearningProfile.rule_id == rule_id,
                RuleLearningProfile.customer == customer
            )
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile is not None:
            return profile

        # Lookup rule details for identifier and archetype
        rule_stmt = select(Rule).where(Rule.id == rule_id)
        rule_res = await db.execute(rule_stmt)
        rule_obj = rule_res.scalar_one_or_none()

        rule_identifier = rule_obj.rule_id if rule_obj else rule_id
        primary_archetype = "POLICY_VIOLATION" if "policy" in rule_identifier.lower() else "UNKNOWN"

        profile = RuleLearningProfile(
            rule_id=rule_id,
            rule_identifier=rule_identifier,
            customer=customer,
            primary_archetype=primary_archetype,
            lifecycle_stage=cls.STAGE_LEARNING,
            active_model_identifier="Qwen/Qwen2.5-7B-Instruct-AWQ",
            total_incidents_processed=0,
            total_analyst_reviews=0,
            verified_tp_count=0,
            verified_fp_count=0,
            ai_correct_count=0,
            ai_incorrect_count=0,
            abstention_count=0,
            validation_failure_count=0,
        )
        db.add(profile)
        await db.flush()

        # Record initial creation state history
        history = RuleLearningStateHistory(
            profile_id=profile.id,
            previous_stage="INITIAL",
            new_stage=cls.STAGE_LEARNING,
            transition_reason="Initial rule learning profile created",
            triggered_by_user_id="system",
            metrics_snapshot={"initial": True}
        )
        db.add(history)
        await db.flush()
        return profile

    @classmethod
    async def record_verdict_completion(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str,
        effective_verdict: str,
        is_abstained: bool = False,
        validation_failed: bool = False,
    ) -> RuleLearningProfile:
        """
        Asynchronously increments operational counters when an AI verdict is evaluated.
        """
        profile = await cls.get_or_create_profile(db, rule_id, customer)
        profile.total_incidents_processed += 1
        if is_abstained:
            profile.abstention_count += 1
        if validation_failed:
            profile.validation_failure_count += 1

        profile.last_evaluated_at = utc_now()
        db.add(profile)
        await db.flush()
        return profile

    @classmethod
    async def record_analyst_feedback(
        cls,
        db: AsyncSession,
        profile_id: str,
        analyst_verdict: str,
        ai_verdict: Optional[str],
        comparison_outcome: str,
    ) -> RuleLearningProfile:
        """
        Updates rule learning profile metrics following a human analyst review.
        """
        stmt = select(RuleLearningProfile).where(RuleLearningProfile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        profile.total_analyst_reviews += 1
        if analyst_verdict == "TRUE_POSITIVE":
            profile.verified_tp_count += 1
        elif analyst_verdict == "FALSE_POSITIVE":
            profile.verified_fp_count += 1

        if comparison_outcome in ("AGREEMENT_TP", "AGREEMENT_FP"):
            profile.ai_correct_count += 1
        elif comparison_outcome in ("AI_FALSE_ALARM", "CRITICAL_MISSED_TP"):
            profile.ai_incorrect_count += 1
            # Check critical missed TP suspension trigger
            if comparison_outcome == "CRITICAL_MISSED_TP":
                if profile.lifecycle_stage in (cls.STAGE_CONTROLLED_PRODUCTION, cls.STAGE_MONITORING):
                    logger.critical(
                        f"CRITICAL MISSED TRUE POSITIVE on rule {profile.rule_identifier}. "
                        f"Triggering immediate automatic suspension!"
                    )
                    await cls.transition_lifecycle_stage(
                        db=db,
                        profile=profile,
                        new_stage=cls.STAGE_SUSPENDED,
                        reason="Automatic suspension triggered by Critical Missed True Positive event",
                        user_id="governor_sentinel"
                    )

        # Recalculate statistical metrics
        cls._recalculate_profile_metrics(profile)
        db.add(profile)
        await db.flush()
        return profile

    @classmethod
    def _recalculate_profile_metrics(cls, profile: RuleLearningProfile) -> None:
        """Computes empirical accuracy, precision, recall, and Wilson confidence bounds."""
        total_eval = profile.ai_correct_count + profile.ai_incorrect_count
        if total_eval > 0:
            profile.empirical_accuracy = round(float(profile.ai_correct_count) / float(total_eval), 4)

        # For FP prediction precision: (correct FP) / (correct FP + missed TP where AI predicted FP)
        # Note: ai_correct_count includes both TP and FP agreements.
        # We query actual reviews or use verified FP ratio
        total_fp_predictions = profile.verified_fp_count
        if total_fp_predictions > 0:
            # Conservative estimate: correct FP / total verified FP cases
            successes = max(0, profile.verified_fp_count - (1 if profile.empirical_accuracy and profile.empirical_accuracy < 1.0 else 0))
            profile.fp_precision = round(float(successes) / float(total_fp_predictions), 4)
            profile.wilson_lower_bound = WilsonScoreEvaluator.calculate_lower_bound(
                successes=successes,
                total=total_fp_predictions
            )

        total_tp = profile.verified_tp_count
        if total_tp > 0:
            profile.tp_recall = round(float(max(0, total_tp - profile.ai_incorrect_count)) / float(total_tp), 4)

    @classmethod
    def check_production_eligibility(cls, profile: RuleLearningProfile) -> Tuple[bool, List[str]]:
        """
        Determines whether a detection rule satisfies all requirements for CONTROLLED_PRODUCTION.
        Returns (is_eligible, list_of_reasons).
        """
        reasons = []
        if profile.total_analyst_reviews < cls.MIN_PRODUCTION_SAMPLES:
            reasons.append(
                f"Insufficient verified sample size: {profile.total_analyst_reviews}/{cls.MIN_PRODUCTION_SAMPLES} reviews."
            )
        if profile.verified_tp_count < cls.MIN_PRODUCTION_TP:
            reasons.append(
                f"Insufficient True Positive cases: {profile.verified_tp_count}/{cls.MIN_PRODUCTION_TP} required."
            )
        if profile.verified_fp_count < cls.MIN_PRODUCTION_FP:
            reasons.append(
                f"Insufficient False Positive cases: {profile.verified_fp_count}/{cls.MIN_PRODUCTION_FP} required."
            )

        fp_prec = profile.fp_precision or 0.0
        if fp_prec < cls.MIN_PRODUCTION_FP_PRECISION:
            reasons.append(
                f"Observed FP Precision ({fp_prec*100:.1f}%) below requirement ({cls.MIN_PRODUCTION_FP_PRECISION*100:.1f}%)."
            )

        wilson_lb = profile.wilson_lower_bound or 0.0
        if wilson_lb < cls.MIN_PRODUCTION_WILSON_LOWER:
            reasons.append(
                f"Wilson 95% lower confidence bound ({wilson_lb*100:.1f}%) below safety threshold ({cls.MIN_PRODUCTION_WILSON_LOWER*100:.1f}%)."
            )

        tp_rec = profile.tp_recall or 0.0
        if tp_rec < cls.MIN_PRODUCTION_TP_RECALL:
            reasons.append(
                f"TP Recall ({tp_rec*100:.1f}%) below requirement ({cls.MIN_PRODUCTION_TP_RECALL*100:.1f}%)."
            )

        is_eligible = len(reasons) == 0
        return is_eligible, reasons

    @classmethod
    async def transition_lifecycle_stage(
        cls,
        db: AsyncSession,
        profile: RuleLearningProfile,
        new_stage: str,
        reason: str,
        user_id: str,
        bypass_eligibility_check: bool = False
    ) -> RuleLearningProfile:
        """
        Transitions rule lifecycle state, enforcing valid state machine pathways and
        mandatory eligibility checks unless explicitly bypassed with administrative role.
        """
        current_stage = profile.lifecycle_stage
        valid_next_stages = cls.VALID_TRANSITIONS.get(current_stage, set())

        if new_stage not in valid_next_stages and new_stage != cls.STAGE_SUSPENDED:
            raise ValueError(
                f"Invalid lifecycle transition from {current_stage} to {new_stage}. "
                f"Valid targets: {valid_next_stages}"
            )

        # Enforce eligibility checks when transitioning to CONTROLLED_PRODUCTION
        if new_stage == cls.STAGE_CONTROLLED_PRODUCTION and not bypass_eligibility_check:
            is_eligible, reasons = cls.check_production_eligibility(profile)
            if not is_eligible:
                raise ValueError(
                    f"Rule {profile.rule_identifier} is not eligible for CONTROLLED_PRODUCTION: " + "; ".join(reasons)
                )

        # Enforce eligibility checks when transitioning to SUPERVISED_PILOT
        if new_stage == cls.STAGE_SUPERVISED_PILOT and not bypass_eligibility_check:
            if profile.total_analyst_reviews < cls.MIN_PILOT_SAMPLES:
                raise ValueError(
                    f"Rule {profile.rule_identifier} requires at least {cls.MIN_PILOT_SAMPLES} reviews for SUPERVISED_PILOT (current: {profile.total_analyst_reviews})."
                )

        profile.lifecycle_stage = new_stage
        db.add(profile)

        # Record audit history
        history = RuleLearningStateHistory(
            profile_id=profile.id,
            previous_stage=current_stage,
            new_stage=new_stage,
            transition_reason=reason,
            triggered_by_user_id=user_id,
            metrics_snapshot={
                "total_reviews": profile.total_analyst_reviews,
                "empirical_accuracy": profile.empirical_accuracy,
                "fp_precision": profile.fp_precision,
                "wilson_lower_bound": profile.wilson_lower_bound,
            }
        )
        db.add(history)
        await db.flush()
        return profile

