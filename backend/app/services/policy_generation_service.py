import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    ArchetypeId,
    ArchetypeDefinition,
    SemanticsDefinitionStatus,
    SourceProvenance,
)
from app.schemas.evidence_contract import RuleEvidenceContract
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper

logger = logging.getLogger("ai_verdict.policy_generation")

# REQ-04 Section 1: Standardized, Versioned Enterprise SOC Baseline
# Strictly eliminates hardcoded confidence ranges and unsafe universal benign assumptions
ENTERPRISE_SOC_BASELINE_V2 = """# ENTERPRISE SOC LEVEL-2 INVESTIGATION & TRIAGE PROTOCOL (BASELINE v2.0.0)
You are an expert Level-2 Security Operations Center (SOC) Senior Incident Investigator.
Your mission is to perform strict, evidence-grounded triage on incoming SIEM incident telemetry and determine ground-truth status.

## CORE INVESTIGATIVE PRINCIPLES:
1. FACTUAL GROUNDING: Every conclusion, assertion, or verdict MUST be grounded strictly in observed, verified incident telemetry. Inventing or hallucinating unobserved facts is strictly prohibited.
2. DISTINGUISH SUSPICION FROM CONFIRMATION: An anomalous, rare, or unclassified indicator represents suspicion, NOT confirmed maliciousness. Do not classify an incident as TRUE_POSITIVE without corroborating security-relevant tradecraft.
3. NO UNIVERSAL BENIGN ASSUMPTIONS: Internal RFC-1918 traffic (10.x, 172.16-31.x, 192.168.x) and loopback addresses are NOT inherently harmless. Adversaries routinely leverage internal hosts for lateral movement, credential access, and internal staging. Verify administrative authorization and business justification before classifying activity as benign.
4. HONEST CONFIDENCE EVALUATION: Do NOT prescribe arbitrary or hardcoded confidence ranges. Report subjective model confidence honestly based strictly on the completeness and clarity of observed indicators.
5. MANDATORY ABSTENTION ON DEFICIENT EVIDENCE: When material telemetry required by the rule's Evidence Contract is missing, truncated, or conflicting, you MUST vote REQUIRES_ATTENTION with an explicit list of absent evidence items.

## VERDICT DEFINITIONS:
- TRUE_POSITIVE: Observed telemetry independently verifies active threat adversary tradecraft, policy violation, or unauthorized operational compromise.
- FALSE_POSITIVE: Observed telemetry independently verifies authorized administrative maintenance, documented business operations, or a verifiable SIEM detection syntax/reflection error.
- REQUIRES_ATTENTION: Critical evidence is absent, truncated, contradictory, or requires physical host containment / out-of-band human incident response verification.
"""


class PolicyGenerationService:
    """
    REQ-04: Detection-Aware Nine-Section Policy Generation Service.
    Generates tailored, evidence-grounded investigation policies directly
    from structured detection semantics and behavioral archetypes.
    
    Guarantees:
      - Large Outbound Transfer receives network exfiltration directives, NOT malware execution.
      - Never invents missing rule conditions or thresholds.
      - Common SOC baseline has no hardcoded confidence ranges or blanket RFC-1918 benign rules.
      - Evidence requirements align 100% with the machine-verifiable Evidence Contract.
      - Generated policies remain strictly in DRAFT status.
    """
    GENERATOR_VERSION = "v2.0.0"

    @classmethod
    def generate_nine_section_draft(
        cls,
        rule: Rule,
        authoritative_siem_definition: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes the complete nine-section policy specification for a rule.
        Returns a dictionary of fields ready to construct a PromptVersion.
        """
        # 1. Analyze Detection Semantics
        semantics = RuleIntelligenceAnalyzer.analyze_rule(
            rule=rule,
            authoritative_siem_definition=authoritative_siem_definition,
        )

        # 2. Classify into Versioned Detection Archetype
        classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)

        # 3. Derive Evidence Contract Requirements
        contract = EvidenceRequirementMapper.map_evidence_contract(
            rule=rule,
            semantics=semantics,
            archetype_def=archetype_def,
        )

        # 4. Synthesize Section 1: Common SOC Baseline
        common_prompt = ENTERPRISE_SOC_BASELINE_V2

        # 5. Synthesize Section 2: Rule-Specific Directive
        rule_directive = cls._generate_section2_directive(semantics, archetype_def, classification)

        # 6. Synthesize Section 3: Detection Conditions
        detection_conditions = cls._generate_section3_detection_conditions(semantics, rule)

        # 7. Synthesize Section 4: Required Evidence Checklist
        required_evidence = cls._generate_section4_evidence(contract, semantics)

        # 8. Synthesize Section 5: True Positive Indicators
        tp_indicators = cls._generate_section5_tp_indicators(semantics, archetype_def)

        # 9. Synthesize Section 6: False Positive Indicators
        fp_indicators = cls._generate_section6_fp_indicators(semantics, archetype_def)

        # 10. Synthesize Section 7: Missing Information / Abstention Criteria
        missing_info = cls._generate_section7_abstention(semantics, archetype_def)

        # 11. Synthesize Section 8: Escalation Conditions
        escalation = cls._generate_section8_escalation(semantics, archetype_def)

        # 12. Synthesize Section 9: Analyst Investigation Questions
        analyst_questions = cls._generate_section9_questions(semantics, archetype_def)

        summary_note = (
            f"AIS 2.0 Intelligent Template Draft ({archetype_def.name} | Archetype: {archetype_def.archetype_id.value}) "
            f"— Semantics: {semantics.definition_status.value}."
        )
        if semantics.definition_status == SemanticsDefinitionStatus.INCOMPLETE:
            summary_note += " WARNING: Authoritative SIEM rule definition incomplete. Human review required before approval."

        return {
            "common_prompt": common_prompt.strip(),
            "rule_specific_prompt": rule_directive.strip(),
            "detection_conditions": detection_conditions.strip(),
            "required_evidence": required_evidence.strip(),
            "tp_indicators": tp_indicators.strip(),
            "fp_indicators": fp_indicators.strip(),
            "missing_info_criteria": missing_info.strip(),
            "escalation_conditions": escalation.strip(),
            "analyst_questions": analyst_questions,
            "change_summary": summary_note,
            "is_template_draft": True,
            "status": "DRAFT",
            "quality_status": "GENERATED_DRAFT",
            "created_by_user_id": user_id,
            "semantics_snapshot": semantics.model_dump(mode="json"),
            "primary_archetype": archetype_def.archetype_id.value,
        }

    @classmethod
    def _generate_section2_directive(
        cls,
        semantics: DetectionSemantics,
        archetype_def: ArchetypeDefinition,
        classification: Any,
    ) -> str:
        lines = [
            f"### {semantics.rule_name.upper()} ({semantics.rule_identifier})",
            f"Archetype: {archetype_def.archetype_id.value} | Category: {semantics.event_category or 'General'}",
            f"Objective: {semantics.detection_objective}",
            "Mandates:",
        ]

        if archetype_def.archetype_id == ArchetypeId.NETWORK_EXFILTRATION:
            lines.extend([
                "1. Confirm outbound direction (internal source -> external destination) and total bytes transferred.",
                "2. Check destination authorization (approved corporate cloud/partner vs untrusted/newly registered host).",
                "3. Cross-check corroborating DLP, archive-staging, or endpoint process context.",
                "4. Compare volume against historical host/user baseline.",
                "5. Do NOT assume internal RFC-1918 traffic is benign if lateral staging/exfiltration is possible.",
            ])
        elif archetype_def.archetype_id == ArchetypeId.MALWARE_EXECUTION:
            lines.extend([
                "1. Inspect full process command line arguments and switches.",
                "2. Verify parent-child process lineage, signer/digital signature, and file hash reputation.",
                "3. Check for LOLBin abuse or execution from writable temporary paths.",
            ])
        elif archetype_def.archetype_id == ArchetypeId.NETWORK_SCAN:
            lines.extend([
                "1. Verify sequential/horizontal connection attempts across destination hosts/ports.",
                "2. Verify whether source IP is an authorized scanner (Nessus/Qualys/Rapid7/monitoring) or change ticket.",
                "3. Assess scan target breadth, rate, and TCP handshake behavior (SYN vs RST/timeouts/established).",
                "4. Do NOT assume RFC-1918 or loopback traffic is benign without verified scanner/admin authorization.",
                "5. Check follow-on exploit payloads, brute force, or lateral movement.",
            ])
        elif archetype_def.archetype_id == ArchetypeId.BRUTE_FORCE:
            lines.extend([
                "1. Check failed-logon sequence and whether a subsequent logon succeeded.",
                "2. Assess source IP reputation, ASN, and targeted account breadth (single user vs password spray).",
            ])
        else:
            lines.extend([
                "1. Validate SIEM trigger conditions against canonical telemetry and host/user identity.",
                "2. Distinguish verified threat activity from documented administrative operations.",
            ])

        return "\n".join(lines)

    @classmethod
    def _generate_section3_detection_conditions(cls, semantics: DetectionSemantics, rule: Rule) -> str:
        lines = [
            f"Category: {semantics.event_category or 'Standard'} | Source: {semantics.data_source or 'FortiSIEM'} | Provenance: {semantics.source_provenance.value}",
        ]

        if semantics.threshold is not None:
            lines.append(f"Authoritative Threshold: {semantics.threshold} {semantics.threshold_unit or ''}".strip())
        else:
            lines.append("Authoritative Threshold: UNVERIFIED (No verified threshold in SIEM rule logic)")

        if semantics.aggregation_window:
            lines.append(f"Aggregation Window: {semantics.aggregation_window}")
        else:
            lines.append("Aggregation Window: UNVERIFIED")

        if semantics.conditions:
            lines.append("Conditions: " + "; ".join(
                f"{cond.get('field')} {cond.get('operator')} {cond.get('value')}"
                for cond in semantics.conditions
            ))
        elif rule.pattern_logic:
            raw_logic = str(rule.pattern_logic).strip()
            lines.append(f"Raw Logic: {raw_logic[:300]}")

        if semantics.definition_status == SemanticsDefinitionStatus.INCOMPLETE:
            lines.append(
                "NOTICE (INCOMPLETE): Lacks authoritative SIEM rule condition block; observed counters (e.g. sentBytes64) are NOT thresholds."
            )

        return "\n".join(lines)

    @classmethod
    def _generate_section4_evidence(cls, contract: RuleEvidenceContract, semantics: DetectionSemantics) -> str:
        lines = ["Required Evidence (Evidence Contract):"]

        core_reqs = [r for r in contract.required_evidence if getattr(r, "requirement_level", "CORE") == "CORE"]
        cond_reqs = [r for r in contract.required_evidence if getattr(r, "requirement_level", "") == "CONDITIONAL"]
        opt_reqs = [r for r in contract.required_evidence if getattr(r, "requirement_level", "") in ("OPTIONAL", "UNVERIFIED")]

        if core_reqs:
            core_items = [
                f"{r.field}{' [CRITICAL]' if r.critical else ''} ({r.evidence_type})"
                for r in core_reqs
            ]
            lines.append("Core: " + "; ".join(core_items))

        if cond_reqs:
            lines.append("Conditional: " + "; ".join(r.field for r in cond_reqs))

        if opt_reqs:
            lines.append("Optional: " + "; ".join(r.field for r in opt_reqs))

        return "\n".join(lines)

    @classmethod
    def _generate_section5_tp_indicators(cls, semantics: DetectionSemantics, archetype_def: ArchetypeDefinition) -> str:
        lines = ["TRUE_POSITIVE only when observed telemetry verifies:"]
        for ind in archetype_def.tp_indicator_candidates:
            lines.append(f"- {ind}")
        return "\n".join(lines)

    @classmethod
    def _generate_section6_fp_indicators(cls, semantics: DetectionSemantics, archetype_def: ArchetypeDefinition) -> str:
        lines = ["FALSE_POSITIVE when observed telemetry verifies authorized operations/noise:"]
        for ind in archetype_def.fp_indicator_candidates:
            lines.append(f"- {ind}")
        return "\n".join(lines)

    @classmethod
    def _generate_section7_abstention(cls, semantics: DetectionSemantics, archetype_def: ArchetypeDefinition) -> str:
        lines = ["Abstain (REQUIRES_ATTENTION) if:"]
        for req in archetype_def.abstention_requirements:
            lines.append(f"- {req}")

        if semantics.definition_status == SemanticsDefinitionStatus.INCOMPLETE:
            lines.append("- Authoritative SIEM threshold/window undefined.")

        return "\n".join(lines)

    @classmethod
    def _generate_section8_escalation(cls, semantics: DetectionSemantics, archetype_def: ArchetypeDefinition) -> str:
        lines = ["P1/P2 Escalation triggers:"]
        for esc in archetype_def.escalation_considerations:
            lines.append(f"- {esc}")
        return "\n".join(lines)

    @classmethod
    def _generate_section9_questions(cls, semantics: DetectionSemantics, archetype_def: ArchetypeDefinition) -> List[str]:
        return list(archetype_def.analyst_question_templates)
