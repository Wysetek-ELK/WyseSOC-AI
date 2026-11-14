import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.datetime_utils import utc_now
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_learning import RuleLearningProfile
from app.models.policy_drift import PolicyDriftEvent
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.schemas.production_readiness import (
    ReadinessStatus,
    StageStatus,
    ActionButton,
    ReadinessStageItem,
    SmartNextAction,
    ProductionReadinessResponse,
)
from app.schemas.rule_intelligence import SemanticsDefinitionStatus, SourceProvenance
from app.schemas.policy_quality import GateStatus, SimulationStatus
from app.services.policy_governance import (
    resolve_canonical_rule,
    get_rule_semantics_and_contract,
    assess_policy_runtime_certification,
    SIMULATED_PROVIDER_TOKENS,
)
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.rule_learning_service import RuleLearningService

logger = logging.getLogger("ai_verdict.production_readiness")


class ProductionReadinessService:
    """
    Authoritative Production Readiness Evaluation Engine for Agent Intelligence Studio 2.0.
    Evaluates:
      1. Detection Rule Definition Integrity & Semantics Verification
      2. Evidence Contract Feasibility & Core Telemetry Mappings
      3. AI Policy Structural Quality Requirements (G1-G7)
      4. Independent Ground Truth Samples & Analyst Reviews
      5. Empirical AI Accuracy, FP Precision, TP Recall & Wilson Confidence Bound
      6. Production Approval Eligibility & Governance Promotion Safety

    Guarantees:
      - Readiness is strictly calculated from backend verification results (never guessed or inferred).
      - Separates Production Readiness Status from SIEM Baseline Deployment Status.
      - Never treats missing data or N/A as PASS.
      - Never treats raw telemetry field presence as semantic verification.
      - Never marks an offline LLM or simulated replay as live empirical certification.
    """

    @classmethod
    async def evaluate_readiness(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_id: Optional[str] = None,
        customer: str = "DEFAULT",
    ) -> ProductionReadinessResponse:
        clean_id = str(rule_identifier or "").strip()
        rule = await resolve_canonical_rule(db, clean_id)
        if not rule:
            raise ValueError(f"Detection Rule '{rule_identifier}' not found in registry")

        # 1. Resolve RulePrompt and Target PromptVersion
        prompt_q = (
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        prompt_res = await db.execute(prompt_q)
        rule_prompt = prompt_res.scalars().first()

        all_versions: List[PromptVersion] = rule_prompt.versions if (rule_prompt and rule_prompt.versions) else []
        active_version: Optional[PromptVersion] = None
        if rule_prompt and rule_prompt.active_version_id:
            active_version = next((v for v in all_versions if v.id == rule_prompt.active_version_id), None)

        target_version: Optional[PromptVersion] = None
        if version_id:
            target_version = next((v for v in all_versions if str(v.id) == str(version_id)), None)

        if not target_version:
            # Prefer candidate draft version if exists (newer than active), otherwise active, otherwise newest
            drafts = [v for v in all_versions if v.status == "DRAFT"]
            if drafts:
                target_version = drafts[0]
            elif active_version:
                target_version = active_version
            elif all_versions:
                target_version = all_versions[0]

        # 2. Extract Detection Semantics & Machine-Verifiable Evidence Contract
        semantics, contract, snapshot = await get_rule_semantics_and_contract(
            db, rule, prompt_version=target_version, for_quality_validation=True
        )
        classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)

        # Build Plain-English Detection Description
        plain_english_desc = cls._build_plain_english_description(
            rule=rule,
            semantics=semantics,
            archetype_def=archetype_def
        )

        # 3. Resolve Latest Empirical Simulation Run (G8)
        sim_results: Optional[Dict[str, Any]] = None
        if target_version:
            sim_q = (
                select(HistoricalEvaluationRunRecord)
                .where(
                    HistoricalEvaluationRunRecord.rule_id.in_([rule.id, rule.rule_id]),
                    HistoricalEvaluationRunRecord.policy_version_id == str(target_version.id),
                    HistoricalEvaluationRunRecord.status.in_(["COMPLETED", "FAILED"]),
                )
                .order_by(desc(HistoricalEvaluationRunRecord.completed_at), desc(HistoricalEvaluationRunRecord.started_at))
                .limit(1)
            )
            sim_exec = await db.execute(sim_q)
            latest_run = sim_exec.scalars().first()
            if latest_run:
                m_dict = getattr(latest_run, "metrics", {}) or {}
                r_sum = getattr(latest_run, "regression_summary", {}) or {}
                cfg_snap = getattr(latest_run, "config_snapshot", {}) or {}
                eligible_gt = m_dict.get("verified_ground_truth_cases", getattr(latest_run, "verified_ground_truth_cases", 0))
                provider_t = str(cfg_snap.get("provider_type") or ("SIMULATED" if cfg_snap.get("is_simulated") else "UNKNOWN")).upper()
                is_sim = bool(cfg_snap.get("is_simulated")) or provider_t in SIMULATED_PROVIDER_TOKENS

                sim_results = {
                    "simulation_run_id": latest_run.id,
                    "sample_count": getattr(latest_run, "total_cases", 0),
                    "eligible_ground_truth_count": eligible_gt,
                    "verified_ground_truth_cases": eligible_gt,
                    "simulation_status": latest_run.validation_state,
                    "regression_status": r_sum.get("regression_status") or ("NOT_ASSESSED" if not latest_run.baseline_run_id else latest_run.validation_state),
                    "critical_regressions": 1 if latest_run.status == "FAILED" or m_dict.get("critical_false_negatives", 0) > 0 or latest_run.validation_state == "REGRESSION_DETECTED" else 0,
                    "policy_digest": cfg_snap.get("policy_digest"),
                    "provider_type": provider_t,
                    "model_identifier": cfg_snap.get("model_identifier"),
                    "is_simulated": is_sim,
                    "execution_provenance": cfg_snap.get("execution_provenance"),
                    "balanced_accuracy": m_dict.get("balanced_accuracy"),
                    "overall_accuracy": m_dict.get("overall_accuracy"),
                }

        # 4. Evaluate Policy Quality Assessment (G1 through G8)
        quality_score: Optional[float] = None
        gate_results: Dict[str, Any] = {}
        blocking_issues: List[str] = []
        warnings: List[str] = []
        missing_evidence_mappings: List[str] = []
        last_eval_timestamp: Optional[datetime] = None

        if target_version:
            assessment = PolicyQualityValidator.validate_policy_quality(
                rule=rule,
                prompt_version=target_version,
                contract=contract,
                semantics=semantics,
                simulation_results=sim_results,
            )
            quality_score = assessment.quality_score
            gate_results = assessment.gate_results
            blocking_issues = list(assessment.blocking_issues)
            warnings = list(assessment.warnings)
            missing_evidence_mappings = list(assessment.missing_evidence_mappings)
            last_eval_timestamp = assessment.evaluated_at

        # 5. Load Operational Learning Profile & Ground Truth
        profile = await RuleLearningService.get_profile(db=db, rule_id=rule.id, customer=customer)
        total_reviews = profile.total_analyst_reviews if profile else 0
        verified_tp = profile.verified_tp_count if profile else 0
        verified_fp = profile.verified_fp_count if profile else 0
        empirical_accuracy = profile.empirical_accuracy if profile else None
        fp_precision = profile.fp_precision if profile else None
        wilson_lower = profile.wilson_lower_bound if profile else None
        tp_recall = profile.tp_recall if profile else None

        # 6. Check Drift Events & Runtime Certification
        drift_q = select(PolicyDriftEvent).where(
            PolicyDriftEvent.rule_id == rule.id,
            PolicyDriftEvent.acknowledged == False
        )
        unack_drift = (await db.execute(drift_q)).scalars().all()
        blocking_drift_absent = len(unack_drift) == 0

        cert = await assess_policy_runtime_certification(db, rule, target_version)

        # 7. Evaluate Core Gates & Pass/Fail Criteria
        rule_def_verified = (
            semantics.definition_status == SemanticsDefinitionStatus.VERIFIED
            and gate_results.get("G1_RULE_INTEGRITY") is not None
            and gate_results["G1_RULE_INTEGRITY"].status != GateStatus.FAILED
        )

        archetype_relevance_verified = (
            gate_results.get("G2_ARCHETYPE_RELEVANCE") is not None
            and gate_results["G2_ARCHETYPE_RELEVANCE"].status != GateStatus.FAILED
        )

        evidence_contract_verified = (
            contract is not None
            and len(contract.required_evidence) > 0
            and gate_results.get("G3_EVIDENCE_FEASIBILITY") is not None
            and gate_results["G3_EVIDENCE_FEASIBILITY"].status == GateStatus.PASSED
            and len(missing_evidence_mappings) == 0
        )

        g4_passed = gate_results.get("G4_TP_CRITERIA_VALIDITY") is not None and gate_results["G4_TP_CRITERIA_VALIDITY"].status != GateStatus.FAILED
        g5_passed = gate_results.get("G5_FP_CRITERIA_VALIDITY") is not None and gate_results["G5_FP_CRITERIA_VALIDITY"].status != GateStatus.FAILED
        g6_passed = gate_results.get("G6_ABSTENTION_ESCALATION") is not None and gate_results["G6_ABSTENTION_ESCALATION"].status != GateStatus.FAILED
        g7_passed = gate_results.get("G7_POLICY_CONSISTENCY") is not None and gate_results["G7_POLICY_CONSISTENCY"].status != GateStatus.FAILED

        policy_structural_passed = (
            target_version is not None
            and quality_score is not None
            and quality_score >= 70.0
            and len(blocking_issues) == 0
            and g4_passed
            and g5_passed
            and g6_passed
            and g7_passed
        )

        pilot_reviews_passed = total_reviews >= RuleLearningService.MIN_PILOT_SAMPLES
        prod_reviews_passed = (
            total_reviews >= RuleLearningService.MIN_PRODUCTION_SAMPLES
            and verified_tp >= RuleLearningService.MIN_PRODUCTION_TP
            and verified_fp >= RuleLearningService.MIN_PRODUCTION_FP
        )

        fp_precision_passed = fp_precision is not None and fp_precision >= RuleLearningService.MIN_PRODUCTION_FP_PRECISION
        wilson_passed = wilson_lower is not None and wilson_lower >= RuleLearningService.MIN_PRODUCTION_WILSON_LOWER
        tp_recall_passed = tp_recall is not None and tp_recall >= RuleLearningService.MIN_PRODUCTION_TP_RECALL

        sim_passed = (
            gate_results.get("G8_SIMULATION_REGRESSION") is not None
            and gate_results["G8_SIMULATION_REGRESSION"].status == GateStatus.PASSED
            and sim_results is not None
            and not sim_results.get("is_simulated")
        )

        # Count passed gates (out of 8)
        passed_gates_count = sum(1 for g in gate_results.values() if g.status == GateStatus.PASSED)

        # 8. Compile All Blocking Requirements
        blocking_requirements: List[str] = []
        if not rule_def_verified:
            blocking_requirements.append("Authoritative FortiSIEM correlation conditions & thresholds unverified")
        if not evidence_contract_verified:
            if missing_evidence_mappings:
                blocking_requirements.append(f"Unmapped mandatory evidence fields: {', '.join(missing_evidence_mappings)}")
            else:
                blocking_requirements.append("Evidence Contract feasibility unverified")
        if not policy_structural_passed:
            if quality_score is not None and quality_score < 70.0:
                blocking_requirements.append(f"Policy Quality Score ({quality_score}/100) below 70 minimum threshold")
            for b in blocking_issues:
                if b not in blocking_requirements:
                    blocking_requirements.append(b)
        if not pilot_reviews_passed:
            blocking_requirements.append(f"Insufficient ground truth reviews ({total_reviews}/{RuleLearningService.MIN_PILOT_SAMPLES} for pilot)")
        if not sim_passed:
            blocking_requirements.append("Non-simulated empirical regression simulation (G8) required on active policy digest")
        if not blocking_drift_absent:
            blocking_requirements.append(f"{len(unack_drift)} unacknowledged drift event(s) detected")

        # Approval eligibility (strict server-side gate)
        approval_eligible = (
            rule_def_verified
            and evidence_contract_verified
            and policy_structural_passed
            and pilot_reviews_passed
            and blocking_drift_absent
            and len(blocking_issues) == 0
        )

        # 9. Build The 6 Guided Checklist Stages
        stages: List[ReadinessStageItem] = []

        # Stage 1: Define Detection
        s1_status = (
            StageStatus.COMPLETED if (rule_def_verified and archetype_relevance_verified)
            else StageStatus.BLOCKED if (semantics.definition_status in (SemanticsDefinitionStatus.INCOMPLETE, SemanticsDefinitionStatus.UNKNOWN))
            else StageStatus.NEEDS_ACTION
        )
        s1_missing = (
            "Authoritative SIEM detection condition and threshold definition missing. "
            "Observed incident counters cannot serve as a verified correlation threshold."
            if not rule_def_verified else None
        )
        s1_next = (
            "Review FortiSIEM correlation threshold definitions and verify semantics in Advanced Configuration."
            if not rule_def_verified else "Authoritative detection conditions and archetype verified."
        )
        stages.append(
            ReadinessStageItem(
                stage_id="define_detection",
                stage_name="Define Detection",
                stage_number=1,
                status=s1_status,
                simple_explanation="Verifies the FortiSIEM correlation conditions, trigger threshold, aggregation window, and detection archetype.",
                missing_requirement=s1_missing,
                next_action=s1_next,
                action_button=ActionButton(
                    label="Inspect Semantics",
                    action="open_tab",
                    target_tab="advanced",
                    target_section="intelligence"
                ),
                technical_details={
                    "definition_status": str(semantics.definition_status.value if hasattr(semantics.definition_status, "value") else semantics.definition_status),
                    "source_provenance": str(semantics.source_provenance.value if hasattr(semantics.source_provenance, "value") else semantics.source_provenance),
                    "primary_archetype": classification.primary_archetype,
                    "threshold": semantics.threshold,
                    "threshold_unit": semantics.threshold_unit,
                    "aggregation_window": semantics.aggregation_window,
                    "g1_gate": gate_results.get("G1_RULE_INTEGRITY").model_dump(mode="json") if gate_results.get("G1_RULE_INTEGRITY") else None,
                    "g2_gate": gate_results.get("G2_ARCHETYPE_RELEVANCE").model_dump(mode="json") if gate_results.get("G2_ARCHETYPE_RELEVANCE") else None,
                }
            )
        )

        # Stage 2: Verify Evidence
        s2_status = (
            StageStatus.COMPLETED if evidence_contract_verified
            else StageStatus.BLOCKED if not rule_def_verified
            else StageStatus.NEEDS_ACTION
        )
        s2_missing = (
            f"Missing mandatory evidence fields: {', '.join(missing_evidence_mappings)}"
            if missing_evidence_mappings
            else ("Evidence contract feasibility unverified or missing core bindings" if not evidence_contract_verified else None)
        )
        s2_next = (
            "Map missing mandatory telemetry fields in the Evidence Contract."
            if not evidence_contract_verified else "All required telemetry fields are mapped and feasible."
        )
        stages.append(
            ReadinessStageItem(
                stage_id="verify_evidence",
                stage_name="Verify Evidence",
                stage_number=2,
                status=s2_status,
                simple_explanation="Ensures all SIEM telemetry fields required to evaluate this attack behavior are present and mapped in the Evidence Contract.",
                missing_requirement=s2_missing,
                next_action=s2_next,
                action_button=ActionButton(
                    label="Inspect Contract",
                    action="open_tab",
                    target_tab="advanced",
                    target_section="contract"
                ),
                technical_details={
                    "contract_status": contract.status if contract else "UNVERIFIED",
                    "core_fields_count": len(contract.required_evidence) if contract else 0,
                    "missing_mappings": missing_evidence_mappings,
                    "g3_gate": gate_results.get("G3_EVIDENCE_FEASIBILITY").model_dump(mode="json") if gate_results.get("G3_EVIDENCE_FEASIBILITY") else None,
                }
            )
        )

        # Stage 3: Validate AI Policy
        s3_status = (
            StageStatus.COMPLETED if policy_structural_passed
            else StageStatus.BLOCKED if (not rule_def_verified or not evidence_contract_verified)
            else StageStatus.NEEDS_ACTION if target_version is not None
            else StageStatus.PENDING
        )
        s3_missing = (
            f"Quality score ({quality_score}/100) below 70 requirement; {len(blocking_issues)} blocking findings detected"
            if not policy_structural_passed and quality_score is not None
            else ("No policy version created yet" if not target_version else None)
        )
        s3_next = (
            "Validate policy quality criteria (G1–G8) and resolve blocking findings."
            if not policy_structural_passed else "AI prompt satisfies all structural quality criteria."
        )
        stages.append(
            ReadinessStageItem(
                stage_id="validate_policy",
                stage_name="Validate AI Policy",
                stage_number=3,
                status=s3_status,
                simple_explanation="Evaluates the AI prompt against quality criteria: true positive indicators, benign false positive assumptions, abstention safety, and consistency.",
                missing_requirement=s3_missing,
                next_action=s3_next,
                action_button=ActionButton(
                    label="Validate Quality",
                    action="trigger_validation",
                    target_tab="overview"
                ),
                technical_details={
                    "quality_score": quality_score,
                    "blocking_issues_count": len(blocking_issues),
                    "g4_gate": gate_results.get("G4_TP_CRITERIA_VALIDITY").model_dump(mode="json") if gate_results.get("G4_TP_CRITERIA_VALIDITY") else None,
                    "g5_gate": gate_results.get("G5_FP_CRITERIA_VALIDITY").model_dump(mode="json") if gate_results.get("G5_FP_CRITERIA_VALIDITY") else None,
                    "g6_gate": gate_results.get("G6_ABSTENTION_ESCALATION").model_dump(mode="json") if gate_results.get("G6_ABSTENTION_ESCALATION") else None,
                    "g7_gate": gate_results.get("G7_POLICY_CONSISTENCY").model_dump(mode="json") if gate_results.get("G7_POLICY_CONSISTENCY") else None,
                }
            )
        )

        # Stage 4: Analyst Learning
        s4_status = (
            StageStatus.COMPLETED if pilot_reviews_passed
            else StageStatus.NEEDS_ACTION if (rule_def_verified and evidence_contract_verified)
            else StageStatus.PENDING
        )
        s4_missing = (
            f"Need {max(0, RuleLearningService.MIN_PILOT_SAMPLES - total_reviews)} more verified reviews for pilot (target: {RuleLearningService.MIN_PILOT_SAMPLES}) and {max(0, RuleLearningService.MIN_PRODUCTION_SAMPLES - total_reviews)} for production (target: {RuleLearningService.MIN_PRODUCTION_SAMPLES})."
            if not pilot_reviews_passed else None
        )
        s4_next = (
            "Conduct independent, double-blind reviews on pending incidents in Analyst Review tab."
            if not pilot_reviews_passed else f"Ground truth calibration established ({total_reviews} verified reviews)."
        )
        stages.append(
            ReadinessStageItem(
                stage_id="analyst_learning",
                stage_name="Analyst Learning",
                stage_number=4,
                status=s4_status,
                simple_explanation="Collects independent, double-blind analyst determinations (TP/FP) on real incidents to establish ground truth calibration.",
                missing_requirement=s4_missing,
                next_action=s4_next,
                action_button=ActionButton(
                    label="Review Incidents",
                    action="open_tab",
                    target_tab="learning"
                ),
                technical_details={
                    "total_analyst_reviews": total_reviews,
                    "verified_tp_count": verified_tp,
                    "verified_fp_count": verified_fp,
                    "pilot_threshold": RuleLearningService.MIN_PILOT_SAMPLES,
                    "production_threshold": RuleLearningService.MIN_PRODUCTION_SAMPLES,
                }
            )
        )

        # Stage 5: Test AI Accuracy
        s5_status = (
            StageStatus.COMPLETED if (sim_passed and fp_precision_passed and wilson_passed and tp_recall_passed)
            else StageStatus.BLOCKED if total_reviews == 0
            else StageStatus.NEEDS_ACTION if pilot_reviews_passed
            else StageStatus.PENDING
        )
        s5_missing = (
            "Accuracy validation requires verified analyst reviews; currently N/A (0 reviews)."
            if total_reviews == 0
            else (
                "Empirical simulation replay required on active policy version with live model"
                if not sim_passed else (
                    f"Statistical requirements: FP Precision {fp_precision or 0:.1%} (req: 98%), Wilson Bound {wilson_lower or 0:.1%} (req: 96%)"
                    if not (fp_precision_passed and wilson_passed) else None
                )
            )
        )
        s5_next = (
            "Perform independent analyst reviews before running accuracy benchmarks."
            if total_reviews == 0
            else (
                "Run simulation replay to validate model accuracy against verified ground truth."
                if not sim_passed else "Statistical accuracy meets production requirements."
            )
        )
        stages.append(
            ReadinessStageItem(
                stage_id="test_accuracy",
                stage_name="Test AI Accuracy",
                stage_number=5,
                status=s5_status,
                simple_explanation="Tests the AI prompt against historical incidents in simulation replay to verify statistical precision (≥98%), recall (≥95%), and confidence (≥96%).",
                missing_requirement=s5_missing,
                next_action=s5_next,
                action_button=ActionButton(
                    label="Run Simulation",
                    action="trigger_simulation",
                    target_tab="overview"
                ),
                technical_details={
                    "empirical_accuracy": empirical_accuracy,
                    "fp_precision": fp_precision,
                    "wilson_lower_bound": wilson_lower,
                    "tp_recall": tp_recall,
                    "simulation_status": sim_results.get("simulation_status") if sim_results else "NOT_EVALUATED",
                    "simulation_provider": sim_results.get("provider_type") if sim_results else None,
                    "g8_gate": gate_results.get("G8_SIMULATION_REGRESSION").model_dump(mode="json") if gate_results.get("G8_SIMULATION_REGRESSION") else None,
                }
            )
        )

        # Stage 6: Production Approval
        is_target_approved = target_version is not None and target_version.status == "APPROVED"
        s6_status = (
            StageStatus.COMPLETED if (is_target_approved and rule.status == "ACTIVE")
            else StageStatus.NEEDS_ACTION if approval_eligible
            else StageStatus.BLOCKED
        )
        s6_missing = (
            f"Approval blocked by {len(blocking_requirements)} unresolved requirements: {'; '.join(blocking_requirements[:3])}"
            if not approval_eligible and not is_target_approved
            else None
        )
        s6_next = (
            "All prerequisite quality criteria satisfied. Ready for Administrator approval sign-off."
            if approval_eligible and not is_target_approved
            else (
                "Policy version approved and actively deployed in production."
                if is_target_approved else "Resolve blocking stages above to enable production approval."
            )
        )
        stages.append(
            ReadinessStageItem(
                stage_id="production_approval",
                stage_name="Production Approval",
                stage_number=6,
                status=s6_status,
                simple_explanation="Formal governance gate: verifies that all quality criteria pass before an authorized administrator signs off on production deployment.",
                missing_requirement=s6_missing,
                next_action=s6_next,
                action_button=ActionButton(
                    label="Approve Policy",
                    action="request_approval",
                    target_tab="overview"
                ),
                technical_details={
                    "target_version_status": target_version.status if target_version else "NONE",
                    "rule_status": rule.status,
                    "approval_eligible": approval_eligible,
                    "dual_key_required": True,
                }
            )
        )

        # 10. Derive Smart Next Action (Priority Cascade)
        smart_action = cls._derive_smart_next_action(
            rule_def_verified=rule_def_verified,
            evidence_contract_verified=evidence_contract_verified,
            policy_structural_passed=policy_structural_passed,
            total_reviews=total_reviews,
            sim_passed=sim_passed,
            fp_precision_passed=fp_precision_passed,
            wilson_passed=wilson_passed,
            tp_recall_passed=tp_recall_passed,
            approval_eligible=approval_eligible,
            is_target_approved=is_target_approved,
            rule_status=rule.status,
            quality_score=quality_score,
            blocking_issues_count=len(blocking_issues),
            missing_evidence_count=len(missing_evidence_mappings),
        )

        # 11. Derive Overall Production Readiness Status
        readiness_status, readiness_label = cls._derive_readiness_status(
            rule_def_verified=rule_def_verified,
            evidence_contract_verified=evidence_contract_verified,
            policy_structural_passed=policy_structural_passed,
            total_reviews=total_reviews,
            sim_passed=sim_passed,
            fp_precision_passed=fp_precision_passed,
            wilson_passed=wilson_passed,
            approval_eligible=approval_eligible,
            is_target_approved=is_target_approved,
            rule_status=rule.status,
            blocking_drift_absent=blocking_drift_absent,
            definition_status=semantics.definition_status,
        )

        # 12. Calculate Readiness Progress (0-100%)
        completed_stages = sum(1 for s in stages if s.status == StageStatus.COMPLETED)
        readiness_progress = int(round((completed_stages / 6.0) * 100))

        ev_refs: List[str] = []
        if hasattr(contract, "core_fields") and contract.core_fields:
            for item in contract.core_fields:
                if isinstance(item, dict):
                    ev_refs.append(str(item.get("field_name") or item.get("name") or item))
                elif hasattr(item, "field_name"):
                    ev_refs.append(str(item.field_name))
                else:
                    ev_refs.append(str(item))

        return ProductionReadinessResponse(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_identifier=semantics.rule_identifier,
            severity=rule.severity or "MEDIUM",
            detection_archetype=classification.primary_archetype,
            detection_description=plain_english_desc,
            version_id=str(target_version.id) if target_version else None,
            version_number=target_version.version_number if target_version else None,
            version_status=target_version.status if target_version else "NONE",
            rule_deployment_status=rule.status or "ACTIVE",
            deployment_status=rule.status or "ACTIVE",
            active_version_number=active_version.version_number if active_version else None,
            active_version_status=active_version.status if active_version else "NONE",
            readiness_status=readiness_status,
            readiness_label=readiness_label,
            readiness_progress=readiness_progress,
            quality_score=quality_score,
            quality_gates_passed=passed_gates_count,
            total_quality_gates=8,
            verified_reviews_count=total_reviews,
            required_reviews_count=RuleLearningService.MIN_PILOT_SAMPLES,
            production_reviews_target=RuleLearningService.MIN_PRODUCTION_SAMPLES,
            approval_eligible=approval_eligible,
            last_evaluated_at=last_eval_timestamp,
            stages=stages,
            recommended_action=smart_action,
            gate_results=gate_results,
            blocking_requirements=blocking_requirements,
            warnings=warnings,
            supporting_evidence_references=ev_refs,
            metrics={
                "empirical_accuracy": empirical_accuracy,
                "fp_precision": fp_precision,
                "wilson_lower_bound": wilson_lower,
                "tp_recall": tp_recall,
                "verified_tp_count": verified_tp,
                "verified_fp_count": verified_fp,
                "total_analyst_reviews": total_reviews,
                "unacknowledged_drift_events": len(unack_drift),
            }
        )

    @classmethod
    def _build_plain_english_description(
        cls,
        rule: Rule,
        semantics: Any,
        archetype_def: Any
    ) -> str:
        """Constructs an intuitive, L1-friendly plain-English description of the detection rule."""
        if rule.description and len(rule.description.strip()) > 15 and not rule.description.startswith("Detection rule"):
            return rule.description.strip()

        arch_name = archetype_def.name if archetype_def else "Security Detection"
        name = rule.name or semantics.rule_identifier

        if "scan" in name.lower():
            return f"Monitors network traffic for port scanning and reconnaissance behavior matching {name}."
        elif "brute" in name.lower() or "auth" in name.lower() or "login" in name.lower():
            return f"Detects repeated authentication failures and credential brute-force attempts ({name})."
        elif "transfer" in name.lower() or "exfiltration" in name.lower() or "outbound" in name.lower():
            return f"Identifies anomalous high-volume outbound data transfers indicating potential data exfiltration ({name})."
        elif "malware" in name.lower() or "c2" in name.lower():
            return f"Identifies command-and-control communications and malicious process execution ({name})."

        return f"Monitors security telemetry for {arch_name} activity defined by {name}."

    @classmethod
    def _derive_smart_next_action(
        cls,
        rule_def_verified: bool,
        evidence_contract_verified: bool,
        policy_structural_passed: bool,
        total_reviews: int,
        sim_passed: bool,
        fp_precision_passed: bool,
        wilson_passed: bool,
        tp_recall_passed: bool,
        approval_eligible: bool,
        is_target_approved: bool,
        rule_status: str,
        quality_score: Optional[float],
        blocking_issues_count: int,
        missing_evidence_count: int,
    ) -> SmartNextAction:
        """Determines the single highest-priority next action based on actual blocking dependencies."""
        if not rule_def_verified:
            return SmartNextAction(
                title="Verify FortiSIEM Detection Semantics",
                description="Authoritative correlation conditions and thresholds are missing. Review FortiSIEM detection rule specifications to unblock production approval.",
                label="Inspect Semantics",
                target_tab="advanced",
                target_section="intelligence",
                action_type="NAVIGATE",
                status="warning"
            )

        if not evidence_contract_verified:
            return SmartNextAction(
                title="Resolve Missing Evidence Fields",
                description=f"Evidence Contract has {missing_evidence_count} unmapped core fields. Map required telemetry fields to satisfy Gate 3.",
                label="Inspect Contract",
                target_tab="advanced",
                target_section="contract",
                action_type="NAVIGATE",
                status="warning"
            )

        if not policy_structural_passed:
            score_str = f"{quality_score}/100" if quality_score is not None else "Pending"
            return SmartNextAction(
                title="Improve AI Policy Quality",
                description=f"Policy quality score is {score_str} with {blocking_issues_count} blocking findings. Refine prompt sections to meet production standards.",
                label="Run Quality Validation",
                target_tab="overview",
                action_type="VALIDATE_QUALITY",
                status="primary"
            )

        if total_reviews < RuleLearningService.MIN_PILOT_SAMPLES:
            return SmartNextAction(
                title="Review Pending Incidents",
                description=f"Ground truth dataset requires at least {RuleLearningService.MIN_PILOT_SAMPLES} verified analyst reviews (currently {total_reviews}). Conduct double-blind evaluations on pending incidents.",
                label="Review Incidents",
                target_tab="learning",
                action_type="NAVIGATE",
                status="primary"
            )

        if not sim_passed:
            return SmartNextAction(
                title="Run Simulation & Accuracy Validation",
                description="Sufficient ground truth is available. Run simulation replay to validate AI accuracy against historical incidents.",
                label="Run Simulation",
                target_tab="overview",
                action_type="RUN_SIMULATION",
                status="primary"
            )

        if not (fp_precision_passed and wilson_passed and tp_recall_passed):
            return SmartNextAction(
                title="Expand Ground Truth Sample Reviews",
                description="Current FP precision or Wilson confidence is below production thresholds (98% precision, 96% Wilson bound). Continue reviewing incidents to expand sample size.",
                label="Review Queue",
                target_tab="learning",
                action_type="NAVIGATE",
                status="primary"
            )

        if approval_eligible and not is_target_approved:
            return SmartNextAction(
                title="Request Production Approval",
                description="All quality gates and empirical accuracy benchmarks have passed. The policy is eligible for production sign-off.",
                label="Approve & Activate",
                target_tab="overview",
                action_type="APPROVE",
                status="success"
            )

        return SmartNextAction(
            title="Monitor Production Performance",
            description="Policy is active in production. Monitor drift alerts and review newly flagged incidents to maintain calibration.",
            label="View Drift Monitor",
            target_tab="advanced",
            target_section="drift",
            action_type="NAVIGATE",
            status="normal"
        )

    @classmethod
    def _derive_readiness_status(
        cls,
        rule_def_verified: bool,
        evidence_contract_verified: bool,
        policy_structural_passed: bool,
        total_reviews: int,
        sim_passed: bool,
        fp_precision_passed: bool,
        wilson_passed: bool,
        approval_eligible: bool,
        is_target_approved: bool,
        rule_status: str,
        blocking_drift_absent: bool,
        definition_status: Any,
    ) -> Tuple[ReadinessStatus, str]:
        """Calculates authoritative production readiness status without conflating deployment status."""
        def_val = definition_status.value if hasattr(definition_status, "value") else str(definition_status)
        if not rule_def_verified or def_val in ("INCOMPLETE", "UNKNOWN") or not blocking_drift_absent:
            return ReadinessStatus.BLOCKED, "Blocked / Incomplete"

        if not evidence_contract_verified or not policy_structural_passed:
            return ReadinessStatus.BLOCKED, "Blocked / Quality Gaps"

        if total_reviews < RuleLearningService.MIN_PILOT_SAMPLES:
            return ReadinessStatus.LEARNING, "Supervised Learning"

        if not sim_passed or not fp_precision_passed or not wilson_passed:
            return ReadinessStatus.VALIDATING, "Validating Accuracy"

        if approval_eligible and not is_target_approved:
            return ReadinessStatus.READY_FOR_APPROVAL, "Ready for Approval"

        if is_target_approved:
            if rule_status == "ACTIVE":
                return ReadinessStatus.ACTIVE, "Active in Production"
            return ReadinessStatus.APPROVED, "Approved Baseline"

        return ReadinessStatus.VALIDATING, "Validating"
