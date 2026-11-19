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
                    f"({bidir}/{sampled} bidirectional sessions, {unans} unanswered probes)."
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
        elif "scan.sample_context" in record_map:
            semantic_notes.append(
                "Sample Window Scope: Telemetry represents a sampled 100-event window slice. "
                "Missing corroboration in the sample slice is distinguished from verified absence of malicious behavior."
            )

        # -------------------------------------------------------------
        # Check 5: Firewall Action Semantics Guardrail
        # -------------------------------------------------------------
        # Distinguish between observing client-rst (normal TCP teardown) vs server-rst (rejection/termination)
        if "server-rst" in narrative_lower:
            semantic_notes.append(
                "Firewall Action Note: server-rst indicates reset/rejection from destination endpoint (e.g. closed port or drop)."
            )
        if "client-rst" in narrative_lower:
            semantic_notes.append(
                "Firewall Action Note: client-rst indicates client-initiated teardown, standard in web browsing session closure or connection reuse."
            )

        # -------------------------------------------------------------
        # Check 6: Policy Violation — Loopback Claimed on External/Distinct Traffic
        # -------------------------------------------------------------
        loopback_claim_pattern = re.compile(
            r'\b(?:same\s+source\s+and\s+destination\s+ip|identical\s+source\s+and\s+destination|'
            r'source\s+and\s+destination\s+are\s+(?:the\s+)?same|traffic\s+(?:is|was)\s+loopback|'
            r'internal\s+loopback|localhost\s+traffic|sent\s+to\s+itself|self-referential\s+ip)\b',
            re.IGNORECASE,
        )
        if loopback_claim_pattern.search(narrative_lower):
            src_ip = str(record_map.get("network.source_ip") or record_map.get("srcIpAddr") or "").strip()
            dst_ip = str(record_map.get("network.destination_ip") or record_map.get("destIpAddr") or "").strip()
            dst_name = str(record_map.get("network.destination_domain") or record_map.get("destName") or "").strip()

            # If both source and destination are present and clearly distinct
            if src_ip and dst_ip and src_ip != dst_ip and not dst_ip.startswith("127."):
                contradictions.append(
                    f"Contradiction: Model asserted identical source and destination IP / loopback traffic, "
                    f"but observed telemetry confirms distinct source ({src_ip}) and destination ({dst_ip}{' / ' + dst_name if dst_name else ''}). "
                    f"Rule grouping 'Same Source and Destination' reflects FortiSIEM correlation aggregation criteria, not loopback."
                )
                if "REASONING_CONTRADICTION" not in reason_codes:
                    reason_codes.append("REASONING_CONTRADICTION")
                if "LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC" not in reason_codes:
                    reason_codes.append("LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC")

        # -------------------------------------------------------------
        # Check 7: Policy Violation — Firewall Action Inversion (Allowed vs Blocked)
        # -------------------------------------------------------------
        asserts_allowed_pattern = re.compile(
            r'\b(?:traffic\s+was\s+allowed|request\s+was\s+permitted|successfully\s+connected|'
            r'connection\s+succeeded|session\s+was\s+established|data\s+was\s+exfiltrated|'
            r'successfully\s+accessed|allowed\s+by\s+policy)\b',
            re.IGNORECASE,
        )
        action_val = str(record_map.get("security.action") or record_map.get("action") or "").lower()
        event_type_val = str(record_map.get("security.event_type") or record_map.get("eventType") or "").lower()
        is_blocked_action = (
            any(term in action_val for term in ("blocked", "denied", "dropped", "reset"))
            or "cat-blk" in event_type_val
            or "filter-block" in event_type_val
        )
        if asserts_allowed_pattern.search(narrative_lower) and is_blocked_action:
            contradictions.append(
                f"Contradiction: Model asserted traffic was allowed or session successfully established, "
                f"but observed telemetry confirms action='{record_map.get('security.action') or action_val}' "
                f"and eventType='{record_map.get('security.event_type') or event_type_val}'."
            )
            if "REASONING_CONTRADICTION" not in reason_codes:
                reason_codes.append("REASONING_CONTRADICTION")

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

    # -------------------------------------------------------------
    # Negation and Speculation Patterns (V8.3a Hotfix)
    # -------------------------------------------------------------
    NEGATED_THREAT_RE = re.compile(
        r'\b(?:no|not|neither|nor|without|never|unobserved|none|not\s+observed|not\s+detected|not\s+found|zero|absence\s+of)\s+'
        r'(?:exploit|c2|malice|payload|threat|attack|botnet|brute\s*force|malware|reconnaissance|malicious\s+activity)\b|'
        r'\b(?:c2|exploit|malware|threat|payload|botnet)\s+(?:was\s+not|is\s+not|not)\s+(?:observed|detected|found|seen|present)\b',
        re.IGNORECASE,
    )

    SPECULATIVE_THREAT_RE = re.compile(
        r'\b(?:potential\s+malicious\s+ip|model\s+suspects\s+reconnaissance|suspects\s+reconnaissance|'
        r'unconfirmed\s+threat|hypothetical\s+c2|might\s+be\s+malicious|could\s+be\s+an\s+exploit)\b',
        re.IGNORECASE,
    )

    NEGATED_AUTH_RE = re.compile(
        r'\b(?:scanner\s+authorization\s+unknown|not\s+an\s+authorized\s+scanner|no\s+approved\s+change\s+ticket|'
        r'unauthorized\s+scanner|unapproved\s+scanner|authorization\s+unknown|no\s+change\s+ticket|'
        r'authorization\s+(?:was\s+not|is\s+not|not)\s+(?:found|observed|verified|provided|present)|'
        r'(?:no|without|absence\s+of)\s+(?:approved|authorized)\s+(?:change|ticket|maintenance|scanner))\b',
        re.IGNORECASE,
    )

    AUTHORIZATION_FIELDS = frozenset({
        "asset.authorization",
        "asset.authorization_ticket",
        "asset.scanner_role",
        "asset.is_authorized_scanner",
        "change.ticket_id",
        "change.approval_status",
        "maintenance.window_active",
        "itsm.ticket_id",
        "telemetry.change_ticket",
        "asset.scan_approval",
        "scan.authorization",
    })

    THREAT_FIELDS = frozenset({
        "threat_intel.verdict",
        "threat_intel.reputation",
        "threat_intel.category",
        "security_event.signature",
        "security_event.threat_name",
        "security_event.attack_technique",
        "payload.signature",
        "c2.indicator",
        "antivirus.threat_name",
        "ips.attack_name",
        "scan.threat_intel",
        "endpoint.ioc_match",
    })

    TICKET_ID_RE = re.compile(r'\b(?:CHG|RFC|INC|TKT|SEC)-(?:[A-Za-z0-9]+-)*[A-Za-z0-9]+\b', re.IGNORECASE)

    @classmethod
    def verify_threat_corroboration(
        cls,
        supporting_claims: List[ModelSupportingClaim],
        normalization_result: EvidenceNormalizationResult,
        model_reason: str,
    ) -> Tuple[bool, str, List[str]]:
        """
        V8.3a Hotfix: Evidence-backed threat corroboration validator.
        Guarantees that decisive TRUE_POSITIVE proposals on traffic resembling browsing
        are backed by genuine, verified threat intelligence, exploit payloads, or C2 indicators.
        Strictly rejects:
        - Narrative keyword matches without verified evidence records
        - Negated statements ("No exploit detected", "C2 was not observed")
        - Speculative statements ("Potential malicious IP", "The model suspects reconnaissance")
        - Bare EV-* identifiers citing unrelated evidence (e.g. protocol or destination IP list)
        - Fabricated claims lacking provenance
        """
        verified_eids: List[str] = []
        record_by_id = {r.evidence_id: r for r in normalization_result.records}

        # 1. Inspect direct canonical evidence records for authoritative threat intelligence / attack signatures
        for rec in normalization_result.records:
            sf_lower = rec.source_field.lower()
            val_lower = str(rec.observed_value).lower()
            if sf_lower in cls.THREAT_FIELDS or any(sf_lower.startswith(prefix) for prefix in ("threat_intel.", "security_event.", "c2.", "payload.")):
                is_positive_threat = any(term in val_lower for term in ("malicious", "c2", "botnet", "exploit", "trojan", "attack", "high_risk", "phishing", "backdoor", "scanner"))
                is_clean_threat = any(term in val_lower for term in ("clean", "benign", "safe", "none", "no exploit", "not observed", "0"))
                if is_positive_threat and not is_clean_threat:
                    verified_eids.append(rec.evidence_id)

        # 2. Inspect grounded claims
        for claim in supporting_claims:
            claim_text = str(getattr(claim, "claim_text", "") or "").strip()
            asserted_val = str(getattr(claim, "asserted_value", "") or "").strip()
            full_claim = f"{claim_text} {asserted_val}".lower()

            if cls.NEGATED_THREAT_RE.search(full_claim) or cls.SPECULATIVE_THREAT_RE.search(full_claim):
                continue

            if not getattr(claim, "is_grounded", False) or getattr(claim, "grounding_status", "") != "GROUNDED":
                continue

            matched_id = getattr(claim, "matched_evidence_id", None)
            if matched_id and matched_id in record_by_id:
                matched_rec = record_by_id[matched_id]
                m_field = matched_rec.source_field.lower()
                m_val = str(matched_rec.observed_value).lower()

                is_authoritative_threat_record = (
                    m_field in cls.THREAT_FIELDS
                    or any(m_field.startswith(p) for p in ("threat_intel.", "security_event.", "c2.", "payload.", "antivirus.", "ips."))
                    or any(term in m_val for term in ("malicious", "c2", "botnet", "exploit", "trojan", "compromised", "brute_force"))
                )
                if is_authoritative_threat_record:
                    if matched_id not in verified_eids:
                        verified_eids.append(matched_id)

        if verified_eids:
            return (
                True,
                f"Threat corroboration independently verified via {len(verified_eids)} canonical record(s) ({', '.join(verified_eids[:3])})",
                verified_eids,
            )

        if cls.NEGATED_THREAT_RE.search(model_reason):
            return (
                False,
                "Model narrative explicitly contains negated threat statements ('no exploit detected' / 'C2 was not observed') which cannot establish maliciousness",
                [],
            )
        if cls.SPECULATIVE_THREAT_RE.search(model_reason):
            return (
                False,
                "Model narrative contains speculative/unconfirmed assertions ('potential malicious IP' / 'model suspects reconnaissance') lacking verified evidence records",
                [],
            )

        return (
            False,
            "No verified threat intelligence, exploit payload, or C2 evidence found in canonical evidence records. Model-generated prose or citations of unrelated evidence IDs do not establish maliciousness",
            [],
        )

    @classmethod
    def verify_authorization(
        cls,
        supporting_claims: List[ModelSupportingClaim],
        normalization_result: EvidenceNormalizationResult,
        model_reason: str,
    ) -> Tuple[bool, str, List[str]]:
        """
        V8.3a Hotfix: Evidence-backed scanner and change authorization validator.
        Guarantees that decisive FALSE_POSITIVE proposals on internal scan sweeps
        are backed by verifiable change management tickets, scanner registrations, or maintenance approvals.
        Strictly rejects:
        - Narrative keyword matches without verified evidence records
        - Negated statements ("Scanner authorization unknown", "Not an authorized scanner", "No approved change ticket")
        - Model-generated ticket identifiers with no verified record (e.g. hallucinated "CHG-9999")
        - Bare EV-* identifiers citing unrelated evidence
        - Speculative or unverified claims
        """
        verified_eids: List[str] = []
        record_by_id = {r.evidence_id: r for r in normalization_result.records}

        # 1. Inspect direct canonical evidence records for authoritative change tickets or scanner registrations
        for rec in normalization_result.records:
            sf_lower = rec.source_field.lower()
            val_str = str(rec.observed_value)
            val_lower = val_str.lower()

            if sf_lower in cls.AUTHORIZATION_FIELDS or any(sf_lower.startswith(prefix) for prefix in ("asset.auth", "change.", "maintenance.", "itsm.")):
                has_ticket = bool(cls.TICKET_ID_RE.search(val_str))
                has_approval = any(term in val_lower for term in ("authorized", "approved", "active_maintenance", "registered_scanner", "scheduled"))
                is_negated = any(term in val_lower for term in ("unauthorized", "unapproved", "rejected", "expired", "cancelled", "unknown", "none"))
                if (has_ticket or has_approval) and not is_negated:
                    verified_eids.append(rec.evidence_id)

        # 2. Inspect grounded claims
        for claim in supporting_claims:
            claim_text = str(getattr(claim, "claim_text", "") or "").strip()
            asserted_val = str(getattr(claim, "asserted_value", "") or "").strip()
            full_claim = f"{claim_text} {asserted_val}".lower()

            if cls.NEGATED_AUTH_RE.search(full_claim):
                continue

            if not getattr(claim, "is_grounded", False) or getattr(claim, "grounding_status", "") != "GROUNDED":
                continue

            matched_id = getattr(claim, "matched_evidence_id", None)
            if matched_id and matched_id in record_by_id:
                matched_rec = record_by_id[matched_id]
                m_field = matched_rec.source_field.lower()
                m_val = str(matched_rec.observed_value)

                is_authoritative_auth_record = (
                    m_field in cls.AUTHORIZATION_FIELDS
                    or any(m_field.startswith(p) for p in ("asset.auth", "change.", "maintenance.", "itsm."))
                    or bool(cls.TICKET_ID_RE.search(m_val))
                    or any(term in m_val.lower() for term in ("authorized scanner", "approved change", "maintenance window"))
                )
                if is_authoritative_auth_record:
                    if matched_id not in verified_eids:
                        verified_eids.append(matched_id)

        if verified_eids:
            return (
                True,
                f"Scanner/change authorization independently verified via {len(verified_eids)} canonical record(s) ({', '.join(verified_eids[:3])})",
                verified_eids,
            )

        if cls.NEGATED_AUTH_RE.search(model_reason):
            return (
                False,
                "Model narrative explicitly indicates scanner authorization is unknown, unapproved, or lacking a change ticket ('not an authorized scanner' / 'no approved change ticket')",
                [],
            )

        narrative_ticket_match = cls.TICKET_ID_RE.search(model_reason)
        if narrative_ticket_match:
            hallucinated_ticket = narrative_ticket_match.group(0)
            return (
                False,
                f"Model-generated ticket identifier '{hallucinated_ticket}' was asserted in narrative but has no verified record in canonical incident evidence",
                [],
            )

        return (
            False,
            "No verified change ticket, scanner asset registration, or maintenance approval found in canonical evidence records. Model-generated prose or citations of unrelated evidence IDs do not establish authorization",
            [],
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
        Phase 3 Verdict Consistency Engine (V8.3a Hotfix):
        Validates whether observed telemetry actually justifies a decisive TP or FP proposal
        under the rule-specific policy criteria.
        Enforces evidence-verified threat corroboration and scanner authorization:
        - Rejects narrative-keyword matches without verified evidence records.
        - Rejects negated statements ("No exploit detected", "C2 was not observed").
        - Rejects speculative statements ("Potential malicious IP", "The model suspects reconnaissance").
        - Rejects bare EV-* citations referring to unrelated evidence.
        - Requires verifiable change ticket / scanner asset records for internal scans.
        """
        clean_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        record_map: Dict[str, Any] = {
            r.source_field: r.observed_value for r in normalization_result.records
        }

        tcp_behavior = cls.parse_tcp_behavior(record_map.get("scan.tcp_behavior_summary"))
        dest_scope = cls.parse_destination_scope(record_map.get("scan.destination_scope"))

        reason_str = str(model_reason or "").strip()
        semantic_notes: List[str] = []

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

            is_pure_external_browsing = (
                internal_dst == 0
                and external_dst > 0
                and bidir >= 80
                and unans == 0
                and denied == 0
                and any(term in policy_and_svc for term in ("browsing", "https", "ssl", "internet"))
            )

            # V8.3a Evidence-Verified Threat Corroboration Check
            is_threat_verified, threat_detail, verified_threat_eids = cls.verify_threat_corroboration(
                supporting_claims=supporting_claims,
                normalization_result=normalization_result,
                model_reason=reason_str,
            )

            if is_pure_external_browsing and not is_threat_verified:
                conflict_msg = (
                    f"Verdict Conflict: Proposed TRUE_POSITIVE contradicts observed telemetry showing "
                    f"100% external bidirectional browsing (bidirectional={bidir}, unanswered={unans}, "
                    f"denied={denied}, internal=0, policy={record_map.get('scan.policy_and_service')}). "
                    f"Requirement unsatisfied: {threat_detail}. Model narrative keywords or ungrounded "
                    "assertions cannot establish maliciousness without verified canonical evidence records."
                )
                return ReasoningValidationResult(
                    is_valid=False,
                    validation_status="VERDICT_EVIDENCE_CONFLICT",
                    reason_codes=["VERDICT_EVIDENCE_CONFLICT", "TP_CRITERIA_UNSATISFIED"],
                    detected_contradictions=[conflict_msg],
                    semantic_review_notes=semantic_notes,
                    analyst_action_directive="Proposed TRUE_POSITIVE lacks verified threat intelligence or attack tradecraft in canonical evidence records. Overruled to REQUIRES_ATTENTION for manual triage.",
                    effective_verdict_override="REQUIRES_ATTENTION",
                )
            elif is_threat_verified:
                semantic_notes.append(f"Threat Corroboration Verified: {threat_detail}")

        # -------------------------------------------------------------
        # False Positive Consistency Rules for Network Scan
        # -------------------------------------------------------------
        elif clean_prop == "FALSE_POSITIVE" and rule_archetype in ("NETWORK_SCAN", "UNKNOWN"):
            internal_dst = dest_scope["internal"]

            # V8.3a Evidence-Verified Authorization Check
            is_auth_verified, auth_detail, verified_auth_eids = cls.verify_authorization(
                supporting_claims=supporting_claims,
                normalization_result=normalization_result,
                model_reason=reason_str,
            )

            if internal_dst > 0 and not is_auth_verified:
                conflict_msg = (
                    f"Verdict Conflict: Proposed FALSE_POSITIVE contradicts observed internal/mixed destination scope "
                    f"(internal={internal_dst}, external={dest_scope['external']}). "
                    f"Requirement unsatisfied: {auth_detail}. Internal host sweeps require verifiable change "
                    "ticket, scanner registration, or maintenance approval in evidence records before benign closure."
                )
                return ReasoningValidationResult(
                    is_valid=False,
                    validation_status="VERDICT_EVIDENCE_CONFLICT",
                    reason_codes=["VERDICT_EVIDENCE_CONFLICT", "FP_CRITERIA_UNSATISFIED"],
                    detected_contradictions=[conflict_msg],
                    semantic_review_notes=semantic_notes,
                    analyst_action_directive="Proposed FALSE_POSITIVE lacks verifiable authorization evidence for internal targets. Overruled to REQUIRES_ATTENTION.",
                    effective_verdict_override="REQUIRES_ATTENTION",
                )
            elif is_auth_verified:
                semantic_notes.append(f"Scanner Authorization Verified: {auth_detail}")

        # -------------------------------------------------------------
        # Policy Violation Consistency Rules (Archetype: POLICY_VIOLATION)
        # -------------------------------------------------------------
        elif rule_archetype == "POLICY_VIOLATION":
            if clean_prop == "FALSE_POSITIVE":
                is_auth_verified, auth_detail, verified_auth_eids = cls.verify_authorization(
                    supporting_claims=supporting_claims,
                    normalization_result=normalization_result,
                    model_reason=reason_str,
                )
                claims_authorization = any(
                    term in reason_str.lower()
                    for term in ("authorized", "approved exception", "business exemption", "change ticket", "maintenance window")
                )
                if claims_authorization and not is_auth_verified:
                    conflict_msg = (
                        f"Verdict Conflict: Proposed FALSE_POSITIVE asserts business exemption or authorized exception, "
                        f"but no verified change ticket or policy exception was found in canonical evidence records ({auth_detail})."
                    )
                    return ReasoningValidationResult(
                        is_valid=False,
                        validation_status="VERDICT_EVIDENCE_CONFLICT",
                        reason_codes=["VERDICT_EVIDENCE_CONFLICT", "FP_CRITERIA_UNSATISFIED"],
                        detected_contradictions=[conflict_msg],
                        semantic_review_notes=semantic_notes,
                        analyst_action_directive="Proposed FALSE_POSITIVE lacks verifiable authorization evidence. Overruled to REQUIRES_ATTENTION.",
                        effective_verdict_override="REQUIRES_ATTENTION",
                    )
                elif is_auth_verified:
                    semantic_notes.append(f"Policy Exception / Authorization Verified: {auth_detail}")

            elif clean_prop == "TRUE_POSITIVE":
                action_val = str(record_map.get("security.action") or record_map.get("action") or "").lower()
                event_type_val = str(record_map.get("security.event_type") or record_map.get("eventType") or "").lower()
                web_cat = str(record_map.get("webCategory") or "").lower()
                is_violation_telemetry = (
                    any(term in action_val for term in ("blocked", "denied", "dropped"))
                    or "cat-blk" in event_type_val
                    or "filter-block" in event_type_val
                    or bool(web_cat)
                )
                if not is_violation_telemetry:
                    conflict_msg = (
                        "Verdict Conflict: Proposed TRUE_POSITIVE for POLICY_VIOLATION, but telemetry lacks "
                        "policy violation action (blocked/denied) or restricted category."
                    )
                    return ReasoningValidationResult(
                        is_valid=False,
                        validation_status="VERDICT_EVIDENCE_CONFLICT",
                        reason_codes=["VERDICT_EVIDENCE_CONFLICT", "TP_CRITERIA_UNSATISFIED"],
                        detected_contradictions=[conflict_msg],
                        semantic_review_notes=semantic_notes,
                        analyst_action_directive="Proposed TRUE_POSITIVE lacks telemetry proof of policy violation. Overruled to REQUIRES_ATTENTION.",
                        effective_verdict_override="REQUIRES_ATTENTION",
                    )
                else:
                    semantic_notes.append("Policy Violation Telemetry Verified: Confirmed block action or category filtering.")

        # Safe Abstention:
        elif clean_prop in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE"):
            return ReasoningValidationResult(
                is_valid=True,
                validation_status="SAFE_ABSTENTION",
                reason_codes=[],
                detected_contradictions=[],
                semantic_review_notes=semantic_notes,
                analyst_action_directive="Model safely abstained; route to analyst triage.",
                effective_verdict_override="REQUIRES_ATTENTION",
            )

        return ReasoningValidationResult(
            is_valid=True,
            validation_status="VALIDATED",
            reason_codes=[],
            detected_contradictions=[],
            semantic_review_notes=semantic_notes,
            analyst_action_directive="Verdict-evidence consistency verified.",
            effective_verdict_override=None,
        )
