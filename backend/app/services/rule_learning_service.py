import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.incident import Incident
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
    MIN_PRODUCTION_ACCURACY = 0.95
    MIN_PRODUCTION_FP_PRECISION = 0.99
    MIN_PRODUCTION_WILSON_LOWER = 0.96
    MIN_PRODUCTION_TP_RECALL = 0.95
    MAX_CRITICAL_MISSED_TP = 0

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
        primary_archetype = "UNKNOWN"
        try:
            from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
            from app.services.detection_archetype_registry import DetectionArchetypeRegistry
            sem = RuleIntelligenceAnalyzer.analyze_rule(rule_obj)
            cls_res = DetectionArchetypeRegistry.classify_rule(sem, rule_obj)
            primary_archetype = cls_res.primary_archetype.value
        except Exception:
            if "host_scan" in rule_identifier.lower() or "port_scan" in rule_identifier.lower():
                primary_archetype = "NETWORK_SCAN"
            elif "policy" in rule_identifier.lower():
                primary_archetype = "POLICY_VIOLATION"

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
                min_fp_precision=0.99,
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
                await cls._trigger_critical_missed_tp_suspension(
                    db=db,
                    profile=profile,
                    reason="Automatic suspension triggered by Critical Missed True Positive event",
                )

        # Recalculate statistical metrics
        cls._recalculate_profile_metrics(profile)
        db.add(profile)
        await db.flush()
        return profile

    @classmethod
    async def _trigger_critical_missed_tp_suspension(
        cls,
        db: AsyncSession,
        profile: RuleLearningProfile,
        reason: str,
    ) -> bool:
        """
        Immediately suspends rule lifecycle AND disables ProductionAutomationPolicy
        for the affected rule/tenant scope whenever a verified critical missed TP occurs
        in CONTROLLED_PRODUCTION or MONITORING.
        """
        from app.models.production_governance import ProductionAutomationPolicy
        from app.models.prompt import RulePrompt

        if profile.lifecycle_stage not in (cls.STAGE_CONTROLLED_PRODUCTION, cls.STAGE_MONITORING):
            return False

        logger.critical(
            f"CRITICAL MISSED TRUE POSITIVE on rule {profile.rule_identifier} [{profile.customer}]. "
            f"Triggering immediate automatic suspension and disabling FP auto-closure!"
        )
        await cls.transition_lifecycle_stage(
            db=db,
            profile=profile,
            new_stage=cls.STAGE_SUSPENDED,
            reason=reason,
            user_id="governor_sentinel",
        )

        # Immediately disable scoped ProductionAutomationPolicy (never touches other rules/tenants)
        pol_res = await db.execute(
            select(ProductionAutomationPolicy).where(
                or_(
                    ProductionAutomationPolicy.profile_id == profile.id,
                    and_(
                        ProductionAutomationPolicy.rule_id == profile.rule_identifier,
                        ProductionAutomationPolicy.customer == profile.customer,
                    ),
                )
            )
        )
        for pol in pol_res.scalars().all():
            pol.is_enabled = False
            pol.emergency_disable = True
            db.add(pol)

        # Also flag RulePrompt if present so autonomous execution halts immediately
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == profile.rule_id))
        rp = rp_res.scalar_one_or_none()
        if rp:
            rp.ai_execution_suspended = True
            rp.suspension_reason = reason
            db.add(rp)

        await db.flush()
        return True

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
            if new_outcome == "CRITICAL_MISSED_TP":
                await cls._trigger_critical_missed_tp_suspension(
                    db=db,
                    profile=profile,
                    reason="Automatic suspension triggered by Critical Missed True Positive discovered via verdict correction/adjudication",
                )

        cls._recalculate_profile_metrics(profile)
        db.add(profile)
        await db.flush()
        return profile

    @classmethod
    def _recalculate_profile_metrics(cls, profile: RuleLearningProfile) -> None:
        """
        Computes exact empirical classification metrics, Wilson confidence bounds,
        and populates authoritative confusion matrix keys.
        """
        err_dist = dict(profile.error_distribution or {})
        agreed_fp = err_dist.get("agreement_fp", 0)  # TN (AI: FP, Analyst: FP)
        missed_tp = err_dist.get("critical_missed_tp", 0)  # FN (AI: FP, Analyst: TP)
        agreed_tp = err_dist.get("agreement_tp", 0)  # TP (AI: TP, Analyst: TP)
        false_alarm = err_dist.get("ai_false_alarm", 0)  # FP (AI: TP, Analyst: FP)

        # Total decisive automated predictions (excluding abstentions)
        total_decisive = agreed_tp + agreed_fp + false_alarm + missed_tp
        if total_decisive > 0:
            profile.empirical_accuracy = round(float(agreed_tp + agreed_fp) / float(total_decisive), 4)
        else:
            profile.empirical_accuracy = None

        # FP-Class Precision (precision of benign/FP predictions): TN / (TN + FN)
        total_fp_pred = agreed_fp + missed_tp
        if total_fp_pred > 0:
            profile.fp_precision = round(float(agreed_fp) / float(total_fp_pred), 4)
            profile.wilson_lower_bound = WilsonScoreEvaluator.calculate_lower_bound(
                successes=agreed_fp,
                total=total_fp_pred
            )
        else:
            profile.fp_precision = None
            profile.wilson_lower_bound = None

        # TP-Class Precision: TP / (TP + FP)
        total_tp_pred = agreed_tp + false_alarm
        tp_precision = round(float(agreed_tp) / float(total_tp_pred), 4) if total_tp_pred > 0 else None

        # TP Recall (Sensitivity): TP / (TP + FN)
        total_actual_tp = agreed_tp + missed_tp
        if total_actual_tp > 0:
            profile.tp_recall = round(float(agreed_tp) / float(total_actual_tp), 4)
        else:
            profile.tp_recall = None

        # Specificity (True Negative Rate): TN / (TN + FP)
        total_actual_fp = agreed_fp + false_alarm
        specificity = round(float(agreed_fp) / float(total_actual_fp), 4) if total_actual_fp > 0 else None

        # Store normalized matrix & metric keys in error_distribution
        err_dist["tp"] = agreed_tp
        err_dist["fp"] = false_alarm
        err_dist["tn"] = agreed_fp
        err_dist["fn"] = missed_tp
        err_dist["tp_as_tp"] = agreed_tp
        err_dist["fp_as_tp"] = false_alarm
        err_dist["tp_as_fp"] = missed_tp
        err_dist["fp_as_fp"] = agreed_fp
        err_dist["agreement_tp"] = agreed_tp
        err_dist["ai_false_alarm"] = false_alarm
        err_dist["critical_missed_tp"] = missed_tp
        err_dist["agreement_fp"] = agreed_fp
        err_dist["tp_precision"] = tp_precision
        err_dist["fp_precision"] = profile.fp_precision
        err_dist["specificity"] = specificity
        err_dist["tp_recall"] = profile.tp_recall
        err_dist["selective_accuracy"] = profile.empirical_accuracy
        err_dist["decisive_evaluations"] = total_decisive
        profile.error_distribution = err_dist

    @classmethod
    def check_production_eligibility(cls, profile: RuleLearningProfile) -> Tuple[bool, List[str]]:
        """
        Determines whether a detection rule satisfies all empirical requirements for CONTROLLED_PRODUCTION:
          - >= 100 eligible verified TP/FP evaluations (abstentions/disputes excluded)
          - >= 25 verified TP and >= 50 verified FP cases
          - >= 95.0% verified rule accuracy
          - 0 observed critical missed TPs
          - >= 99.0% observed FP precision
          - >= 96.0% Wilson 95% lower confidence bound
          - >= 95.0% TP recall
        Returns (is_eligible, list_of_reasons).
        """
        reasons = []
        eligible_eval_count = int((profile.ai_correct_count or 0) + (profile.ai_incorrect_count or 0))
        err_dist = profile.error_distribution or {}
        missed_tp_count = int(err_dist.get("critical_missed_tp", 0))

        if eligible_eval_count < cls.MIN_PRODUCTION_SAMPLES:
            reasons.append(
                f"Insufficient eligible verified TP/FP evaluations: {eligible_eval_count}/{cls.MIN_PRODUCTION_SAMPLES} required (total reviews: {profile.total_analyst_reviews})."
            )
        if profile.verified_tp_count < cls.MIN_PRODUCTION_TP:
            reasons.append(
                f"Insufficient True Positive cases: {profile.verified_tp_count}/{cls.MIN_PRODUCTION_TP} required."
            )
        if profile.verified_fp_count < cls.MIN_PRODUCTION_FP:
            reasons.append(
                f"Insufficient False Positive cases: {profile.verified_fp_count}/{cls.MIN_PRODUCTION_FP} required."
            )

        if profile.empirical_accuracy is None:
            reasons.append(
                f"Verified Rule Accuracy: NOT MEASURABLE ({eligible_eval_count} eligible evaluations; >={cls.MIN_PRODUCTION_ACCURACY*100:.1f}% required)."
            )
        elif profile.empirical_accuracy < cls.MIN_PRODUCTION_ACCURACY:
            reasons.append(
                f"Verified Rule Accuracy ({profile.empirical_accuracy*100:.1f}%) below requirement ({cls.MIN_PRODUCTION_ACCURACY*100:.1f}%)."
            )

        if missed_tp_count > cls.MAX_CRITICAL_MISSED_TP:
            reasons.append(
                f"Critical Missed True Positives detected ({missed_tp_count}); promotion strictly requires 0 observed missed TPs."
            )

        if profile.fp_precision is None:
            reasons.append(
                f"Observed FP Precision: NOT MEASURABLE (0 AI FP evaluations; >={cls.MIN_PRODUCTION_FP_PRECISION*100:.1f}% required)."
            )
        elif profile.fp_precision < cls.MIN_PRODUCTION_FP_PRECISION:
            reasons.append(
                f"Observed FP Precision ({profile.fp_precision*100:.1f}%) below requirement ({cls.MIN_PRODUCTION_FP_PRECISION*100:.1f}%)."
            )

        if profile.wilson_lower_bound is None:
            reasons.append(
                f"Wilson 95% lower confidence bound: NOT MEASURABLE (>={cls.MIN_PRODUCTION_WILSON_LOWER*100:.1f}% required)."
            )
        elif profile.wilson_lower_bound < cls.MIN_PRODUCTION_WILSON_LOWER:
            reasons.append(
                f"Wilson 95% lower confidence bound ({profile.wilson_lower_bound*100:.1f}%) below safety threshold ({cls.MIN_PRODUCTION_WILSON_LOWER*100:.1f}%)."
            )

        if profile.tp_recall is None:
            reasons.append(
                f"TP Recall: NOT MEASURABLE (0 verified TP evaluations; >={cls.MIN_PRODUCTION_TP_RECALL*100:.1f}% required)."
            )
        elif profile.tp_recall < cls.MIN_PRODUCTION_TP_RECALL:
            reasons.append(
                f"TP Recall ({profile.tp_recall*100:.1f}%) below requirement ({cls.MIN_PRODUCTION_TP_RECALL*100:.1f}%)."
            )

        is_eligible = len(reasons) == 0
        return is_eligible, reasons

    @classmethod
    async def evaluate_rule_accuracy(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str = "DEFAULT",
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authoritative evaluation and reconciliation of empirical rule accuracy.
        Audits all AnalystVerdictReview records against Incident AI determinations,
        computes decisive classification metrics (Selective Accuracy, TP Recall,
        FP-Class Precision, Specificity, Wilson 95% confidence bounds),
        evaluates class balance (Tier 2 Pilot requires >= 10 TP and >= 10 FP),
        persists updated metrics to RuleLearningProfile, and returns a detailed
        diagnostic breakdown.
        """
        profile = await cls.get_or_create_profile(db=db, rule_id=rule_id, customer=customer)

        stmt = select(Rule).where(or_(Rule.id == rule_id, Rule.rule_id == rule_id))
        res = await db.execute(stmt)
        rule = res.scalar_one_or_none()
        rule_identifiers = [rule_id]
        if rule:
            rule_identifiers = list(set([rule.id, rule.rule_id, rule_id]))

        rule_filter = or_(
            AnalystVerdictReview.rule_id.in_(rule_identifiers),
            Incident.rule_id.in_(rule_identifiers),
            Incident.event_type.in_(rule_identifiers),
        )

        if customer and customer.upper() not in ("ALL", "GLOBAL"):
            if customer.upper() == "DEFAULT":
                cust_filter = or_(
                    AnalystVerdictReview.customer == "DEFAULT",
                    AnalystVerdictReview.customer == "default",
                    AnalystVerdictReview.customer == "",
                    AnalystVerdictReview.customer.is_(None),
                    Incident.customer == "DEFAULT",
                    Incident.customer == "default",
                    Incident.customer == "",
                    Incident.customer.is_(None),
                )
            else:
                cust_filter = or_(
                    AnalystVerdictReview.customer == customer,
                    Incident.customer == customer,
                )
            rev_stmt = (
                select(AnalystVerdictReview)
                .outerjoin(Incident, AnalystVerdictReview.incident_id == Incident.id)
                .where(and_(rule_filter, cust_filter))
            )
        else:
            rev_stmt = (
                select(AnalystVerdictReview)
                .outerjoin(Incident, AnalystVerdictReview.incident_id == Incident.id)
                .where(rule_filter)
            )

        rev_res = await db.execute(rev_stmt)
        all_candidate_reviews = rev_res.scalars().all()

        # Exclude patterned synthetic test fixtures from certified evaluation metrics
        import re
        def is_patterned_test_uuid(val: Optional[str]) -> bool:
            if not val:
                return False
            return bool(re.match(r"^[0-9]0000000-0000-0000-0000-[0-9a-f]{12}$", str(val).strip().lower()))

        reviews = [
            r for r in all_candidate_reviews
            if not is_patterned_test_uuid(r.incident_id) and not is_patterned_test_uuid(r.id)
        ]

        # Audit current operational incident inventory
        inc_stmt = select(Incident).where(
            or_(
                Incident.rule_id.in_(rule_identifiers),
                Incident.event_type.in_(rule_identifiers),
            )
        )
        if customer and customer.upper() not in ("ALL", "GLOBAL"):
            if customer.upper() == "DEFAULT":
                inc_stmt = inc_stmt.where(or_(Incident.customer == "DEFAULT", Incident.customer == "", Incident.customer.is_(None)))
            else:
                inc_stmt = inc_stmt.where(Incident.customer == customer)
        curr_inc_res = await db.execute(inc_stmt)
        curr_incs = curr_inc_res.scalars().all()
        curr_inc_ids = {i.id for i in curr_incs} | {i.incident_id for i in curr_incs if i.incident_id}

        curr_matched_revs = [r for r in reviews if r.incident_id in curr_inc_ids]
        curr_tp = sum(1 for r in curr_matched_revs if (r.analyst_verdict or "").upper() == "TRUE_POSITIVE")
        curr_fp = sum(1 for r in curr_matched_revs if (r.analyst_verdict or "").upper() == "FALSE_POSITIVE")
        curr_abstained = sum(1 for r in curr_matched_revs if (r.revealed_ai_verdict or "").upper() in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE") or (r.comparison_outcome or "").upper() == "ANALYST_RESOLVED_ABSTENTION")

        total_reviews = len(reviews)
        if total_reviews == 0 and (profile.total_analyst_reviews or 0) > 0:
            # Fallback to existing profile counts to preserve verified reviews
            err_dist_prev = dict(profile.error_distribution or {})
            total_reviews = profile.total_analyst_reviews
            verified_tp = profile.verified_tp_count
            verified_fp = profile.verified_fp_count
            agreement_tp = err_dist_prev.get("agreement_tp", 0)
            agreement_fp = err_dist_prev.get("agreement_fp", 0)
            ai_false_alarm = err_dist_prev.get("ai_false_alarm", 0)
            critical_missed_tp = err_dist_prev.get("critical_missed_tp", 0)
            analyst_resolved_abstention = err_dist_prev.get("analyst_resolved_abstention", 0)
            analyst_only_initial_benchmark = err_dist_prev.get("analyst_only_initial_benchmark", 0)
            disputed = err_dist_prev.get("disputed", 0)
        else:
            verified_tp = 0
            verified_fp = 0
            analyst_abstain = 0

            agreement_tp = 0
            agreement_fp = 0
            ai_false_alarm = 0
            critical_missed_tp = 0
            analyst_resolved_abstention = 0
            analyst_only_initial_benchmark = 0
            disputed = 0

            for r in reviews:
                av = (r.analyst_verdict or "").upper().strip()
                if av == "TRUE_POSITIVE":
                    verified_tp += 1
                elif av == "FALSE_POSITIVE":
                    verified_fp += 1
                else:
                    analyst_abstain += 1

                outcome = (r.comparison_outcome or "").upper().strip()
                if outcome == "AGREEMENT_TP":
                    agreement_tp += 1
                elif outcome == "AGREEMENT_FP":
                    agreement_fp += 1
                elif outcome == "AI_FALSE_ALARM":
                    ai_false_alarm += 1
                elif outcome == "CRITICAL_MISSED_TP":
                    critical_missed_tp += 1
                elif outcome == "ANALYST_RESOLVED_ABSTENTION":
                    analyst_resolved_abstention += 1
                elif outcome == "ANALYST_ONLY_INITIAL_BENCHMARK":
                    analyst_only_initial_benchmark += 1
                elif outcome in ("DISPUTED", "AGREEMENT_REQUIRES_ATTENTION"):
                    disputed += 1
                else:
                    ai_v = (r.revealed_ai_verdict or "").upper().strip() if r.revealed_ai_verdict else None
                    if not ai_v:
                        analyst_only_initial_benchmark += 1
                    elif ai_v in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE"):
                        analyst_resolved_abstention += 1
                    elif av == "TRUE_POSITIVE" and ai_v == "TRUE_POSITIVE":
                        agreement_tp += 1
                    elif av == "FALSE_POSITIVE" and ai_v == "FALSE_POSITIVE":
                        agreement_fp += 1
                    elif av == "FALSE_POSITIVE" and ai_v == "TRUE_POSITIVE":
                        ai_false_alarm += 1
                    elif av == "TRUE_POSITIVE" and ai_v == "FALSE_POSITIVE":
                        critical_missed_tp += 1
                    else:
                        disputed += 1

        total_decisive = agreement_tp + agreement_fp + ai_false_alarm + critical_missed_tp
        ai_correct = agreement_tp + agreement_fp
        ai_incorrect = ai_false_alarm + critical_missed_tp

        if total_decisive > 0:
            empirical_accuracy = round(float(ai_correct) / float(total_decisive), 4)
            total_fp_pred = agreement_fp + critical_missed_tp
            fp_precision = round(float(agreement_fp) / float(total_fp_pred), 4) if total_fp_pred > 0 else None
            wilson_lower_bound = WilsonScoreEvaluator.calculate_lower_bound(
                successes=agreement_fp,
                total=total_fp_pred
            ) if total_fp_pred > 0 else None
            total_tp_actual = agreement_tp + critical_missed_tp
            tp_recall = round(float(agreement_tp) / float(total_tp_actual), 4) if total_tp_actual > 0 else None
            total_fp_actual = agreement_fp + ai_false_alarm
            specificity = round(float(agreement_fp) / float(total_fp_actual), 4) if total_fp_actual > 0 else None
            total_tp_pred = agreement_tp + ai_false_alarm
            tp_precision = round(float(agreement_tp) / float(total_tp_pred), 4) if total_tp_pred > 0 else None
        else:
            empirical_accuracy = None
            fp_precision = None
            wilson_lower_bound = None
            tp_recall = None
            specificity = None
            tp_precision = None

        profile.total_analyst_reviews = total_reviews
        profile.verified_tp_count = verified_tp
        profile.verified_fp_count = verified_fp
        profile.ai_correct_count = ai_correct
        profile.ai_incorrect_count = ai_incorrect
        profile.empirical_accuracy = empirical_accuracy
        profile.fp_precision = fp_precision
        profile.wilson_lower_bound = wilson_lower_bound
        profile.tp_recall = tp_recall
        profile.last_evaluated_at = utc_now()

        err_dist = dict(profile.error_distribution or {})
        err_dist["tp"] = agreement_tp
        err_dist["fp"] = ai_false_alarm
        err_dist["tn"] = agreement_fp
        err_dist["fn"] = critical_missed_tp
        err_dist["tp_as_tp"] = agreement_tp
        err_dist["fp_as_tp"] = ai_false_alarm
        err_dist["tp_as_fp"] = critical_missed_tp
        err_dist["fp_as_fp"] = agreement_fp
        err_dist["agreement_tp"] = agreement_tp
        err_dist["agreement_fp"] = agreement_fp
        err_dist["ai_false_alarm"] = ai_false_alarm
        err_dist["critical_missed_tp"] = critical_missed_tp
        err_dist["analyst_resolved_abstention"] = analyst_resolved_abstention
        err_dist["analyst_only_initial_benchmark"] = analyst_only_initial_benchmark
        err_dist["disputed"] = disputed
        err_dist["decisive_evaluations"] = total_decisive
        err_dist["selective_accuracy"] = empirical_accuracy
        err_dist["fp_precision"] = fp_precision
        err_dist["tp_recall"] = tp_recall
        err_dist["tp_precision"] = tp_precision
        err_dist["specificity"] = specificity
        err_dist["current_inventory_incidents"] = len(curr_incs)
        err_dist["current_inventory_reviews"] = len(curr_matched_revs)
        err_dist["current_inventory_verified_tp"] = curr_tp
        err_dist["current_inventory_verified_fp"] = curr_fp
        err_dist["current_inventory_abstained"] = curr_abstained
        profile.error_distribution = err_dist

        is_eligible, reasons = cls.check_production_eligibility(profile)
        profile.is_production_eligible = is_eligible
        profile.eligibility_reasons = reasons

        db.add(profile)
        await db.commit()

        pilot_tp_required = cls.MIN_PILOT_TP
        pilot_fp_required = cls.MIN_PILOT_FP
        is_pilot_balanced = verified_tp >= pilot_tp_required and verified_fp >= pilot_fp_required

        if total_decisive == 0:
            if total_reviews == 0:
                msg = "No analyst reviews exist for this rule. Independent double-blind reviews must be completed to establish ground truth."
            else:
                msg = (
                    f"Accuracy cannot be calculated: 0 eligible decisive AI predictions were found across {total_reviews} historical verified reviews "
                    f"({analyst_resolved_abstention} reviews resolved AI abstentions, and {analyst_only_initial_benchmark} were initial benchmarks without AI inference). "
                    f"Selective Accuracy requires decisive AI predictions (TP or FP) matched against verified analyst verdicts."
                )
        else:
            msg = f"Evaluation complete: {empirical_accuracy * 100:.1f}% empirical accuracy calculated across {total_decisive} decisive comparisons."

        return {
            "success": True,
            "rule_id": rule_id,
            "customer": customer,
            "total_analyst_reviews": total_reviews,
            "verified_tp_count": verified_tp,
            "verified_fp_count": verified_fp,
            "decisive_evaluations": total_decisive,
            "ai_correct_count": ai_correct,
            "ai_incorrect_count": ai_incorrect,
            "empirical_accuracy": empirical_accuracy,
            "fp_precision": fp_precision,
            "wilson_lower_bound": wilson_lower_bound,
            "tp_recall": tp_recall,
            "current_inventory": {
                "population_name": "Current Incident Inventory",
                "total_incidents": len(curr_incs),
                "verified_reviews": len(curr_matched_revs),
                "verified_tp": curr_tp,
                "verified_fp": curr_fp,
                "abstained": curr_abstained,
                "decisive": 0,
            },
            "historical_cohort": {
                "population_name": "Cumulative Historical Ground Truth",
                "total_reviews": total_reviews,
                "verified_tp": verified_tp,
                "verified_fp": verified_fp,
                "abstained": analyst_resolved_abstention,
                "initial_benchmarks_missing_inference": analyst_only_initial_benchmark,
                "decisive": total_decisive,
            },
            "class_balance": {
                "verified_tp": verified_tp,
                "required_pilot_tp": pilot_tp_required,
                "verified_fp": verified_fp,
                "required_pilot_fp": pilot_fp_required,
                "is_balanced": is_pilot_balanced,
                "tp_deficit": max(0, pilot_tp_required - verified_tp),
                "fp_deficit": max(0, pilot_fp_required - verified_fp),
            },
            "breakdown": {
                "agreement_tp": agreement_tp,
                "agreement_fp": agreement_fp,
                "ai_false_alarm": ai_false_alarm,
                "critical_missed_tp": critical_missed_tp,
                "analyst_resolved_abstention": analyst_resolved_abstention,
                "analyst_only_initial_benchmark": analyst_only_initial_benchmark,
                "disputed": disputed,
            },
            "message": msg,
            "last_evaluated_at": profile.last_evaluated_at.isoformat() if profile.last_evaluated_at else None,
        }

    @classmethod
    async def evaluate_full_production_readiness(
        cls,
        db: AsyncSession,
        profile: RuleLearningProfile,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Comprehensive production readiness gate combining empirical metrics,
        zero unresolved disputes, approved prompt/model binding, and G1-G8 quality gates.
        """
        from app.models.prompt import RulePrompt, PromptVersion
        from app.models.policy_quality import PolicyQualityAssessmentRecord

        emp_ok, reasons = cls.check_production_eligibility(profile)
        reasons = list(reasons)

        # Check unresolved critical analyst disputes
        dispute_res = await db.execute(
            select(func.count(AnalystVerdictReview.id)).where(
                and_(
                    or_(
                        AnalystVerdictReview.rule_id == profile.rule_id,
                        AnalystVerdictReview.rule_id == profile.rule_identifier,
                    ),
                    AnalystVerdictReview.ground_truth_status == "DISPUTED",
                )
            )
        )
        unresolved_disputes = int(dispute_res.scalar() or 0)
        if unresolved_disputes > 0:
            reasons.append(f"Unresolved analyst disputes ({unresolved_disputes}) must be adjudicated prior to promotion.")

        # Check approved active prompt version & suspension status
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == profile.rule_id))
        rp = rp_res.scalar_one_or_none()
        approved_version_id = None
        approved_version_number = None
        g1_g8_passed = False
        gates_passed_count = 0

        if not rp or not rp.active_version_id:
            reasons.append("No approved active AIS policy version is bound to this rule.")
        else:
            if getattr(rp, "ai_execution_suspended", False):
                reasons.append(f"AI execution is currently suspended for this rule: {rp.suspension_reason or 'revoked/suspended'}.")
            ver_res = await db.execute(select(PromptVersion).where(PromptVersion.id == rp.active_version_id))
            ver = ver_res.scalar_one_or_none()
            if not ver or ver.status != "APPROVED":
                reasons.append("Active prompt version is not in APPROVED status.")
            else:
                approved_version_id = ver.id
                approved_version_number = ver.version_number
                qa_res = await db.execute(
                    select(PolicyQualityAssessmentRecord)
                    .where(PolicyQualityAssessmentRecord.prompt_version_id == ver.id)
                    .order_by(PolicyQualityAssessmentRecord.evaluated_at.desc())
                    .limit(1)
                )
                latest_qa = qa_res.scalar_one_or_none()
                if not latest_qa or not latest_qa.gate_results:
                    reasons.append("No G1-G8 quality assessment record found for active approved prompt version.")
                else:
                    gates_passed_count = sum(
                        1 for g in latest_qa.gate_results.values()
                        if (g.get("status") if isinstance(g, dict) else getattr(g, "status", "")) == "PASSED"
                    )
                    if gates_passed_count < 8 or (latest_qa.blocking_issues and len(latest_qa.blocking_issues) > 0):
                        reasons.append(f"All G1-G8 quality gates must PASS before production promotion (passed: {gates_passed_count}/8).")
                    else:
                        g1_g8_passed = True

        candidate_draft_id = None
        candidate_draft_number = None
        candidate_draft_status = None
        if rp:
            draft_res = await db.execute(
                select(PromptVersion)
                .where(
                    and_(
                        PromptVersion.prompt_id == rp.id,
                        PromptVersion.status == "DRAFT",
                    )
                )
                .order_by(PromptVersion.version_number.desc())
                .limit(1)
            )
            latest_draft = draft_res.scalar_one_or_none()
            if latest_draft:
                candidate_draft_id = latest_draft.id
                candidate_draft_number = latest_draft.version_number
                candidate_draft_status = latest_draft.status

        eligible_eval_count = int((profile.ai_correct_count or 0) + (profile.ai_incorrect_count or 0))
        metadata = {
            "empirical_gates_passed": emp_ok,
            "unresolved_disputes": unresolved_disputes,
            "approved_prompt_version_id": approved_version_id,
            "approved_prompt_version_number": approved_version_number,
            "candidate_draft_version_id": candidate_draft_id,
            "candidate_draft_version_number": candidate_draft_number,
            "candidate_draft_status": candidate_draft_status,
            "active_model_identifier": profile.active_model_identifier,
            "g1_g8_passed": g1_g8_passed,
            "gates_passed_count": gates_passed_count,
            "critical_missed_tp_count": int((profile.error_distribution or {}).get("critical_missed_tp", 0)),
            "accuracy_status": "MEASURED" if eligible_eval_count > 0 else "NOT_MEASURABLE",
        }
        return (len(reasons) == 0), reasons, metadata

    @classmethod
    async def propose_prompt_improvement_draft(
        cls,
        db: AsyncSession,
        rule_id: str,
        customer: str = "DEFAULT",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inspects verified analyst disagreements for the rule and creates a controlled DRAFT
        candidate prompt version incorporating targeted remediation guidance.
        NEVER mutates the currently approved production prompt or fine-tunes the model.
        """
        from app.services.prompt_studio_service import PromptStudioService
        from app.schemas.prompt import PromptVersionCreate

        profile = await cls.get_or_create_profile(db=db, rule_id=rule_id, customer=customer)
        rev_res = await db.execute(
            select(AnalystVerdictReview).where(
                and_(
                    or_(
                        AnalystVerdictReview.rule_id == profile.rule_id,
                        AnalystVerdictReview.rule_id == profile.rule_identifier,
                    ),
                    AnalystVerdictReview.ground_truth_status.in_(["VERIFIED", "ADJUDICATED"]),
                    AnalystVerdictReview.comparison_outcome.in_(["CRITICAL_MISSED_TP", "AI_FALSE_ALARM", "ANALYST_RESOLVED_ABSTENTION"]),
                )
            ).order_by(AnalystVerdictReview.created_at.desc()).limit(20)
        )
        error_reviews = list(rev_res.scalars().all())

        missed_tps = [r for r in error_reviews if r.comparison_outcome == "CRITICAL_MISSED_TP"]
        false_alarms = [r for r in error_reviews if r.comparison_outcome == "AI_FALSE_ALARM"]
        abstentions = [r for r in error_reviews if r.comparison_outcome == "ANALYST_RESOLVED_ABSTENTION"]

        ps = PromptStudioService(db)
        rp = await ps.get_or_create_rule_prompt(profile.rule_id)
        versions_list = list(rp.versions or [])
        base_ver = next((v for v in versions_list if rp.active_version_id and v.id == rp.active_version_id), None)
        if base_ver is None and versions_list:
            base_ver = versions_list[0]

        tp_additions = []
        fp_additions = []
        abs_additions = []
        for r in missed_tps[:5]:
            note = (r.analyst_notes or r.correction_reason or "Verified missed true positive").strip()[:200]
            tp_additions.append(f"- [Feedback Lesson — Missed TP]: {note}")
        for r in false_alarms[:5]:
            note = (r.analyst_notes or r.correction_reason or "Verified benign operational pattern").strip()[:200]
            fp_additions.append(f"- [Feedback Lesson — False Alarm]: {note}")
        for r in abstentions[:5]:
            note = (r.analyst_notes or "Analyst resolved abstention").strip()[:200]
            abs_additions.append(f"- [Feedback Lesson — Resolved Abstention ({r.analyst_verdict})]: {note}")

        tp_text = ((base_ver.tp_indicators if base_ver else "") or "").strip()
        if tp_additions:
            tp_text = (tp_text + "\n\nVerified Feedback Corrections:\n" + "\n".join(tp_additions)).strip()

        fp_text = ((base_ver.fp_indicators if base_ver else "") or "").strip()
        if fp_additions:
            fp_text = (fp_text + "\n\nVerified Feedback Corrections:\n" + "\n".join(fp_additions)).strip()

        abs_text = ((base_ver.missing_info_criteria if base_ver else "") or "").strip()
        if abs_additions:
            abs_text = (abs_text + "\n\nVerified Feedback Clarifications:\n" + "\n".join(abs_additions)).strip()

        summary = (
            f"Feedback-driven candidate draft from {len(error_reviews)} verified error/abstention cases "
            f"(missed_tp={len(missed_tps)}, false_alarm={len(false_alarms)}, resolved_abstention={len(abstentions)}). "
            f"Requires offline replay and explicit Admin approval before activation."
        )
        base_rule_prompt = ((base_ver.rule_specific_prompt if base_ver else "") or "").strip()
        if len(base_rule_prompt) < 5:
            base_rule_prompt = f"Rule-specific investigation directive for {profile.rule_identifier}"
        draft_payload = PromptVersionCreate(
            common_prompt=(base_ver.common_prompt if base_ver else "") or "",
            rule_specific_prompt=base_rule_prompt,
            detection_conditions=(base_ver.detection_conditions if base_ver else "") or "",
            required_evidence=(base_ver.required_evidence if base_ver else "") or "",
            tp_indicators=tp_text,
            fp_indicators=fp_text,
            missing_info_criteria=abs_text,
            escalation_conditions=(base_ver.escalation_conditions if base_ver else "") or "",
            analyst_questions=list(base_ver.analyst_questions) if (base_ver and base_ver.analyst_questions) else [],
            change_summary=summary[:512],
        )
        draft = await ps.create_draft_version(
            rule_id=profile.rule_id,
            data=draft_payload,
            user_id=user_id,
        )
        return {
            "status": "DRAFT_CREATED",
            "rule_id": profile.rule_id,
            "draft_version_id": draft.id,
            "draft_version_number": draft.version_number,
            "draft_status": draft.status,
            "active_production_prompt_modified": False,
            "error_cases_analyzed": len(error_reviews),
            "breakdown": {
                "critical_missed_tp": len(missed_tps),
                "ai_false_alarm": len(false_alarms),
                "analyst_resolved_abstention": len(abstentions),
            },
            "change_summary": summary,
        }

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

