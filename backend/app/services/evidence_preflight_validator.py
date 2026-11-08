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
        missing_fields: List[str] = []
        critical_missing: List[str] = []
        satisfied_count = 0

        for req in contract.required_evidence:
            # Check if this exact field is present in available telemetry
            is_present = False
            if req.field in available_fields:
                is_present = True
            else:
                # Check for semantic field alias (e.g. process.name vs process.file_name)
                if req.field == "process.name" and ("process.file_name" in available_fields or "process.file_path" in available_fields):
                    is_present = True
                elif req.field == "network.destination_ip" and "dns.domain" in available_fields:
                    is_present = True

            if is_present:
                satisfied_count += 1
            else:
                missing_fields.append(req.field)
                if req.critical:
                    critical_missing.append(req.field)

        total_reqs = len(contract.required_evidence)
        completeness = (satisfied_count / total_reqs) if total_reqs > 0 else 1.0

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
        elif missing_fields:
            status = "PARTIAL"
            can_proceed = True
            must_abstain = False
            action = "PROCEED_TO_INFERENCE"
            reason = f"PARTIAL_TELEMETRY: Non-critical evidence fields missing: {', '.join(missing_fields)}"
        else:
            status = "COMPLETE"
            can_proceed = True
            must_abstain = False
            action = "PROCEED_TO_INFERENCE"
            reason = "COMPLETE_TELEMETRY: All required evidence fields present and verified."

        return PreflightValidationResult(
            incident_id=incident_id,
            rule_id=contract.rule_id,
            contract_id=contract.contract_id,
            contract_version=contract.version_number,
            contract_status=contract.status,
            preflight_status=status,
            required_evidence_count=total_reqs,
            available_required_count=satisfied_count,
            evidence_completeness=round(completeness, 3),
            missing_evidence_fields=missing_fields,
            critical_missing_fields=critical_missing,
            detected_contradictions=detected_contradictions,
            can_proceed_to_inference=can_proceed,
            must_abstain_immediately=must_abstain,
            safe_next_action=action,
            reason=reason,
        )

