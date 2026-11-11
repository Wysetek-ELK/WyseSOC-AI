import re
import hashlib
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from app.utils.datetime_utils import utc_now

from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    ArchetypeId,
    ArchetypeDefinition,
    SemanticsDefinitionStatus,
    SourceProvenance,
)
from app.schemas.policy_quality import (
    GateStatus,
    SimulationStatus,
    QualityGateResult,
    PolicyQualityAssessmentResponse,
)
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import CANONICAL_FIELD_CATALOG

logger = logging.getLogger("ai_verdict.policy_validator")


class PolicyQualityValidator:
    """
    REQ-05 / REQ-06: Central Policy Quality Validation Engine.
    Evaluates both generated and manually edited policies against 8 mandatory gates.
    Calculates a transparent quality score (0 to 100).
    
    CRITICAL SAFETY PRINCIPLE:
      HARD GATE FAILURE STRICTLY OVERRIDES TOTAL SCORE.
      Even if a policy scores 95/100, if an authoritative rule condition is missing,
      an invented threshold is detected, or policy contradicts contract,
      approval_eligible MUST BE FALSE.
    """
    VALIDATOR_VERSION = "v2.0.0"

    # Scoring Weights (Total = 100)
    WEIGHT_DETECTION_SEMANTICS = 20.0
    WEIGHT_EVIDENCE_CONTRACT = 20.0
    WEIGHT_TP_FP_SPECIFICITY = 20.0
    WEIGHT_ABSTENTION_ESCALATION = 15.0
    WEIGHT_INTERNAL_CONSISTENCY = 10.0
    WEIGHT_SIMULATION_QUALITY = 15.0

    @classmethod
    def validate_policy_quality(
        cls,
        rule: Rule,
        prompt_version: PromptVersion,
        contract: Optional[RuleEvidenceContract] = None,
        semantics: Optional[DetectionSemantics] = None,
        simulation_results: Optional[Dict[str, Any]] = None,
    ) -> PolicyQualityAssessmentResponse:
        """
        Executes comprehensive quality validation across G1 through G8.
        Returns a deterministic PolicyQualityAssessmentResponse with exact digest bindings.
        """
        # 1. Resolve Semantics & Classification
        if not semantics:
            semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)

        classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)

        # 2. Extract digests
        policy_digest = cls.compute_policy_digest(prompt_version)
        rule_digest = cls.compute_rule_digest(rule, semantics)
        contract_digest = cls.compute_contract_digest(contract) if contract else "UNBOUND_CONTRACT"

        blocking_issues: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        missing_evidence_mappings: List[str] = []
        gate_results: Dict[str, QualityGateResult] = {}
        score_breakdown: Dict[str, float] = {}

        # -------------------------------------------------------------------------
        # GATE 1: Rule Definition Integrity (Weight: 20 pts)
        # -------------------------------------------------------------------------
        g1_score, g1_status, g1_blockers, g1_warns, g1_details = cls._evaluate_gate_1_integrity(semantics, prompt_version)
        gate_results["G1_RULE_INTEGRITY"] = QualityGateResult(
            gate_id="G1",
            gate_name="Rule Definition Integrity",
            status=g1_status,
            score=g1_score,
            max_score=cls.WEIGHT_DETECTION_SEMANTICS,
            details=g1_details,
            blocking_findings=g1_blockers,
            warnings=g1_warns,
        )
        blocking_issues.extend(g1_blockers)
        warnings.extend(g1_warns)
        score_breakdown["detection_semantics"] = g1_score

        # -------------------------------------------------------------------------
        # GATE 2: Detection Archetype Relevance (Weight evaluated with G1 / G7)
        # -------------------------------------------------------------------------
        g2_status, g2_blockers, g2_warns, g2_details = cls._evaluate_gate_2_relevance(prompt_version, archetype_def, semantics)
        g2_score = cls.WEIGHT_DETECTION_SEMANTICS if g2_status == GateStatus.PASSED else (10.0 if g2_status == GateStatus.WARNING else 0.0)
        gate_results["G2_ARCHETYPE_RELEVANCE"] = QualityGateResult(
            gate_id="G2",
            gate_name="Detection Archetype Relevance",
            status=g2_status,
            score=g2_score,
            max_score=cls.WEIGHT_DETECTION_SEMANTICS,
            details=g2_details,
            blocking_findings=g2_blockers,
            warnings=g2_warns,
        )
        blocking_issues.extend(g2_blockers)
        warnings.extend(g2_warns)

        # Ensure score_breakdown reflects G2 penalty
        if g2_status == GateStatus.WARNING:
            score_breakdown["detection_semantics"] = min(score_breakdown.get("detection_semantics", 20.0), 10.0)
        elif g2_status == GateStatus.FAILED:
            score_breakdown["detection_semantics"] = 0.0

        # -------------------------------------------------------------------------
        # GATE 3: Evidence Contract Feasibility (Weight: 20 pts)
        # -------------------------------------------------------------------------
        g3_score, g3_status, g3_blockers, g3_warns, g3_missing, g3_details = cls._evaluate_gate_3_contract(prompt_version, contract, archetype_def)
        gate_results["G3_EVIDENCE_FEASIBILITY"] = QualityGateResult(
            gate_id="G3",
            gate_name="Evidence Contract Feasibility",
            status=g3_status,
            score=g3_score,
            max_score=cls.WEIGHT_EVIDENCE_CONTRACT,
            details=g3_details,
            blocking_findings=g3_blockers,
            warnings=g3_warns,
        )
        blocking_issues.extend(g3_blockers)
        warnings.extend(g3_warns)
        missing_evidence_mappings.extend(g3_missing)
        score_breakdown["evidence_contract"] = g3_score

        # -------------------------------------------------------------------------
        # GATE 4: TP Criteria Specificity & Validity (Part of 20 pts)
        # -------------------------------------------------------------------------
        g4_score, g4_status, g4_blockers, g4_warns, g4_details = cls._evaluate_gate_4_tp_criteria(prompt_version, archetype_def)
        gate_results["G4_TP_CRITERIA_VALIDITY"] = QualityGateResult(
            gate_id="G4",
            gate_name="TP Criteria Validity",
            status=g4_status,
            score=g4_score,
            max_score=10.0,
            details=g4_details,
            blocking_findings=g4_blockers,
            warnings=g4_warns,
        )
        blocking_issues.extend(g4_blockers)
        warnings.extend(g4_warns)

        # -------------------------------------------------------------------------
        # GATE 5: FP Criteria Validity & Benign Assumptions (Part of 20 pts)
        # -------------------------------------------------------------------------
        g5_score, g5_status, g5_blockers, g5_warns, g5_details = cls._evaluate_gate_5_fp_criteria(prompt_version, archetype_def)
        gate_results["G5_FP_CRITERIA_VALIDITY"] = QualityGateResult(
            gate_id="G5",
            gate_name="FP Criteria & Benign Assumptions",
            status=g5_status,
            score=g5_score,
            max_score=10.0,
            details=g5_details,
            blocking_findings=g5_blockers,
            warnings=g5_warns,
        )
        blocking_issues.extend(g5_blockers)
        warnings.extend(g5_warns)
        score_breakdown["tp_fp_criteria"] = g4_score + g5_score

        # -------------------------------------------------------------------------
        # GATE 6: Abstention & Escalation Safety (Weight: 15 pts)
        # -------------------------------------------------------------------------
        g6_score, g6_status, g6_blockers, g6_warns, g6_details = cls._evaluate_gate_6_abstention_escalation(prompt_version, archetype_def, semantics)
        gate_results["G6_ABSTENTION_ESCALATION"] = QualityGateResult(
            gate_id="G6",
            gate_name="Abstention & Escalation Safety",
            status=g6_status,
            score=g6_score,
            max_score=cls.WEIGHT_ABSTENTION_ESCALATION,
            details=g6_details,
            blocking_findings=g6_blockers,
            warnings=g6_warns,
        )
        blocking_issues.extend(g6_blockers)
        warnings.extend(g6_warns)
        score_breakdown["abstention_escalation"] = g6_score

        # -------------------------------------------------------------------------
        # GATE 7: Policy Consistency (Weight: 10 pts)
        # -------------------------------------------------------------------------
        g7_score, g7_status, g7_blockers, g7_warns, g7_details = cls._evaluate_gate_7_consistency(prompt_version, contract, semantics, archetype_def)
        gate_results["G7_POLICY_CONSISTENCY"] = QualityGateResult(
            gate_id="G7",
            gate_name="Internal Policy & Contract Consistency",
            status=g7_status,
            score=g7_score,
            max_score=cls.WEIGHT_INTERNAL_CONSISTENCY,
            details=g7_details,
            blocking_findings=g7_blockers,
            warnings=g7_warns,
        )
        blocking_issues.extend(g7_blockers)
        warnings.extend(g7_warns)
        score_breakdown["internal_consistency"] = g7_score

        # -------------------------------------------------------------------------
        # GATE 8: Simulation & Regression Evidence (Weight: 15 pts)
        # -------------------------------------------------------------------------
        g8_score, g8_status, sim_status, g8_blockers, g8_warns, g8_details = cls._evaluate_gate_8_simulation(
            simulation_results,
            current_policy_digest=policy_digest,
        )
        gate_results["G8_SIMULATION_REGRESSION"] = QualityGateResult(
            gate_id="G8",
            gate_name="Simulation & Regression Validation",
            status=g8_status,
            score=g8_score,
            max_score=cls.WEIGHT_SIMULATION_QUALITY,
            details=g8_details,
            blocking_findings=g8_blockers,
            warnings=g8_warns,
        )
        blocking_issues.extend(g8_blockers)
        warnings.extend(g8_warns)
        score_breakdown["historical_simulation"] = g8_score

        # 3. Calculate Overall Policy Quality Score (0 to 100) and separate structural health
        structural_raw = (
            score_breakdown.get("detection_semantics", 0.0)
            + score_breakdown.get("evidence_contract", 0.0)
            + score_breakdown.get("tp_fp_criteria", 0.0)
            + score_breakdown.get("abstention_escalation", 0.0)
            + score_breakdown.get("internal_consistency", 0.0)
        )
        structural_score = round(min(100.0, (structural_raw / 85.0) * 100.0), 1)
        total_score = round(sum(score_breakdown.values()), 1)

        # 4. Strict Approval Eligibility Determination
        # MANDATORY: Zero blocking issues allowed. High score does NOT override blocking findings.
        approval_eligible = (len(blocking_issues) == 0)

        # Build comprehensive corrective recommendations covering all failed and warning gates
        seen_recs = set()
        def add_rec(text: str):
            if text and text not in seen_recs:
                seen_recs.add(text)
                recommendations.append(text)

        for gate_key, gate_res in gate_results.items():
            if gate_res.status in (GateStatus.FAILED, GateStatus.WARNING):
                all_findings = gate_res.blocking_findings + gate_res.warnings
                findings_text = " ".join(all_findings).lower()

                if gate_key == "G1_RULE_INTEGRITY":
                    if "incomplete" in findings_text or "threshold" in findings_text:
                        add_rec("Obtain authoritative SIEM rule definition from Supervisor XML/JSON API.")
                    if "invented_threshold" in findings_text:
                        add_rec("Remove fabricated or unverified numeric thresholds from Section 3 detection conditions.")
                    if "auto-synced" in findings_text:
                        add_rec("Verify and augment rule definition from authoritative SIEM configuration.")

                elif gate_key == "G2_ARCHETYPE_RELEVANCE":
                    if "inadequate_telemetry" in findings_text or "unclassified" in findings_text:
                        add_rec("Enrich rule telemetry mappings and bind authoritative detection archetype instead of Unclassified / Inadequate Telemetry.")
                    if "relevance_mismatch" in findings_text or "malware" in findings_text:
                        add_rec("Remove malware-execution directives from network data transfer policy.")

                elif gate_key == "G3_EVIDENCE_FEASIBILITY":
                    if "missing_evidence_contract" in findings_text:
                        add_rec("Bind an authoritative Evidence Contract to the policy version.")
                    elif "unmapped" in findings_text or "critical" in findings_text:
                        add_rec("Map missing contract fields to verifiable telemetry attributes or classify as unmapped context.")

                elif gate_key == "G4_TP_CRITERIA_VALIDITY":
                    add_rec("Define concrete, measurable, and evidence-backed True Positive criteria in Section 5.")

                elif gate_key == "G5_FP_CRITERIA_VALIDITY":
                    if "confidence_range" in findings_text or "prescriptive_confidence" in findings_text:
                        add_rec("Remove hardcoded subjective confidence ranges (e.g. 80-98%) from policy prompt.")
                    if "unsafe_fp" in findings_text or "rfc-1918" in findings_text or "loopback" in findings_text:
                        add_rec("Revise Section 1 & Section 6 to remove blanket benign assumptions on internal or loopback traffic.")
                    if "brief" in findings_text:
                        add_rec("Expand False Positive indicators with specific, observable operational exceptions.")

                elif gate_key == "G6_ABSTENTION_ESCALATION":
                    add_rec("Specify mandatory abstention triggers and human analyst escalation conditions in Sections 7 & 8.")

                elif gate_key == "G7_POLICY_CONSISTENCY":
                    if "critical" in findings_text and ("event_type" in findings_text or "security.event_type" in findings_text):
                        add_rec("Explicitly reference critical contract fields (e.g. security.event_type) in Section 4 required evidence.")
                    elif "contradiction" in findings_text or "contract" in findings_text:
                        add_rec("Align required evidence in Section 4 with machine-verifiable Evidence Contract fields.")
                    else:
                        add_rec("Resolve inconsistencies between policy prompt sections and Evidence Contract requirements.")

                elif gate_key == "G8_SIMULATION_REGRESSION":
                    if "regression" in findings_text:
                        add_rec("Investigate and resolve behavioral regression against approved baseline version on frozen dataset.")
                    elif "insufficient_data" in findings_text or "not been executed" in findings_text:
                        add_rec("Collect at least 5 independently verified, analyst-labeled historical incidents before empirical approval.")

        assessment_id = f"PQA-{semantics.rule_identifier}-V{prompt_version.version_number}-{hashlib.sha256(policy_digest.encode()).hexdigest()[:8]}"

        return PolicyQualityAssessmentResponse(
            assessment_id=assessment_id,
            rule_identifier=semantics.rule_identifier,
            policy_version_number=prompt_version.version_number,
            prompt_version_id=prompt_version.id,
            archetype=archetype_def.archetype_id.value,
            validator_version=cls.VALIDATOR_VERSION,
            quality_score=total_score,
            structural_quality_score=structural_score,
            empirical_validation_score=round(g8_score, 1),
            empirical_validation_status=sim_status.value,
            score_breakdown=score_breakdown,
            gate_results=gate_results,
            blocking_issues=blocking_issues,
            warnings=warnings,
            missing_evidence_mappings=missing_evidence_mappings,
            recommendations=recommendations,
            simulation_status=sim_status,
            approval_eligible=approval_eligible,
            policy_digest=policy_digest,
            contract_digest=contract_digest,
            rule_digest=rule_digest,
            archetype_version=archetype_def.version,
            evaluated_at=utc_now(),
        )

    # -------------------------------------------------------------------------
    # Gate Evaluator Implementations
    # -------------------------------------------------------------------------

    @classmethod
    def _evaluate_gate_1_integrity(
        cls, semantics: DetectionSemantics, prompt_version: PromptVersion
    ) -> Tuple[float, GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 20.0

        # Mandatory reference case check: Incomplete SIEM rule definition
        if semantics.definition_status in (SemanticsDefinitionStatus.INCOMPLETE, SemanticsDefinitionStatus.UNKNOWN):
            blockers.append(
                f"RULE_DEFINITION_INCOMPLETE: Rule '{semantics.rule_identifier}' lacks authoritative SIEM "
                "detection logic. Observed incident telemetry (e.g. incidentCount, sentBytes64) cannot serve as a verified threshold."
            )
            score -= 10.0

        if semantics.source_provenance == SourceProvenance.AUTO_SYNCED_FROM_INCIDENT:
            warns.append("Rule was auto-synced from incident telemetry cache-miss. Source parameters are unverified.")
            score -= 4.0
        elif semantics.source_provenance == SourceProvenance.HEURISTIC_PARSER:
            warns.append("Rule definition was inferred via heuristic parser without authoritative SIEM definition/XML.")
            score -= 6.0

        # Check if runtime incident metadata is present in rule conditions/logic
        s3 = getattr(prompt_version, "detection_conditions", "") or ""
        conds_str = str(getattr(semantics, "conditions", []) or []) + str(s3)
        if "incidentCount" in conds_str or "incidentDetail" in conds_str:
            warns.append("Incident runtime counter observed in rule conditions. Authoritative correlation parameters required.")
            score -= 4.0

        # Check if policy Section 3 invents a threshold
        if semantics.threshold is None and re.search(r"threshold\s*[:=]\s*\d+", s3, re.IGNORECASE):
            # Check if this threshold is fictitious
            blockers.append(
                "INVENTED_THRESHOLD_DETECTED: Section 3 asserts a specific numeric threshold that is not present "
                "in the authoritative SIEM rule definition."
            )
            score -= 8.0

        if semantics.definition_status in (SemanticsDefinitionStatus.INCOMPLETE, SemanticsDefinitionStatus.UNKNOWN):
            score = min(score, 10.0)

        score = max(0.0, score)
        status = GateStatus.FAILED if blockers else (GateStatus.WARNING if warns else GateStatus.PASSED)
        details = f"Rule definition provenance: {semantics.source_provenance.value}. Status: {semantics.definition_status.value}."
        return score, status, blockers, warns, details

    @classmethod
    def _evaluate_gate_2_relevance(
        cls, prompt_version: PromptVersion, archetype_def: ArchetypeDefinition, semantics: DetectionSemantics
    ) -> Tuple[GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []

        all_text = " ".join([
            getattr(prompt_version, "rule_specific_prompt", "") or "",
            getattr(prompt_version, "detection_conditions", "") or "",
            getattr(prompt_version, "required_evidence", "") or "",
            getattr(prompt_version, "tp_indicators", "") or "",
            getattr(prompt_version, "fp_indicators", "") or "",
        ]).lower()

        # Check if archetype is UNKNOWN / Inadequate Telemetry
        if archetype_def.archetype_id == ArchetypeId.UNKNOWN:
            warns.append(
                "INADEQUATE_TELEMETRY: Rule is classified as 'Unclassified / Inadequate Telemetry'. "
                "Archetype semantics are not definitively established to validate policy relevance."
            )
            details = (
                "Archetype: Unclassified / Inadequate Telemetry. Inadequate telemetry semantics to establish "
                "definitive behavioral archetype. Telemetry enrichment required."
            )
            return GateStatus.WARNING, blockers, warns, details

        # Check for archetype relevance mismatch (e.g. malware in network exfiltration)
        if archetype_def.archetype_id == ArchetypeId.NETWORK_EXFILTRATION:
            # Check if policy erroneously focuses on malware execution
            malware_hits = []
            if "powershell" in all_text and "outbound" not in all_text:
                malware_hits.append("powershell")
            if "lolbin" in all_text:
                malware_hits.append("lolbin")
            if "hash" in all_text and "sha256" in all_text:
                malware_hits.append("file hash")
            if "parent process" in all_text or "ppid" in all_text:
                malware_hits.append("parent process lineage")

            if len(malware_hits) >= 2:
                blockers.append(
                    f"ARCHETYPE_RELEVANCE_MISMATCH: Policy for {archetype_def.name} ({semantics.rule_identifier}) "
                    f"inappropriately emphasizes malware execution concepts ({', '.join(malware_hits)}) "
                    "rather than network transfer direction, destination authorization, and byte volume."
                )

        elif archetype_def.archetype_id == ArchetypeId.NETWORK_SCAN:
            # Check if policy erroneously focuses on endpoint malware execution
            malware_hits = []
            if "powershell" in all_text and "scan" not in all_text:
                malware_hits.append("powershell")
            if "lolbin" in all_text:
                malware_hits.append("lolbin")
            if "hash" in all_text and "sha256" in all_text:
                malware_hits.append("file hash")
            if "parent process" in all_text or "ppid" in all_text:
                malware_hits.append("parent process lineage")
            if "malware execution" in all_text:
                malware_hits.append("malware execution")

            if len(malware_hits) >= 2:
                blockers.append(
                    f"ARCHETYPE_RELEVANCE_MISMATCH: Policy for {archetype_def.name} ({semantics.rule_identifier}) "
                    f"inappropriately emphasizes malware execution concepts ({', '.join(malware_hits)}) "
                    "rather than network scan rate, source IP authorization, target hosts, and destination port."
                )

        status = GateStatus.FAILED if blockers else (GateStatus.WARNING if warns else GateStatus.PASSED)
        details = f"Archetype: {archetype_def.name}. Verified alignment of directives with detection intent."
        return status, blockers, warns, details

    @classmethod
    def _evaluate_gate_3_contract(
        cls,
        prompt_version: PromptVersion,
        contract: Optional[RuleEvidenceContract],
        archetype_def: ArchetypeDefinition,
    ) -> Tuple[float, GateStatus, List[str], List[str], List[str], str]:
        blockers = []
        warns = []
        missing_mappings = []
        score = 20.0

        if not contract:
            blockers.append("MISSING_EVIDENCE_CONTRACT: No Evidence Contract bound to this policy version.")
            return 0.0, GateStatus.FAILED, blockers, warns, missing_mappings, "Missing evidence contract"

        # Check if contract has critical fields
        crit_reqs = [r for r in contract.required_evidence if r.critical]
        if not crit_reqs:
            warns.append("Evidence Contract defines no critical evidence requirements.")
            score -= 5.0

        # Check if mandatory core fields of the archetype are mapped
        contract_fields = {r.field for r in contract.required_evidence}
        for field in archetype_def.mandatory_core_fields:
            if field not in contract_fields:
                missing_mappings.append(field)
                blockers.append(f"UNMAPPED_CORE_EVIDENCE: Mandatory field '{field}' for archetype {archetype_def.archetype_id.value} is missing from contract.")
                score -= 4.0

        # Check if policy demands unsupported fields from archetype
        req_ev_text = (getattr(prompt_version, "required_evidence", "") or "").lower()
        unsupported_demands = []
        for uf in archetype_def.unsupported_fields:
            short_u = uf.split(".")[-1]
            if short_u in req_ev_text or uf.lower() in req_ev_text:
                unsupported_demands.append(uf)
        if unsupported_demands:
            warns.append(
                f"UNSUPPORTED_EVIDENCE_DEMAND: Policy requires fields ({', '.join(unsupported_demands)}) "
                f"that are unsupported by archetype {archetype_def.name}."
            )
            score -= min(6.0, len(unsupported_demands) * 3.0)

        score = max(0.0, score)
        status = GateStatus.FAILED if blockers else (GateStatus.WARNING if warns else GateStatus.PASSED)
        details = f"Contract {contract.contract_id}: {len(contract.required_evidence)} fields defined."
        return score, status, blockers, warns, missing_mappings, details

    @classmethod
    def _evaluate_gate_4_tp_criteria(
        cls, prompt_version: PromptVersion, archetype_def: ArchetypeDefinition
    ) -> Tuple[float, GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 10.0

        tp_text = getattr(prompt_version, "tp_indicators", "") or ""
        if len(tp_text.strip()) < 20:
            blockers.append("INADEQUATE_TP_CRITERIA: True positive indicators are empty or unacceptably brief.")
            score = 0.0
        elif "suspicious" in tp_text.lower() and not any(k in tp_text.lower() for k in ("exceed", "unauthorized", "payload", "anomalous", "beacon", "spike", "failed", "scan", "sweep", "connection", "sequential")):
            warns.append("TP indicators equate general suspiciousness with confirmed maliciousness without objective criteria.")
            score -= 3.0

        if archetype_def.archetype_id in (ArchetypeId.NETWORK_SCAN, ArchetypeId.NETWORK_EXFILTRATION):
            if any(term in tp_text.lower() for term in ("file hash", "sha256", "powershell download", "quarantined")):
                warns.append("TP indicators reference irrelevant endpoint malware artifacts for a network detection rule.")
                score -= 3.0

        score = max(0.0, score)
        status = GateStatus.FAILED if blockers else (GateStatus.WARNING if warns else GateStatus.PASSED)
        details = "Evaluated objective specificity of True Positive criteria."
        return score, status, blockers, warns, details

    @classmethod
    def _evaluate_gate_5_fp_criteria(
        cls, prompt_version: PromptVersion, archetype_def: ArchetypeDefinition
    ) -> Tuple[float, GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 10.0

        fp_text = getattr(prompt_version, "fp_indicators", "") or ""
        common_text = getattr(prompt_version, "common_prompt", "") or ""
        fp_lower = fp_text.lower()
        combo = f"{fp_text} {common_text}".lower()

        # Check FP section directly for unsafe benign assumptions (not diluted by common baseline phrasing)
        if "rfc-1918" in fp_lower and "benign" in fp_lower and "not automatically benign" not in fp_lower and "not benign" not in fp_lower and "verify" not in fp_lower:
            blockers.append(
                "UNSAFE_FP_ASSUMPTION: Policy contains blanket assertion that internal RFC-1918 traffic is benign."
            )
            score -= 5.0
        elif any(term in fp_lower for term in ("loopback", "127.0.0.1", "::1")) and "benign" in fp_lower and "not automatically benign" not in fp_lower and "not benign" not in fp_lower and "verify" not in fp_lower:
            blockers.append(
                "UNSAFE_FP_ASSUMPTION: Policy contains blanket assertion that loopback / 127.0.0.1 traffic is automatically benign."
            )
            score -= 5.0

        # Check for hardcoded prescriptive confidence ranges across FP and baseline text
        if re.search(r"confidence\s*(?:of\s*)?(?:[6-9]\d)\s*(?:-|to)\s*(?:[7-9]\d|100)%", combo) or re.search(r"confidence\s*(?:8\d|9\d)\s*-\s*(?:8\d|9\d)%", combo):
            blockers.append(
                "PRESCRIPTIVE_CONFIDENCE_RANGE: Policy specifies hardcoded artificial confidence ranges (e.g. 80-98%)."
            )
            score -= 5.0

        if len(fp_text.strip()) < 20:
            warns.append("False positive criteria are brief; legitimate administrative exceptions should be expanded.")
            score -= 2.0

        if blockers:
            score = 0.0
            status = GateStatus.FAILED
        else:
            score = max(0.0, score)
            status = GateStatus.WARNING if warns else GateStatus.PASSED

        details = "Evaluated False Positive criteria for unsafe benign assumptions."
        return score, status, blockers, warns, details

    @classmethod
    def _evaluate_gate_6_abstention_escalation(
        cls, prompt_version: PromptVersion, archetype_def: ArchetypeDefinition, semantics: DetectionSemantics
    ) -> Tuple[float, GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 15.0

        missing_text = getattr(prompt_version, "missing_info_criteria", "") or ""
        escalation_text = getattr(prompt_version, "escalation_conditions", "") or ""

        if len(missing_text.strip()) < 15:
            blockers.append("MISSING_CRITICAL_ABSTENTION: Abstention criteria (when to vote REQUIRES_ATTENTION) are undefined.")
            score -= 8.0
        elif "requires_attention" not in missing_text.lower() and "abstain" not in missing_text.lower():
            warns.append("Abstention criteria do not explicitly mandate voting REQUIRES_ATTENTION when telemetry is deficient.")
            score -= 3.0

        if len(escalation_text.strip()) < 15:
            warns.append("P1/P2 escalation conditions are minimal.")
            score -= 4.0

        if "benign" in escalation_text.lower() and ("internal" in escalation_text.lower() or "rfc-1918" in escalation_text.lower()):
            blockers.append("UNSAFE_ESCALATION_ASSUMPTION: Escalation logic assumes internal targets are safe or benign.")
            score -= 5.0

        # Autonomous containment check: Policy should not order unsupported autonomous network cutoffs
        if "isolate host immediately" in escalation_text.lower() and "human" not in escalation_text.lower():
            warns.append("Escalation text suggests autonomous isolation without documented SOC incident response gating.")
            score -= 2.0

        score = max(0.0, score)
        status = GateStatus.FAILED if blockers else (GateStatus.WARNING if warns else GateStatus.PASSED)
        details = "Verified presence of explicit abstention triggers and critical escalation paths."
        return score, status, blockers, warns, details

    @classmethod
    def _evaluate_gate_7_consistency(
        cls,
        prompt_version: PromptVersion,
        contract: Optional[RuleEvidenceContract],
        semantics: DetectionSemantics,
        archetype_def: ArchetypeDefinition,
    ) -> Tuple[float, GateStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 10.0

        req_evidence_text = (getattr(prompt_version, "required_evidence", "") or "").lower()
        tp_text = (getattr(prompt_version, "tp_indicators", "") or "").strip().lower()
        fp_text = (getattr(prompt_version, "fp_indicators", "") or "").strip().lower()

        # Check if contract required fields are completely omitted or contradict Section 4
        if contract:
            crit_fields = [r.field for r in contract.required_evidence if r.critical]
            if crit_fields and len(req_evidence_text.strip()) < 10:
                blockers.append(
                    "G7_CONTRACT_EVIDENCE_OMITTED: Section 4 Required Evidence is blank/missing despite critical fields in Evidence Contract."
                )
                score -= 5.0
            else:
                for cf in crit_fields:
                    short_f = cf.split(".")[-1]
                    if short_f not in req_evidence_text and cf.lower() not in req_evidence_text:
                        warns.append(f"Field '{cf}' marked critical in contract but not explicitly listed in Section 4.")
                        score -= 1.0

        # Check direct TP/FP self-contradiction
        if len(tp_text) >= 15 and tp_text == fp_text:
            blockers.append(
                "G7_TP_FP_SELF_CONTRADICTION: Section 5 (TP indicators) and Section 6 (FP indicators) contain identical contradictory text."
            )
            score -= 6.0

        # Check if unverified threshold in Section 3 contradicts Section 4
        if semantics.definition_status == SemanticsDefinitionStatus.INCOMPLETE:
            if "authoritative threshold" in req_evidence_text and semantics.threshold is None:
                warns.append("Section 4 requires an authoritative threshold that does not exist in SIEM rule definition.")

        if blockers:
            score = 0.0
            status = GateStatus.FAILED
        else:
            score = max(0.0, score)
            status = GateStatus.WARNING if warns else GateStatus.PASSED
        details = "Evaluated internal consistency between 9 policy sections and Evidence Contract."
        return score, status, blockers, warns, details

    @classmethod
    def _evaluate_gate_8_simulation(
        cls,
        simulation_results: Optional[Dict[str, Any]],
        current_policy_digest: Optional[str] = None,
    ) -> Tuple[float, GateStatus, SimulationStatus, List[str], List[str], str]:
        blockers = []
        warns = []
        score = 0.0

        if not simulation_results:
            sim_status = SimulationStatus.NOT_EVALUATED
            warns.append("Historical incident simulation has not been executed for this policy revision.")
            details = "Simulation status: NOT_EVALUATED. Empirical performance unverified."
            return 0.0, GateStatus.WARNING, sim_status, blockers, warns, details

        # Check for policy digest staleness if both digests are available
        sim_digest = simulation_results.get("policy_digest")
        if sim_digest and current_policy_digest and sim_digest != current_policy_digest:
            sim_status = SimulationStatus.NOT_EVALUATED
            warns.append("G8_STALE_SIMULATION: Policy content was modified after the last historical simulation run. Re-run simulation for current digest.")
            details = "Simulation status: NOT_EVALUATED (stale policy digest). Empirical performance unverified for current text."
            return 0.0, GateStatus.WARNING, sim_status, blockers, warns, details

        sample_count = simulation_results.get("sample_count", 0)
        eligible_count = simulation_results.get("eligible_ground_truth_count", simulation_results.get("verified_ground_truth_cases", sample_count))
        sim_status_raw = str(simulation_results.get("simulation_status") or simulation_results.get("status") or "NOT_EVALUATED")

        # Evaluate regression metrics
        regressions = simulation_results.get("critical_regressions", 0)
        reg_detected = simulation_results.get("regression_detected", False) or (simulation_results.get("regression_status") == "REGRESSION_DETECTED")
        if regressions > 0 or reg_detected:
            sim_status = SimulationStatus.EVALUATED_FAILED
            blockers.append(f"FAILED_REGRESSION_GATE: Simulation detected {regressions} critical regressions against baseline.")
            details = f"Simulation FAILED: {regressions} critical regressions observed on historical dataset."
            return 0.0, GateStatus.FAILED, sim_status, blockers, warns, details

        # Evaluate empirical sample sufficiency
        if sim_status_raw == "INSUFFICIENT_DATA" or sample_count < 5 or eligible_count < 5:
            sim_status = SimulationStatus.INSUFFICIENT_DATA
            warns.append(f"G8_INSUFFICIENT_DATA: Insufficient verified historical cases (evaluated={sample_count}, eligible_ground_truth={eligible_count} < 5) to empirically validate policy.")
            details = f"Simulation status: INSUFFICIENT_DATA (evaluated cases: {sample_count}, verified ground-truth cases: {eligible_count} < 5)."
            return 0.0, GateStatus.WARNING, sim_status, blockers, warns, details

        emp_status = str(simulation_results.get("empirical_validation_status") or "").upper()
        overall_acc = simulation_results.get("overall_accuracy")
        cov = simulation_results.get("decision_coverage")
        if (
            sim_status_raw == "INCONCLUSIVE"
            or emp_status == "INCONCLUSIVE"
            or (cov is not None and float(cov) <= 0.0 and overall_acc is None)
        ):
            sim_status = SimulationStatus.INCONCLUSIVE
            warns.append(
                f"G8_INCONCLUSIVE_SIMULATION: Historical simulation produced 0% decisive coverage "
                f"or inconclusive empirical accuracy (evaluated={sample_count}, eligible={eligible_count}); empirical points withheld."
            )
            details = f"Simulation status: INCONCLUSIVE (evaluated cases: {sample_count}, verified ground-truth cases: {eligible_count}, coverage={cov})."
            return 0.0, GateStatus.WARNING, sim_status, blockers, warns, details

        sim_status = SimulationStatus.EVALUATED_PASSED
        score = 15.0
        details = f"Simulation PASSED on {sample_count} historical incidents ({eligible_count} verified ground-truth cases). Zero critical regressions."
        return score, GateStatus.PASSED, sim_status, blockers, warns, details

    # -------------------------------------------------------------------------
    # Cryptographic Digest Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def compute_policy_digest(cls, prompt_version: PromptVersion) -> str:
        h = hashlib.sha256()
        h.update(str(getattr(prompt_version, "version_number", 1)).encode())
        for attr in [
            "common_prompt",
            "rule_specific_prompt",
            "detection_conditions",
            "required_evidence",
            "tp_indicators",
            "fp_indicators",
            "missing_info_criteria",
            "escalation_conditions",
        ]:
            val = getattr(prompt_version, attr, "") or ""
            h.update(val.encode("utf-8"))
        
        q_list = getattr(prompt_version, "analyst_questions", []) or []
        for q in q_list:
            h.update(str(q).encode("utf-8"))
        return h.hexdigest()

    @classmethod
    def compute_contract_digest(cls, contract: Optional[RuleEvidenceContract]) -> str:
        if not contract:
            return "NO_CONTRACT"
        h = hashlib.sha256()
        h.update(contract.contract_id.encode())
        h.update(str(contract.version_number).encode())
        h.update(contract.status.encode())
        h.update(contract.detection_archetype.encode())
        for req in contract.required_evidence:
            h.update(req.field.encode())
            h.update(str(req.critical).encode())
            h.update(str(req.required_for_tp).encode())
        return h.hexdigest()

    @classmethod
    def compute_rule_digest(cls, rule: Rule, semantics: DetectionSemantics) -> str:
        h = hashlib.sha256()
        h.update(semantics.rule_identifier.encode())
        h.update(semantics.definition_status.value.encode())
        h.update(str(semantics.threshold).encode())
        h.update(str(semantics.aggregation_window).encode())
        h.update(str(getattr(rule, "pattern_logic", "")).encode())
        return h.hexdigest()
