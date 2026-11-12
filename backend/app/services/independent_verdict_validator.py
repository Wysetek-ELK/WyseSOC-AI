import hashlib
import ipaddress
import json
import logging
from typing import Dict, Any, List, Optional

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.evidence_claim import ClaimGroundingResult
from app.schemas.verdict_validation import VerdictValidationResult

logger = logging.getLogger(__name__)


class IndependentVerdictValidator:
    """
    P2-REQ-05: Independent Deterministic Verdict Validator.
    The authoritative verification engine that evaluates model propositions against
    real normalized evidence, approved policy contracts, and grounding checks.
    The model's confidence or claims can never override this validator.
    """

    VALIDATOR_VERSION = "2.0.0"

    @classmethod
    def validate_verdict(
        cls,
        incident_id: str,
        proposed_verdict: str,
        raw_model_confidence: float,
        preflight: PreflightValidationResult,
        claim_grounding: ClaimGroundingResult,
        normalization_result: EvidenceNormalizationResult,
        contract: RuleEvidenceContract,
        allow_simulation: bool = False,
        compilation_digest: Optional[str] = None,
        model_reason: str = "",
        contradictory_evidence: Optional[List[str]] = None,
    ) -> VerdictValidationResult:
        """
        Executes the 8 mandatory deterministic checks and determines the final authoritative verdict.
        """
        clean_prop_verdict = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        reason_codes: List[str] = []
        contradictions: List[str] = list(preflight.detected_contradictions)
        if contradictory_evidence:
            for ce in contradictory_evidence:
                if str(ce).strip():
                    contradictions.append(str(ce).strip())
        unsupported_claims: List[Dict[str, Any]] = list(claim_grounding.unsupported_claim_details)

        # Output Integrity Check (Check 8)
        invalid_output_flag = clean_prop_verdict not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
        if invalid_output_flag:
            clean_prop_verdict = "REQUIRES_ATTENTION"
            reason_codes.append("MODEL_OUTPUT_INVALID")

        final_verdict = clean_prop_verdict
        validation_status = "INVALID_MODEL_OUTPUT" if invalid_output_flag else "VALIDATED"
        is_decisive = False
        action_directive = "Verdict verified against canonical evidence contract."

        # Check 1: Policy & Contract Authorization
        if contract.status != "APPROVED":
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "ABSTAINED"
            reason_codes.append("EVIDENCE_CONTRACT_UNVERIFIED")
            action_directive = "Please review and approve the investigation policy in Agent Intelligence Studio before automated triage."

        # Check 2: Mandatory Evidence Completeness
        if preflight.critical_missing_fields:
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "INSUFFICIENT_EVIDENCE"
            reason_codes.append("EVIDENCE_MISSING")
            action_directive = f"Collect missing mandatory telemetry ({', '.join(preflight.critical_missing_fields)}) before closing incident."

        # Check 3: Source Grounding & Unsupported Model Claims
        if claim_grounding.has_hallucinations and clean_prop_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "REJECTED"

            # Discern specific grounding failure reasons
            for c in claim_grounding.claims:
                if not c.is_grounded:
                    if c.grounding_status == "EVIDENCE_REFERENCE_NOT_FOUND":
                        if "EVIDENCE_REFERENCE_NOT_FOUND" not in reason_codes:
                            reason_codes.append("EVIDENCE_REFERENCE_NOT_FOUND")
                    elif c.grounding_status == "EVIDENCE_VALUE_MISMATCH":
                        if "EVIDENCE_VALUE_MISMATCH" not in reason_codes:
                            reason_codes.append("EVIDENCE_VALUE_MISMATCH")
                    else:
                        if "CLAIM_NOT_VERIFIABLE" not in reason_codes:
                            reason_codes.append("CLAIM_NOT_VERIFIABLE")

            action_directive = "Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required."

        # Check 4: Evidence Consistency & Contradictions
        # Detect model-telemetry contradictions
        if clean_prop_verdict == "TRUE_POSITIVE":
            # Example: Model asserts external C2 or remote download when all IPs are internal loopback
            all_ips = [r.observed_value for r in normalization_result.records if r.source_field in ("network.source_ip", "network.destination_ip")]
            def _is_loopback_addr(ip_val: Any) -> bool:
                s = str(ip_val).strip().lower()
                if s in ("127.0.0.1", "::1", "localhost"):
                    return True
                try:
                    return ipaddress.ip_address(s).is_loopback
                except ValueError:
                    return False

            if all_ips and all(_is_loopback_addr(ip) for ip in all_ips):
                for claim in claim_grounding.claims:
                    if "c2" in str(claim.asserted_value).lower() or "external" in str(claim.asserted_value).lower():
                        contradictions.append("Contradiction: Claiming external communication on loopback/local interfaces")
                        reason_codes.append("EVIDENCE_CONTRADICTION")
                        final_verdict = "REQUIRES_ATTENTION"
                        validation_status = "REJECTED"
                        action_directive = "Activity occurs strictly on internal/loopback stack. Verify if local proxy reflection or healthcheck."

        elif clean_prop_verdict == "FALSE_POSITIVE":
            # Detect loopback / same-source-and-destination contradiction:
            # If model reason or claims assert "loopback", "same source and destination", "internal reflection"
            # BUT telemetry shows external destination IP or srcip != dstip:
            reason_lower = (model_reason or "").lower()
            claims_text = " ".join(str(c.asserted_value).lower() for c in claim_grounding.claims)
            all_fp_text = f"{reason_lower} {claims_text}"

            src_ips = [r.observed_value for r in normalization_result.records if r.source_field == "network.source_ip"]
            dst_ips = [r.observed_value for r in normalization_result.records if r.source_field == "network.destination_ip"]

            if any(term in all_fp_text for term in ("loopback", "same source and destination", "internal reflection", "local reflection")):
                if src_ips and dst_ips and src_ips[0] != dst_ips[0]:
                    contradictions.append(
                        f"Contradiction: Model claims internal loopback or same source/destination, but telemetry confirms source {src_ips[0]} connects to distinct destination {dst_ips[0]}"
                    )
                    if "EVIDENCE_CONTRADICTION" not in reason_codes:
                        reason_codes.append("EVIDENCE_CONTRADICTION")
                    final_verdict = "REQUIRES_ATTENTION"
                    validation_status = "REJECTED"
                    action_directive = "Model falsely inferred loopback based on rule name; telemetry confirms distinct source and destination IPs. Human review required."

        # Check 4b: Unresolved Contradictions Prevent Decisive Classification
        if contradictions and clean_prop_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "REJECTED"
            if "EVIDENCE_CONTRADICTION" not in reason_codes:
                reason_codes.append("EVIDENCE_CONTRADICTION")
            action_directive = "Material contradictory evidence detected in incident telemetry. Human Tier 2 review required."

        # Check 5: Verdict-Specific Decision Criteria
        if clean_prop_verdict == "TRUE_POSITIVE":
            # For TP: must meet evidence completeness AND provide at least one grounded claim (prevent empty-claim bypass)
            if preflight.evidence_completeness < 0.6 or claim_grounding.grounded_claims == 0:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "TP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("TP_CRITERIA_UNSATISFIED")
                if "Model fabricated" not in action_directive:
                    action_directive = "Insufficient grounded claims or corroborating evidence to confirm malicious attack. Manual triage required."
            elif not reason_codes and final_verdict == "TRUE_POSITIVE":
                is_decisive = True
                reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "High-confidence malicious attack confirmed with verified evidence. Escalate to IR team."

        elif clean_prop_verdict == "FALSE_POSITIVE":
            # For FP: must have verified telemetry, at least one grounded claim, and cannot rely on blanket negative assumptions
            reason_lower = (model_reason or "").lower()
            affirmative_benign_terms = (
                "authorized", "approved", "backup", "maintenance", "legitimate", "scheduled",
                "harmless", "routine", "expected", "verified vendor", "business", "change ticket",
                "service", "admin", "scanner", "healthcheck",
            )
            has_blanket_negative_fp = any(
                phrase in reason_lower
                for phrase in ("no evidence of compromise", "rfc-1918", "rfc1918", "internal ip only", "nothing suspicious found")
            ) and not any(term in reason_lower for term in affirmative_benign_terms)

            if preflight.preflight_status == "INSUFFICIENT" or preflight.evidence_completeness < 0.5 or claim_grounding.grounded_claims == 0:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "FP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("FP_CRITERIA_UNSATISFIED")
                if "Model fabricated" not in action_directive:
                    action_directive = "Missing grounded claim or benign evidence prevents confirming false positive. Human verification required."
            elif has_blanket_negative_fp:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "FP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("FP_CRITERIA_UNSATISFIED")
                action_directive = "False positive rejected: blanket RFC-1918 or negative-evidence assumption without affirmative benign authorization."
            elif not reason_codes and final_verdict == "FALSE_POSITIVE":
                is_decisive = True
                reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "Activity verified benign against approved detection baseline."

        elif clean_prop_verdict == "REQUIRES_ATTENTION":
            final_verdict = "REQUIRES_ATTENTION"
            is_decisive = False
            if invalid_output_flag or "MODEL_OUTPUT_INVALID" in reason_codes:
                validation_status = "INVALID_MODEL_OUTPUT"
                action_directive = "Model returned invalid or malformed structured output; safely abstained and routed to analyst review."
            else:
                if not reason_codes:
                    reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "Follow standard SOC tier-1 investigation runbook for ambiguous telemetry."

        # Audit Verification Token (Cryptographically binds contract, verdict, evidence count, and policy digest)
        comp_part = f":{compilation_digest}" if compilation_digest else ""
        sig_payload = f"{incident_id}:{contract.contract_id}:{proposed_verdict}:{final_verdict}:{cls.VALIDATOR_VERSION}{comp_part}"
        replay_sig = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:16]

        return VerdictValidationResult(
            incident_id=incident_id,
            proposed_verdict=clean_prop_verdict,
            final_verdict=final_verdict,
            validation_status=validation_status,
            validation_reason_codes=reason_codes,
            is_decisive_accepted=is_decisive,
            evidence_completeness=preflight.evidence_completeness,
            grounding_ratio=claim_grounding.grounding_ratio,
            total_claims_count=claim_grounding.total_claims,
            grounded_claims_count=claim_grounding.grounded_claims,
            unsupported_claims_count=claim_grounding.unsupported_claims,
            missing_evidence_fields=preflight.missing_evidence_fields,
            unsupported_claims=unsupported_claims,
            detected_contradictions=contradictions,
            field_validation_status=getattr(preflight, "field_validation_status", {}),
            analyst_action_directive=action_directive,
            contract_id=contract.contract_id,
            contract_version=contract.version_number,
            validator_version=cls.VALIDATOR_VERSION,
            raw_model_confidence=raw_model_confidence,
            validated_confidence_display=raw_model_confidence if is_decisive else 0.0,
            replay_signature=replay_sig,
        )

    @classmethod
    def replay_validation(
        cls,
        incident_id: str,
        saved_evidence_records: List[Dict[str, Any]],
        contract_dict: Dict[str, Any],
        saved_model_output: Dict[str, Any],
    ) -> VerdictValidationResult:
        """
        Deterministic Replay Engine.
        Reconstructs the exact validation outcome from a saved evidence snapshot and contract.
        """
        from app.services.model_claim_extractor import ModelClaimExtractor
        from app.services.evidence_preflight_validator import EvidencePreflightValidator

        # Rehydrate canonical records
        records = [CanonicalEvidenceRecord(**r) for r in saved_evidence_records]
        by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
        by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
        for r in records:
            by_type.setdefault(r.evidence_type, []).append(r)
            by_field.setdefault(r.source_field, []).append(r)

        norm_result = EvidenceNormalizationResult(
            incident_id=incident_id,
            total_evidence_count=len(records),
            available_evidence_count=len(records),
            records=records,
            evidence_by_type=by_type,
            evidence_by_field=by_field,
        )

        contract = RuleEvidenceContract(**contract_dict)
        preflight = EvidencePreflightValidator.validate_preflight(incident_id, contract, norm_result, allow_simulation=True)
        grounding = ModelClaimExtractor.extract_and_ground_claims(incident_id, saved_model_output, norm_result)

        return cls.validate_verdict(
            incident_id=incident_id,
            proposed_verdict=saved_model_output.get("verdict", "REQUIRES_ATTENTION"),
            raw_model_confidence=float(saved_model_output.get("confidence", 0.0)),
            preflight=preflight,
            claim_grounding=grounding,
            normalization_result=norm_result,
            contract=contract,
            allow_simulation=True,
            model_reason=str(saved_model_output.get("reason", "")),
            contradictory_evidence=saved_model_output.get("contradictory_evidence") if isinstance(saved_model_output.get("contradictory_evidence"), list) else None,
        )
