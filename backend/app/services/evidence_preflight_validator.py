import logging
from typing import List, Dict, Any, Optional

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.evidence_preflight import PreflightValidationResult

logger = logging.getLogger(__name__)


class EvidencePreflightValidator:
    """
    P2-REQ-03: Pre-Inference Evidence Validator.
    Runs prior to LLM inference to deterministically evaluate whether the
    mandatory telemetry specified in the approved evidence contract is available.
    """

    @classmethod
    def validate_preflight(
        cls,
        incident_id: str,
        contract: RuleEvidenceContract,
        normalization_result: EvidenceNormalizationResult,
        allow_simulation: bool = False,
    ) -> PreflightValidationResult:
        """
        Executes preflight validation across the canonical evidence against the contract.
        """
        available_fields = set(normalization_result.evidence_by_field.keys())
        all_records = normalization_result.records

        # 1. Check Contract Verification Status
        if contract.status != "APPROVED" and not allow_simulation:
            return PreflightValidationResult(
                incident_id=incident_id,
                rule_id=contract.rule_id,
                contract_id=contract.contract_id,
                contract_version=contract.version_number,
                contract_status=contract.status,
                preflight_status="UNVERIFIABLE",
                required_evidence_count=len(contract.required_evidence),
                available_required_count=0,
                evidence_completeness=0.0,
                missing_evidence_fields=[r.field for r in contract.required_evidence],
                critical_missing_fields=[r.field for r in contract.required_evidence if r.critical],
                can_proceed_to_inference=False,
                must_abstain_immediately=True,
                safe_next_action="DEFER_TO_HUMAN_ANALYST",
                reason="EVIDENCE_CONTRACT_UNVERIFIED: Rule evidence contract is not in APPROVED status.",
            )

        # 2. Check Required Evidence Availability
        # Separate event-level mandatory CORE requirements from optional/conditional
        # enrichment and rule-level metadata (`detection.*`), which do not live in
        # normalized incident telemetry. Mixing them into the denominator previously
        # diluted CORE completeness below 0.6 and caused valid alerts to abstain.
        telemetry_reqs = [
            req for req in contract.required_evidence
            if not str(req.field).startswith("detection.")
        ]
        core_reqs = [
            req for req in telemetry_reqs
            if (
                getattr(req, "requirement_level", "CORE") == "CORE"
                or bool(getattr(req, "critical", False))
                or bool(getattr(req, "required_for_tp", False))
                or bool(getattr(req, "required_for_fp", False))
            )
            and getattr(req, "requirement_level", "CORE") != "UNVERIFIED"
        ] or telemetry_reqs

        def _is_field_present(field_name: str) -> bool:
            if field_name in available_fields:
                return True
            if field_name == "process.name" and ("process.file_name" in available_fields or "process.file_path" in available_fields):
                return True
            if field_name == "network.destination_ip" and (
                "dns.domain" in available_fields
                or "network.destination_domain" in available_fields
                or "endpoint.hostname" in available_fields
            ):
                return True
            if field_name in ("webCategory", "web.category", "web_category") and (
                "webCategory" in available_fields
                or "web.category" in available_fields
                or "web_category" in available_fields
            ):
                return True
            if field_name in ("http.url", "web.url") and (
                "http.url" in available_fields or "web.url" in available_fields
            ):
                return True
            if field_name in ("network.bytes_out", "sentBytes64") and (
                "network.bytes_out" in available_fields or "sentBytes64" in available_fields
            ):
                return True
            return False

        missing_fields: List[str] = []
        core_missing: List[str] = []
        critical_missing: List[str] = []
        satisfied_core_count = 0

        field_status_map: Dict[str, str] = {}
        unmapped_keys = {
            str(u.get("raw_field", "")).strip().lower()
            for u in (getattr(normalization_result, "unmapped_fields", None) or [])
        }

        core_field_names = {r.field for r in core_reqs}
        for req in core_reqs:
            if _is_field_present(req.field):
                satisfied_core_count += 1
                field_status_map[req.field] = "PRESENT_VALID"
            else:
                core_missing.append(req.field)
                missing_fields.append(req.field)
                clean_req = req.field.replace(".", "").replace("_", "").lower()
                is_unmapped = any(clean_req in uk or uk in clean_req for uk in unmapped_keys if uk)
                field_status_map[req.field] = "NOT_MAPPED" if is_unmapped else "NOT_IN_SOURCE"
                if req.critical:
                    critical_missing.append(req.field)

        for req in telemetry_reqs:
            if req.field not in core_field_names:
                if _is_field_present(req.field):
                    field_status_map[req.field] = "PRESENT_VALID"
                else:
                    missing_fields.append(req.field)
                    clean_req = req.field.replace(".", "").replace("_", "").lower()
                    is_unmapped = any(clean_req in uk or uk in clean_req for uk in unmapped_keys if uk)
                    field_status_map[req.field] = "NOT_MAPPED" if is_unmapped else "NOT_IN_SOURCE"

        total_reqs = len(core_reqs)
        completeness = (satisfied_core_count / total_reqs) if total_reqs > 0 else 1.0

        # 3. Check for obvious contradictions in telemetry (e.g. conflicting internal IPs claiming external connection)
        detected_contradictions: List[str] = []
        src_ips = [r.observed_value for r in all_records if r.source_field == "network.source_ip"]
        dst_ips = [r.observed_value for r in all_records if r.source_field == "network.destination_ip"]

        if src_ips and dst_ips and src_ips[0] == dst_ips[0] and src_ips[0] in ("127.0.0.1", "::1", "localhost"):
            detected_contradictions.append("Loopback traffic: source IP and destination IP are identical localhost interfaces")

        # 4. Determine Preflight Status
        if critical_missing:
            status = "INSUFFICIENT"
            can_proceed = False
            must_abstain = True
            action = "DEFER_TO_HUMAN_ANALYST"
            reason = f"CRITICAL_TELEMETRY_MISSING: Mandatory evidence fields missing from incident: {', '.join(critical_missing)}"
        elif detected_contradictions:
            status = "CONTRADICTORY"
            can_proceed = True
            must_abstain = False  # Allow LLM to examine, but validator will guard
            action = "PROCEED_WITH_CONTRADICTION_FLAG"
            reason = f"TELEMETRY_CONTRADICTIONS_DETECTED: {'; '.join(detected_contradictions)}"
        elif core_missing:
            status = "PARTIAL"
            can_proceed = True
            must_abstain = False
            action = "PROCEED_TO_INFERENCE"
            reason = f"PARTIAL_TELEMETRY: Non-critical core evidence fields missing: {', '.join(core_missing)}"
        else:
            status = "COMPLETE"
            can_proceed = True
            must_abstain = False
            action = "PROCEED_TO_INFERENCE"
            reason = "COMPLETE_TELEMETRY: All required core evidence fields present and verified."

        return PreflightValidationResult(
            incident_id=incident_id,
            rule_id=contract.rule_id,
            contract_id=contract.contract_id,
            contract_version=contract.version_number,
            contract_status=contract.status,
            preflight_status=status,
            required_evidence_count=total_reqs,
            available_required_count=satisfied_core_count,
            evidence_completeness=round(completeness, 3),
            missing_evidence_fields=missing_fields,
            critical_missing_fields=critical_missing,
            detected_contradictions=detected_contradictions,
            field_validation_status=field_status_map,
            can_proceed_to_inference=can_proceed,
            must_abstain_immediately=must_abstain,
            safe_next_action=action,
            reason=reason,
        )

