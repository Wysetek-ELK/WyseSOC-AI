import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
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

    # Authoritative canonical metadata fallback for core SIEM rules when no incidents exist in the environment
    KNOWN_CANONICAL_METADATA: Dict[str, Dict[str, Any]] = {
        "40498741-ee6b-4a71-9101-0d6d3f77154c": {
            "rule_id": "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
            "name": "Heavy TCP Host Scan On Fixed Port",
            "event_type": "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
            "severity": "HIGH",
            "category": "Security",
        },
        "9839fa49-40ac-4676-abcc-4c5581ae9e09": {
            "rule_id": "PH_RULE_HEAVY_TCP_HOST_SCAN",
            "name": "Heavy TCP Host Scan",
            "event_type": "PH_RULE_HEAVY_TCP_HOST_SCAN",
            "severity": "HIGH",
            "category": "Security",
        },
    }

    @classmethod
    async def _provision_missing_rule(cls, db: AsyncSession, rule_id: str) -> Rule:
        """
        Dynamically and idempotently provisions a missing detection rule record to satisfy
        foreign key constraints for RuleLearningProfile. Derives metadata directly from
        incident telemetry first, then canonical metadata fallback, then dynamic synthesis.
        """
        import uuid as uuid_mod
        from app.models.incident import Incident

        clean_id = str(rule_id or "").strip()

        # 1. Check if rule already exists under any identifier
        existing_stmt = select(Rule).where(
            or_(
                Rule.id == clean_id,
                Rule.rule_id == clean_id,
                Rule.event_type == clean_id
            )
        )
        existing_rule = (await db.execute(existing_stmt)).scalars().first()
        if existing_rule:
            return existing_rule

        # 2. Check if rule exists in incidents table to inherit authentic SIEM metadata
        inc_stmt = select(Incident).where(
            or_(Incident.rule_id == clean_id, Incident.event_type == clean_id)
        ).limit(1)
        inc_res = await db.execute(inc_stmt)
        sample_inc = inc_res.scalars().first()

        is_valid_uuid = False
        try:
            uuid_mod.UUID(clean_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        final_id = clean_id if is_valid_uuid else str(uuid_mod.uuid4())
        rule_ident = clean_id
        rule_name = f"Detection Rule {clean_id[:8]}"
        event_type = clean_id
        severity = "MEDIUM"
        category = "Security"

        if sample_inc:
            rule_name = sample_inc.title or f"FortiSIEM: {sample_inc.event_type}"
            event_type = sample_inc.event_type or clean_id
            rule_ident = sample_inc.event_type or clean_id
            severity = sample_inc.severity or "MEDIUM"
            category = sample_inc.category or "Security"
        elif clean_id in cls.KNOWN_CANONICAL_METADATA:
            canonical = cls.KNOWN_CANONICAL_METADATA[clean_id]
            rule_ident = canonical["rule_id"]
            rule_name = canonical["name"]
            event_type = canonical["event_type"]
            severity = canonical.get("severity", "HIGH")
            category = canonical.get("category", "Security")

        rule_obj = Rule(
            id=final_id,
            rule_id=rule_ident,
            name=rule_name,
            event_type=event_type,
            description=f"Detection rule '{rule_name}' synchronized from FortiSIEM telemetry.",
            severity=severity,
            status="ACTIVE",
            data_source="FortiSIEM",
            detection_tech="SIEM Rule Engine",
            evaluation_mode="ONLINE",
            pattern_logic="",
            raw_rule_text=f"Rule: {rule_name}\nEventType: {event_type}",
            parsed_metadata={
                "source": "DYNAMIC_TELEMETRY_DISCOVERY",
                "customer": sample_inc.customer if sample_inc else "DEFAULT",
                "category": category,
                "synced_at": utc_now().isoformat(),
            },
        )
        db.add(rule_obj)
        await db.flush()
        logger.info(f"Dynamically provisioned detection rule {rule_name} (UUID: {final_id}) from telemetry")
        return rule_obj

    @classmethod
    async def get_profile(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str = "DEFAULT"
    ) -> Optional[RuleLearningProfile]:
        """
        Pure read query for an existing RuleLearningProfile.
        Never executes background writes, DDL, or database commits during GET operations.
        """
        clean_rule_id = str(rule_id or "").strip()
        clean_customer = str(customer or "DEFAULT").strip() or "DEFAULT"

        # 1. Query by rule_id or rule_identifier with tenant matching
        stmt = select(RuleLearningProfile).where(
            and_(
                or_(
                    RuleLearningProfile.rule_id == clean_rule_id,
                    RuleLearningProfile.rule_identifier == clean_rule_id
                ),
                or_(
                    RuleLearningProfile.customer == clean_customer,
                    RuleLearningProfile.customer == "DEFAULT",
                    clean_customer == "DEFAULT"
                )
            )
        )
        profiles = (await db.execute(stmt)).scalars().all()
        if profiles:
            for p in profiles:
                if p.customer == clean_customer:
                    return p
            return profiles[0]

        # 2. Fallback: check if clean_rule_id matches a Rule record in rules table
        rule_stmt = select(Rule).where(
            or_(
                Rule.id == clean_rule_id,
                Rule.rule_id == clean_rule_id,
                Rule.event_type == clean_rule_id
            )
        )
        rule_obj = (await db.execute(rule_stmt)).scalars().first()
        if rule_obj:
            sec_stmt = select(RuleLearningProfile).where(
                and_(
                    or_(
                        RuleLearningProfile.rule_id == rule_obj.id,
                        RuleLearningProfile.rule_identifier == rule_obj.rule_id
                    ),
                    or_(
                        RuleLearningProfile.customer == clean_customer,
                        RuleLearningProfile.customer == "DEFAULT"
                    )
                )
            )
            sec_profiles = (await db.execute(sec_stmt)).scalars().all()
            if sec_profiles:
                for p in sec_profiles:
                    if p.customer == clean_customer:
                        return p
                return sec_profiles[0]

        return None

    @classmethod
    async def get_or_create_profile(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str = "DEFAULT"
    ) -> RuleLearningProfile:
        """
        Retrieves existing RuleLearningProfile or creates a default one in LEARNING state.
        Ensures strict tenant and rule scoping, foreign-key safety, and durable database commit.
        """
        from sqlalchemy import or_, and_
        from app.models.production_governance import ProductionAutomationPolicy
        from app.models.incident import Incident

        clean_rule_id = str(rule_id or "").strip()
        clean_customer = str(customer or "DEFAULT").strip() or "DEFAULT"

        # 1. First check if profile already exists for this rule and tenant
        stmt = select(RuleLearningProfile).where(
            and_(
                or_(
                    RuleLearningProfile.rule_id == clean_rule_id,
                    RuleLearningProfile.rule_identifier == clean_rule_id
                ),
                or_(
                    RuleLearningProfile.customer == clean_customer,
                    RuleLearningProfile.customer == "DEFAULT",
                    clean_customer == "DEFAULT"
                )
            )
        )
        res = await db.execute(stmt)
        profiles = res.scalars().all()
        if profiles:
            for p in profiles:
                if p.customer == clean_customer:
                    return p
            return profiles[0]

        # 2. Resolve Rule record deterministically
        rule_stmt = select(Rule).where(
            or_(
                Rule.id == clean_rule_id,
                Rule.rule_id == clean_rule_id,
                Rule.event_type == clean_rule_id
            )
        )
        rule_res = await db.execute(rule_stmt)
        rule_obj = rule_res.scalars().first()

        # If rule record is missing, auto-provision to avoid ForeignKeyViolation
        if not rule_obj:
            rule_obj = await cls._provision_missing_rule(db, clean_rule_id)

        effective_rule_id = rule_obj.id
        rule_identifier = rule_obj.rule_id
        primary_archetype = "POLICY_VIOLATION" if "policy" in rule_identifier.lower() else "UNKNOWN"

        # 3. Double-check profile existence by effective_rule_id to avoid unique constraint collisions
        check_stmt = select(RuleLearningProfile).where(
            and_(
                RuleLearningProfile.rule_id == effective_rule_id,
                RuleLearningProfile.customer == clean_customer
            )
        )
        existing = (await db.execute(check_stmt)).scalars().first()
        if existing:
            return existing

        # Count existing incidents processed for this rule
        inc_cnt = 0
        try:
            cnt_q = select(func.count(Incident.id)).where(
                or_(Incident.rule_id == effective_rule_id, Incident.event_type == rule_obj.event_type)
            )
            if clean_customer != "DEFAULT":
                cnt_q = cnt_q.where(Incident.customer == clean_customer)
            inc_cnt = (await db.execute(cnt_q)).scalar() or 0
        except Exception:
            pass

        # 4. Instantiate new RuleLearningProfile in LEARNING state with zero verified reviews
        profile = RuleLearningProfile(
            rule_id=effective_rule_id,
            rule_identifier=rule_identifier,
            customer=clean_customer,
            primary_archetype=primary_archetype,
            lifecycle_stage=cls.STAGE_LEARNING,
            active_model_identifier="Qwen/Qwen2.5-7B-Instruct-AWQ",
            total_incidents_processed=inc_cnt,
            total_analyst_reviews=0,
            verified_tp_count=0,
            verified_fp_count=0,
            ai_correct_count=0,
            ai_incorrect_count=0,
            abstention_count=0,
            validation_failure_count=0,
            error_distribution={},
        )
        db.add(profile)
        await db.flush()

        # 5. Record initial creation state history
        history = RuleLearningStateHistory(
            profile_id=profile.id,
            previous_stage="INITIAL",
            new_stage=cls.STAGE_LEARNING,
            transition_reason="Initial rule learning profile created",
            triggered_by_user_id="system",
            metrics_snapshot={"initial": True, "incidents_baseline": inc_cnt}
        )
        db.add(history)

        # 6. Ensure default ProductionAutomationPolicy exists with auto-closure STRICTLY DISABLED
        pol_stmt = select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
        existing_pol = (await db.execute(pol_stmt)).scalar_one_or_none()
        if not existing_pol:
            pol = ProductionAutomationPolicy(
                profile_id=profile.id,
                rule_id=rule_identifier,
                customer=clean_customer,
                is_enabled=False,  # REQ-05: Automatic closure strictly disabled by default
                allowed_verdicts=["FALSE_POSITIVE"],
                min_trust_score=8,
                min_fp_precision=0.98,
                daily_closure_limit=50,
                emergency_disable=False
            )
            db.add(pol)

        # 7. Commit changes to durable storage
        try:
            await db.commit()
            await db.refresh(profile)
            logger.info(f"Initialized persistent learning profile for rule {rule_identifier} [{clean_customer}]")
        except Exception as exc:
            await db.rollback()
            # Handle concurrent creation race condition gracefully
            recheck = await db.execute(
                select(RuleLearningProfile).where(
                    and_(
                        RuleLearningProfile.rule_id == effective_rule_id,
                        RuleLearningProfile.customer == clean_customer
                    )
                )
            )
            recheck_p = recheck.scalars().first()
            if recheck_p:
                return recheck_p
            raise exc

        return profile

    @classmethod
    async def ensure_all_rules_initialized(cls, db: AsyncSession) -> List[RuleLearningProfile]:
        """
        Idempotently audits and initializes learning profiles for all detection rules in the database,
        ensuring zero rules are left without an accessible learning profile.
        Dynamically derives all detection rules from existing Rule and Incident records.
        """
        from app.models.incident import Incident

        # 1. Query all detection rules in the database
        rules_res = await db.execute(select(Rule))
        all_rules = list(rules_res.scalars().all())

        # 2. Check for any referenced rules in incidents that lack a Rule record
        try:
            orphaned_q = select(Incident.rule_id, Incident.event_type).where(
                or_(Incident.rule_id.isnot(None), Incident.event_type.isnot(None))
            ).distinct()
            orphaned_res = await db.execute(orphaned_q)
            existing_rule_ids = {r.id for r in all_rules} | {r.rule_id for r in all_rules} | {r.event_type for r in all_rules}

            for inc_r_id, inc_e_type in orphaned_res.all():
                ref = inc_r_id or inc_e_type
                if ref and ref not in existing_rule_ids:
                    prov_rule = await cls._provision_missing_rule(db, ref)
                    all_rules.append(prov_rule)
                    existing_rule_ids.add(prov_rule.id)
                    existing_rule_ids.add(prov_rule.rule_id)
                    existing_rule_ids.add(prov_rule.event_type)
        except Exception as e:
            logger.warning(f"Orphaned incident rule check skipped: {e}")

        initialized_profiles: List[RuleLearningProfile] = []

        # 3. Provision profiles for every rule across all discovered customer tenants
        for rule in all_rules:
            target_customers = {"DEFAULT"}
            try:
                cust_q = select(Incident.customer).where(
                    or_(Incident.rule_id == rule.id, Incident.event_type == rule.event_type)
                ).distinct()
                cust_res = await db.execute(cust_q)
                discovered = {c for c in cust_res.scalars().all() if c and str(c).strip()}
                target_customers.update(discovered)
            except Exception:
                pass

            for cust in target_customers:
                prof = await cls.get_or_create_profile(db=db, rule_id=rule.id, customer=cust)
                initialized_profiles.append(prof)

        return initialized_profiles

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
        elif analyst_verdict in ("INSUFFICIENT_EVIDENCE", "ABSTAIN"):
            profile.abstention_count += 1

        # Record distribution in profile error_distribution
        err_dist = dict(profile.error_distribution or {})
        outcome_key = comparison_outcome.lower()
        err_dist[outcome_key] = err_dist.get(outcome_key, 0) + 1
        profile.error_distribution = err_dist

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
    async def adjust_analyst_feedback(
        cls,
        db: AsyncSession,
        profile_id: str,
        old_verdict: str,
        old_outcome: Optional[str],
        new_verdict: str,
        new_outcome: str,
    ) -> RuleLearningProfile:
        """
        Adjusts rule learning profile metrics when an analyst updates their previous verdict,
        maintaining exact-once total reviews and consistent ground truth tallies.
        """
        stmt = select(RuleLearningProfile).where(RuleLearningProfile.id == profile_id)
        profile = (await db.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        # Reverse old counts
        if old_verdict == "TRUE_POSITIVE":
            profile.verified_tp_count = max(0, profile.verified_tp_count - 1)
        elif old_verdict == "FALSE_POSITIVE":
            profile.verified_fp_count = max(0, profile.verified_fp_count - 1)
        elif old_verdict in ("INSUFFICIENT_EVIDENCE", "ABSTAIN"):
            profile.abstention_count = max(0, profile.abstention_count - 1)

        err_dist = dict(profile.error_distribution or {})
        if old_outcome:
            old_key = old_outcome.lower()
            if old_key in err_dist and err_dist[old_key] > 0:
                err_dist[old_key] -= 1
            if old_outcome in ("AGREEMENT_TP", "AGREEMENT_FP"):
                profile.ai_correct_count = max(0, profile.ai_correct_count - 1)
            elif old_outcome in ("AI_FALSE_ALARM", "CRITICAL_MISSED_TP"):
                profile.ai_incorrect_count = max(0, profile.ai_incorrect_count - 1)

        # Apply new counts (total_analyst_reviews remains constant)
        if new_verdict == "TRUE_POSITIVE":
            profile.verified_tp_count += 1
        elif new_verdict == "FALSE_POSITIVE":
            profile.verified_fp_count += 1
        elif new_verdict in ("INSUFFICIENT_EVIDENCE", "ABSTAIN"):
            profile.abstention_count += 1

        new_key = new_outcome.lower()
        err_dist[new_key] = err_dist.get(new_key, 0) + 1
        profile.error_distribution = err_dist

        if new_outcome in ("AGREEMENT_TP", "AGREEMENT_FP"):
            profile.ai_correct_count += 1
        elif new_outcome in ("AI_FALSE_ALARM", "CRITICAL_MISSED_TP"):
            profile.ai_incorrect_count += 1

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

        err_dist = profile.error_distribution or {}
        agreed_fp = err_dist.get("agreement_fp", 0)
        missed_tp = err_dist.get("critical_missed_tp", 0)
        agreed_tp = err_dist.get("agreement_tp", 0)
        false_alarm = err_dist.get("ai_false_alarm", 0)

        # Precision of FP predictions: correct FP / total cases where AI predicted FP
        total_fp_pred = agreed_fp + missed_tp
        if total_fp_pred > 0:
            profile.fp_precision = round(float(agreed_fp) / float(total_fp_pred), 4)
            profile.wilson_lower_bound = WilsonScoreEvaluator.calculate_lower_bound(
                successes=agreed_fp,
                total=total_fp_pred
            )
        elif profile.verified_fp_count > 0:
            successes = max(0, profile.verified_fp_count - (1 if profile.empirical_accuracy and profile.empirical_accuracy < 1.0 else 0))
            profile.fp_precision = round(float(successes) / float(profile.verified_fp_count), 4)
            profile.wilson_lower_bound = WilsonScoreEvaluator.calculate_lower_bound(
                successes=successes,
                total=profile.verified_fp_count
            )

        # Recall of actual True Positives: correctly escalated TP / total verified TP
        total_actual_tp = agreed_tp + missed_tp
        if total_actual_tp > 0:
            profile.tp_recall = round(float(agreed_tp) / float(total_actual_tp), 4)
        elif profile.verified_tp_count > 0:
            profile.tp_recall = round(float(max(0, profile.verified_tp_count - profile.ai_incorrect_count)) / float(profile.verified_tp_count), 4)

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

