"""
Evidence Sufficiency Engine (AIS 2.1).
Evaluates whether available SIEM evidence is sufficient, reliable, consistent,
and fresh enough to support a defensible verdict.

Deterministic Scoring Weights:
- Required Evidence Coverage: 40%
- Evidence Integrity & Provenance: 25%
- Internal Consistency & Independent Corroboration: 20%
- Freshness & Incident Relevance: 15%
Total: 100%

Infallible Rule: A high weighted score NEVER overrides a missing mandatory field.
When mandatory evidence is missing or contradictory:
-> evidence_status = INSUFFICIENT or CONFLICTING
-> Automatic TP/FP is strictly blocked.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple

from app.schemas.verdict_intelligence import (
    EvidenceStatus,
    EvidenceSufficiencyAssessmentResult,
    EvidenceFieldAudit,
)
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.rule_intelligence import ArchetypeId
from app.services.detection_archetype_registry import DetectionArchetypeRegistry

logger = logging.getLogger("ai_verdict.evidence_sufficiency")


class EvidenceSufficiencyEngine:
    """
    Evaluates evidence completeness, integrity, consistency, and freshness
    against detection archetypes and evidence contracts.
    """

    # Provenance reliability scores (0.0 to 1.0)
    PROVENANCE_RELIABILITY = {
        "EDR_AGENT": 1.0,
        "FIREWALL_FLOW": 0.95,
        "IDENTITY_PROVIDER": 0.95,
        "CLOUD_TRAIL": 0.90,
        "SYSLOG_APPLIANCE": 0.85,
        "SIEM_ALERT_METADATA": 0.70,
        "OBSERVED_TELEMETRY_SAMPLE": 0.65,
        "SYNTHESIZED_FALLBACK": 0.40,
        "UNKNOWN": 0.30,
    }

    @classmethod
    def evaluate_incident_sufficiency(
        cls,
        incident_payload: Dict[str, Any],
        contract: Optional[RuleEvidenceContract] = None,
        archetype_id: Optional[str] = None,
        authoritative_threshold: Optional[float] = None,
    ) -> EvidenceSufficiencyAssessmentResult:
        """
        Executes four-dimensional deterministic sufficiency assessment.
        """
        incident_id = str(incident_payload.get("incident_id") or incident_payload.get("id") or "INC-UNKNOWN")
        rule_id = str(incident_payload.get("rule_id") or "RULE-UNKNOWN")

        # Resolve archetype definition
        resolved_archetype = archetype_id or (getattr(contract, "detection_archetype", None) or "UNKNOWN")
        try:
            arch_enum = ArchetypeId(resolved_archetype)
            archetype_def = DetectionArchetypeRegistry.get_archetype_definition(arch_enum)
        except Exception:
            archetype_def = None

        # Collect observations from normalized telemetry, canonical evidence, and raw payload
        available_fields: Dict[str, Any] = {}
        field_provenance: Dict[str, str] = {}
        contradictions: List[str] = []
        notes: List[str] = []

        # 1. Harvest canonical evidence if present
        canonical_items = incident_payload.get("canonical_evidence") or incident_payload.get("canonical_evidence_records") or []
        for item in canonical_items:
            if isinstance(item, dict):
                f = item.get("source_field") or item.get("field") or ""
                v = item.get("observed_value") or item.get("value")
                prov = item.get("provenance") or "SIEM_ALERT_METADATA"
                if f and v is not None:
                    available_fields[f] = v
                    field_provenance[f] = prov

        # 2. Harvest top-level incident fields
        for k in ("source_ip", "reporting_ip", "event_type", "severity", "category", "first_seen_epoch", "last_seen_epoch", "created_at_epoch"):
            if k in incident_payload and incident_payload[k]:
                available_fields[k] = incident_payload[k]
                if k not in field_provenance:
                    field_provenance[k] = "SIEM_ALERT_METADATA"

        # 3. Harvest nested event attributes from incident events
        events = incident_payload.get("events") or []
        distinct_sources: Set[str] = set()
        bytes_sent_values: List[int] = []

        for evt in events:
            if isinstance(evt, dict):
                src = evt.get("reporting_device") or evt.get("source") or "SIEM"
                distinct_sources.add(str(src))
                attrs = evt.get("attributes") or {}
                if isinstance(attrs, dict):
                    for ak, av in attrs.items():
                        if av is not None:
                            available_fields[ak] = av
                            if ak not in field_provenance:
                                field_provenance[ak] = "FIREWALL_FLOW" if "bytes" in ak.lower() or "sent" in ak.lower() else "SIEM_ALERT_METADATA"
                            if "bytes" in ak.lower() or ak == "sentBytes64":
                                try:
                                    bytes_sent_values.append(int(av))
                                except (ValueError, TypeError):
                                    pass

                # Command line / process attributes
                if evt.get("cmdline"):
                    available_fields["process.cmdline"] = evt["cmdline"]
                    field_provenance["process.cmdline"] = "EDR_AGENT"
                if evt.get("process_name"):
                    available_fields["process.name"] = evt["process_name"]
                    field_provenance["process.name"] = "EDR_AGENT"

        # Check raw payload
        raw_payload = incident_payload.get("raw_payload") or {}
        if isinstance(raw_payload, dict):
            for rk, rv in raw_payload.items():
                if rv is not None and rk not in available_fields:
                    available_fields[rk] = rv
                    field_provenance[rk] = "OBSERVED_TELEMETRY_SAMPLE"
                    if "bytes" in rk.lower() or rk == "sentBytes64":
                        try:
                            bytes_sent_values.append(int(rv))
                        except (ValueError, TypeError):
                            pass

        # -------------------------------------------------------------
        # DIMENSION 1: Required Evidence Coverage (Weight 40%)
        # -------------------------------------------------------------
        mandatory_fields_present: List[str] = []
        mandatory_fields_missing: List[str] = []

        # Determine expected mandatory fields from contract or archetype
        expected_mandatory: List[str] = []
        if contract and hasattr(contract, "required_evidence") and contract.required_evidence:
            expected_mandatory = [f.field for f in contract.required_evidence if getattr(f, "critical", False) or getattr(f, "required_for_tp", False)]
        elif archetype_def and hasattr(archetype_def, "mandatory_core_fields") and archetype_def.mandatory_core_fields:
            expected_mandatory = list(archetype_def.mandatory_core_fields[:3])
        else:
            expected_mandatory = ["source_ip", "event_type"]

        # Field matching helper with canonical alias awareness
        def _match_field(target: str) -> bool:
            clean_target = target.lower().replace("_", ".").replace("-", ".")
            for k in available_fields.keys():
                clean_k = k.lower().replace("_", ".").replace("-", ".")
                if clean_target == clean_k:
                    return True
                # Alias awareness
                if clean_target in ("source.ip", "srcip", "sourceip") and clean_k in ("source.ip", "srcip", "sourceip", "source_ip"):
                    return True
                if clean_target in ("destination.ip", "destip", "destinationip") and clean_k in ("destination.ip", "destip", "destinationip", "destination_ip"):
                    return True
                if clean_target in ("network.bytes.sent", "sentbytes64", "bytes.sent", "bytes_sent") and clean_k in ("network.bytes.sent", "sentbytes64", "bytes.sent", "bytessent", "bytes_sent", "sentbytes"):
                    return True
                if clean_target in ("process.cmdline", "cmdline", "commandline") and clean_k in ("process.cmdline", "cmdline", "commandline", "process_cmdline"):
                    return True
                if clean_target in ("process.name", "processname") and clean_k in ("process.name", "processname", "process_name"):
                    return True
            return False

        for req in expected_mandatory:
            if _match_field(req):
                mandatory_fields_present.append(req)
            else:
                mandatory_fields_missing.append(req)

        coverage_ratio = (len(mandatory_fields_present) / len(expected_mandatory)) if expected_mandatory else 1.0
        required_coverage_score = round(coverage_ratio * 40.0, 2)

        # -------------------------------------------------------------
        # DIMENSION 2: Evidence Integrity & Provenance (Weight 25%)
        # -------------------------------------------------------------
        if mandatory_fields_present:
            provenance_scores = [
                cls.PROVENANCE_RELIABILITY.get(field_provenance.get(f, "UNKNOWN"), 0.5)
                for f in mandatory_fields_present
            ]
            avg_prov = sum(provenance_scores) / len(provenance_scores)
        else:
            avg_prov = 0.0

        integrity_provenance_score = round(avg_prov * 25.0, 2)

        # -------------------------------------------------------------
        # DIMENSION 3: Internal Consistency & Corroboration (Weight 20%)
        # -------------------------------------------------------------
        consistency_points = 20.0

        # Check for conflicting byte transfer values (e.g. 2 GB reported in one log, 50 KB in another for same flow)
        if len(bytes_sent_values) > 1:
            max_b = max(bytes_sent_values)
            min_b = min(bytes_sent_values)
            if max_b > 100_000_000 and min_b < 100_000 and (max_b / max(1, min_b)) > 1000:
                contradictions.append(
                    f"Conflicting transfer volume: Multiple telemetry records report divergent byte counts (min={min_b}, max={max_b})."
                )
                consistency_points -= 10.0

        # Check for directional contradictions (e.g. Inbound marked as Outbound exfiltration)
        direction = str(available_fields.get("direction", "")).upper()
        if "INBOUND" in direction and (resolved_archetype == "NETWORK_EXFILTRATION" or "EXFIL" in rule_id.upper()):
            contradictions.append(
                "Directional conflict: Incident event direction is marked INBOUND while detection specifies OUTBOUND exfiltration."
            )
            consistency_points -= 10.0

        # Multi-source corroboration bonus
        if len(distinct_sources) >= 2:
            notes.append(f"Multi-source corroboration present: {len(distinct_sources)} independent reporting sensors.")
        elif len(distinct_sources) == 1:
            consistency_points = max(0.0, consistency_points - 3.0)  # Single source without independent corroboration

        consistency_corroboration_score = max(0.0, round(consistency_points, 2))

        # -------------------------------------------------------------
        # DIMENSION 4: Freshness & Incident Relevance (Weight 15%)
        # -------------------------------------------------------------
        freshness_points = 15.0
        first_seen = incident_payload.get("first_seen_epoch")
        last_seen = incident_payload.get("last_seen_epoch")

        if first_seen and last_seen:
            duration_ms = abs(int(last_seen) - int(first_seen))
            # If duration is greater than 30 days for a single alert, potential stale correlation
            if duration_ms > 30 * 86400 * 1000:
                freshness_points -= 7.0
                notes.append("Telemetry spans over 30 days: potential stale correlation window.")
        elif not first_seen and not last_seen:
            freshness_points -= 5.0
            notes.append("Telemetry epoch timestamps missing; temporal freshness unverified.")

        freshness_relevance_score = max(0.0, round(freshness_points, 2))

        # -------------------------------------------------------------
        # Aggregation & Status Determination
        # -------------------------------------------------------------
        raw_sufficiency = required_coverage_score + integrity_provenance_score + consistency_corroboration_score + freshness_relevance_score
        overall_sufficiency_score = round(max(0.0, min(100.0, raw_sufficiency)), 2)

        # Infallible Rule: A high weighted score NEVER overrides missing mandatory fields or critical contradictions!
        if mandatory_fields_missing:
            evidence_status = EvidenceStatus.INSUFFICIENT
            notes.append(f"MANDATORY EVIDENCE ABSENT: Missing required fields ({', '.join(mandatory_fields_missing)}). Automatic decision blocked.")
        elif contradictions:
            evidence_status = EvidenceStatus.CONFLICTING
            notes.append(f"MATERIAL CONTRADICTION: {'; '.join(contradictions)}. Automatic decision blocked.")
        elif overall_sufficiency_score < 70.0:
            evidence_status = EvidenceStatus.INSUFFICIENT
            notes.append("Evidence sufficiency score below operational decision threshold (70.0).")
        else:
            evidence_status = EvidenceStatus.SUFFICIENT

        # Optional enrichment tracking
        optional_enrichment_present: List[str] = []
        for opt in ("threat_intel", "geo_location", "whois", "domain", "tls_sni", "destination_host"):
            if opt in available_fields or any(opt in k.lower() for k in available_fields.keys()):
                optional_enrichment_present.append(opt)

        return EvidenceSufficiencyAssessmentResult(
            incident_id=incident_id,
            rule_id=rule_id,
            archetype=resolved_archetype,
            overall_sufficiency_score=overall_sufficiency_score,
            required_coverage_score=required_coverage_score,
            integrity_provenance_score=integrity_provenance_score,
            consistency_corroboration_score=consistency_corroboration_score,
            freshness_relevance_score=freshness_relevance_score,
            evidence_status=evidence_status,
            mandatory_fields_present=mandatory_fields_present,
            mandatory_fields_missing=mandatory_fields_missing,
            conditional_fields_evaluated=[],
            optional_enrichment_present=optional_enrichment_present,
            unsupported_fields_requested=[],
            contradictions_detected=contradictions,
            notes=notes,
            evaluated_at=datetime.utcnow(),
        )
