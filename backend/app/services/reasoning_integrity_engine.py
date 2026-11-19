"""
Reasoning Integrity Engine (AIS 2.0 V8.2).
Authoritative deterministic validator that cross-examines LLM narrative reasoning,
structured factual claims, and proposed verdicts against canonical incident telemetry.
Prevents factual inversions, unsupported TP/FP conclusions, and semantic contradictions.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_claim import ModelSupportingClaim

logger = logging.getLogger("ai_verdict.reasoning_integrity")


class ReasoningValidationResult(BaseModel):
    is_valid: bool = True
    validation_status: str = "VALIDATED"  # VALIDATED, REASONING_CONTRADICTION, VERDICT_EVIDENCE_CONFLICT, SEMANTIC_REVIEW_REQUIRED, SAFE_ABSTENTION
    reason_codes: List[str] = Field(default_factory=list)
    detected_contradictions: List[str] = Field(default_factory=list)
    semantic_review_notes: List[str] = Field(default_factory=list)
    analyst_action_directive: str = ""
    effective_verdict_override: Optional[str] = None


class ReasoningIntegrityEngine:
    """
    Deterministic cross-validation of:
    1. Original normalized evidence
    2. Structured numerical claims
    3. Narrative claim text
    4. Final verdict rationale
    5. Proposed TP/FP conclusion under detection policy
    """

    @classmethod
    def parse_tcp_behavior(cls, val: Any) -> Dict[str, int]:
        """Extracts numerical counts from scan.tcp_behavior_summary."""
        res = {
            "bidirectional_sessions": 0,
            "unanswered_probes": 0,
            "denied_flows": 0,
            "sampled_events": 0,
            "appctrl_pass_events": 0,
        }
        if not val:
            return res
        s = str(val)
        for key in res.keys():
            m = re.search(rf'\b{key}\s*=\s*(\d+)\b', s, re.IGNORECASE)
            if m:
                res[key] = int(m.group(1))
        return res

    @classmethod
    def parse_destination_scope(cls, val: Any) -> Dict[str, int]:
        """Extracts internal, external, and total counts from scan.destination_scope."""
        res = {"internal": 0, "external": 0, "total_unique_hosts": 0}
        if not val:
            return res
        s = str(val)
        for key in res.keys():
            m = re.search(rf'\b{key}\s*=\s*(\d+)\b', s, re.IGNORECASE)
            if m:
                res[key] = int(m.group(1))
        return res

    @classmethod
    def parse_firewall_actions(cls, val: Any) -> Dict[str, int]:
        """Extracts action counts from scan.firewall_action_summary."""
        res: Dict[str, int] = {}
        if not val:
            return res
        s = str(val)
        for part in s.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                k_clean = k.strip().lower()
                try:
                    res[k_clean] = int(v.strip())
                except ValueError:
                    pass
        return res

    @classmethod
    def evaluate_reasoning_integrity(
        cls,
        incident_id: str,
        proposed_verdict: str,
        model_reason: str,
        supporting_claims: List[ModelSupportingClaim],
        normalization_result: EvidenceNormalizationResult,
        contradictory_evidence: Optional[List[str]] = None,
    ) -> ReasoningValidationResult:
        """
        Executes strict cross-validation between narrative text and observed telemetry.
        """
        clean_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        record_map: Dict[str, Any] = {
            r.source_field: r.observed_value for r in normalization_result.records
        }

        # Build narrative text corpus from model rationale and claim text
        reason_str = str(model_reason or "").strip()
        claim_texts = [
            str(getattr(c, "claim_text", "") or getattr(c, "asserted_value", "") or "").strip()
            for c in supporting_claims
        ]
        combined_narrative = f"{reason_str} {' '.join(claim_texts)}".strip()
        narrative_lower = combined_narrative.lower()

        contradictions: List[str] = []
        reason_codes: List[str] = []
        semantic_notes: List[str] = []

        tcp_behavior = cls.parse_tcp_behavior(record_map.get("scan.tcp_behavior_summary"))
        dest_scope = cls.parse_destination_scope(record_map.get("scan.destination_scope"))
        fw_actions = cls.parse_firewall_actions(record_map.get("scan.firewall_action_summary"))

        # -------------------------------------------------------------
        # Check 1: Factual Inversion — Unanswered Probes vs Bidirectional Sessions
        # -------------------------------------------------------------
        # Model claims traffic is predominantly unanswered or lacked bidirectional sessions
        asserts_unanswered_pattern = re.compile(
            r'\b(?:predominantly\s+unanswered|mostly\s+unanswered|all\s+unanswered|'
            r'unanswered\s+probes|unanswered\s+rst(?:\s+responses)?|'
            r'predominant(?:ly)?\s+unanswered\s+rst|'
            r'no\s+bidirectional(?:\s+sessions)?|zero\s+bidirectional|'
            r'without\s+bidirectional|failed\s+to\s+establish\s+bidirectional)\b',
            re.IGNORECASE,
        )

        has_unanswered_claim = bool(asserts_unanswered_pattern.search(narrative_lower))
        if has_unanswered_claim and "scan.tcp_behavior_summary" in record_map:
            bidir = tcp_behavior["bidirectional_sessions"]
            unans = tcp_behavior["unanswered_probes"]
            sampled = tcp_behavior["sampled_events"] or (bidir + unans)

            # If telemetry shows predominantly bidirectional sessions with zero/minimal unanswered
            if (unans == 0 and bidir > 0) or (bidir >= 80 and unans <= 5):
                contradictions.append(
                    f"Contradiction: Model narrative claims predominantly unanswered probes / no bidirectional sessions, "
                    f"but observed telemetry confirms bidirectional_sessions={bidir} and unanswered_probes={unans} "
                    f"({bidir}/{sampled} bidirectional sessions, 0 unanswered probes)."
                )
                reason_codes.append("REASONING_CONTRADICTION")

            # If model explicitly asserts zero or no bidirectional sessions when bidir > 0
            if re.search(r'\b(?:no|zero)\s+bidirectional\s+sessions\b', narrative_lower) and bidir > 0:
                contradictions.append(
                    f"Contradiction: Model asserted zero bidirectional sessions, but observed telemetry confirms "
                    f"bidirectional_sessions={bidir}."
                )
                if "REASONING_CONTRADICTION" not in reason_codes:
                    reason_codes.append("REASONING_CONTRADICTION")

        # -------------------------------------------------------------
        # Check 2: Factual Inversion — Denied Flows
        # -------------------------------------------------------------
        asserts_denied_pattern = re.compile(
            r'\b(?:predominantly\s+denied|mostly\s+denied|all\s+denied|'
            r'denied\s+flows|traffic\s+was\s+denied|blocked\s+by\s+firewall\s+rules?)\b',
            re.IGNORECASE,
        )
        if asserts_denied_pattern.search(narrative_lower) and "scan.tcp_behavior_summary" in record_map:
            denied = tcp_behavior["denied_flows"]
            if denied == 0:
                contradictions.append(
                    "Contradiction: Model asserted traffic was denied or blocked flows, "
                    "but observed telemetry confirms denied_flows=0."
                )
                if "REASONING_CONTRADICTION" not in reason_codes:
                    reason_codes.append("REASONING_CONTRADICTION")

        # -------------------------------------------------------------
        # Check 3: Factual Inversion — Internal Scope vs External Targets
        # -------------------------------------------------------------
        asserts_internal_recon = re.compile(
            r'\b(?:internal\s+(?:host\s+)?scan|internal\s+reconnaissance|'
            r'internal\s+(?:host\s+)?sweep|lateral\s+movement|lateral\s+scan|'
            r'scanning\s+internal\b|probing\s+internal\b|targeting\s+internal\s+(?:assets|hosts|servers))\b',
            re.IGNORECASE,
        )
        if asserts_internal_recon.search(narrative_lower) and "scan.destination_scope" in record_map:
            internal_dst = dest_scope["internal"]
            external_dst = dest_scope["external"]
            if internal_dst == 0 and external_dst > 0:
                contradictions.append(
                    f"Contradiction: Model asserted internal host scan / lateral movement, "
                    f"but observed destination scope confirms 100% external destinations "
                    f"(internal=0, external={external_dst})."
                )
                if "REASONING_CONTRADICTION" not in reason_codes:
                    reason_codes.append("REASONING_CONTRADICTION")

        # -------------------------------------------------------------
        # Check 4: Conflating Sampled Hosts with SIEM Aggregation Trigger
        # -------------------------------------------------------------
        sample_conflation_pattern = re.compile(
            r'\b(?:only\s+\d+\s+hosts?|did\s+not\s+reach\s+(?:the\s+)?100|below\s+(?:the\s+)?threshold|'
            r'falsely\s+triggered\s+because\s+only)\b',
            re.IGNORECASE,
        )
        if sample_conflation_pattern.search(narrative_lower) and "scan.sample_context" in record_map:
            sample_ctx_str = str(record_map["scan.sample_context"])
            m_trig = re.search(r'trigger_count=(\d+)', sample_ctx_str)
            m_samp = re.search(r'sample_unique_dst_hosts=(\d+)', sample_ctx_str)
            if m_trig and m_samp:
                trig_c = int(m_trig.group(1))
                samp_h = int(m_samp.group(1))
                if trig_c >= 100 and samp_h < 100:
                    semantic_notes.append(
                        f"Sample Context Note: Model discussion of host count ({samp_h}) reflects the sampled window, "
                        f"while authoritative SIEM aggregation verified {trig_c} distinct hosts."
                    )

        # -------------------------------------------------------------
        # Check 5: Firewall Action Semantics Guardrail
        # -------------------------------------------------------------
        # Distinguish between observing client-rst (which is normal TCP teardown) vs claiming it was unanswered
        # (covered by Check 1, but we ensure factual neutral notes on client-rst are not falsely flagged)
        if "client-rst" in narrative_lower and not has_unanswered_claim:
            # Neutral observation of client-rst action: legitimate
            pass

        # -------------------------------------------------------------
        # Outcome Determination
        # -------------------------------------------------------------
        if contradictions:
            return ReasoningValidationResult(
                is_valid=False,
                validation_status="REASONING_CONTRADICTION",
                reason_codes=reason_codes,
                detected_contradictions=contradictions,
                semantic_review_notes=semantic_notes,
                analyst_action_directive="Factual contradiction between model narrative and observed telemetry detected. Decisive verdict overruled to REQUIRES_ATTENTION.",
                effective_verdict_override="REQUIRES_ATTENTION",
            )

        return ReasoningValidationResult(
            is_valid=True,
            validation_status="VALIDATED",
            reason_codes=[],
            detected_contradictions=[],
            semantic_review_notes=semantic_notes,
            analyst_action_directive="Reasoning integrity cross-validation passed without factual contradiction.",
            effective_verdict_override=None,
        )

    @classmethod
    def evaluate_verdict_evidence_consistency(
        cls,
        incident_id: str,
        proposed_verdict: str,
        model_reason: str,
        supporting_claims: List[ModelSupportingClaim],
        normalization_result: EvidenceNormalizationResult,
        rule_archetype: str = "NETWORK_SCAN",
    ) -> ReasoningValidationResult:
        """
        Phase 3 Verdict Consistency Engine:
        Validates whether observed telemetry actually justifies a decisive TP or FP proposal
        under the rule-specific policy criteria.
        """
        clean_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        record_map: Dict[str, Any] = {
            r.source_field: r.observed_value for r in normalization_result.records
        }

        tcp_behavior = cls.parse_tcp_behavior(record_map.get("scan.tcp_behavior_summary"))
        dest_scope = cls.parse_destination_scope(record_map.get("scan.destination_scope"))

        # -------------------------------------------------------------
        # True Positive Consistency Rules for Network Scan
        # -------------------------------------------------------------
        if clean_prop == "TRUE_POSITIVE" and rule_archetype in ("NETWORK_SCAN", "UNKNOWN"):
            bidir = tcp_behavior["bidirectional_sessions"]
            unans = tcp_behavior["unanswered_probes"]
            denied = tcp_behavior["denied_flows"]
            internal_dst = dest_scope["internal"]
            external_dst = dest_scope["external"]
            policy_and_svc = str(record_map.get("scan.policy_and_service") or "").lower()

            # Rule: If traffic is 100% external web browsing with predominantly bidirectional sessions,
            # zero unanswered probes, zero denied flows, and standard browsing policy:
            # Proposing TRUE_POSITIVE contradicts the rule's TP criteria (which requires probe sweeps or lateral recon).
            is_pure_external_browsing = (
                internal_dst == 0
                and external_dst > 0
                and bidir >= 80
                and unans == 0
                and denied == 0
                and any(term in policy_and_svc for term in ("browsing", "https", "ssl", "internet"))
            )

            if is_pure_external_browsing:
                conflict_msg = (
                    f"Verdict Conflict: Proposed TRUE_POSITIVE contradicts observed telemetry showing "
                    f"100% external bidirectional browsing (bidirectional={bidir}, unanswered={unans}, "
                    f"denied={denied}, internal=0, policy={record_map.get('scan.policy_and_service')}) "
                    "without corroborating scan indicators, probe timeouts, or lateral attack tradecraft."
                )
                return ReasoningValidationResult(
                    is_valid=False,
                    validation_status="VERDICT_EVIDENCE_CONFLICT",
                    reason_codes=["VERDICT_EVIDENCE_CONFLICT", "TP_CRITERIA_UNSATISFIED"],
                    detected_contradictions=[conflict_msg],
                    analyst_action_directive="Proposed TRUE_POSITIVE is in conflict with observed bidirectional web telemetry. Overruled to REQUIRES_ATTENTION for manual triage.",
                    effective_verdict_override="REQUIRES_ATTENTION",
                )

        # -------------------------------------------------------------
        # False Positive Consistency Rules for Network Scan
        # -------------------------------------------------------------
        elif clean_prop == "FALSE_POSITIVE" and rule_archetype in ("NETWORK_SCAN", "UNKNOWN"):
            # Bidirectional HTTPS sessions alone do NOT conclusively establish False Positive
            # without verifying absence of internal recon or verifying change authorization.
            internal_dst = dest_scope["internal"]
            if internal_dst > 0:
                # Mixed or internal destination scope cannot be closed as FP without explicit authorization
                conflict_msg = (
                    f"Verdict Conflict: Proposed FALSE_POSITIVE contradicts observed mixed destination scope "
                    f"(internal={internal_dst}, external={dest_scope['external']}). Internal targets require "
                    "authoritative scanner/change authorization before benign closure."
                )
                return ReasoningValidationResult(
                    is_valid=False,
                    validation_status="VERDICT_EVIDENCE_CONFLICT",
                    reason_codes=["VERDICT_EVIDENCE_CONFLICT", "FP_CRITERIA_UNSATISFIED"],
                    detected_contradictions=[conflict_msg],
                    analyst_action_directive="Proposed FALSE_POSITIVE lacks required authorization evidence for internal targets. Overruled to REQUIRES_ATTENTION.",
                    effective_verdict_override="REQUIRES_ATTENTION",
                )

        # Safe Abstention:
        elif clean_prop in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE"):
            return ReasoningValidationResult(
                is_valid=True,
                validation_status="SAFE_ABSTENTION",
                reason_codes=[],
                detected_contradictions=[],
                analyst_action_directive="Model safely abstained; route to analyst triage.",
                effective_verdict_override="REQUIRES_ATTENTION",
            )

        return ReasoningValidationResult(
            is_valid=True,
            validation_status="VALIDATED",
            reason_codes=[],
            detected_contradictions=[],
            analyst_action_directive="Verdict-evidence consistency verified.",
            effective_verdict_override=None,
        )
