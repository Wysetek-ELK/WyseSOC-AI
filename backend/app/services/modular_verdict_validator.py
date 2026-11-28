"""
AIS 3.2 — Modular Rule-Aware Independent Verdict Validator.

Composable, declarative validation architecture covering all 11 canonical archetypes
plus legacy CrowdStrike & Prisma SASE compatibility without universal endpoint coupling.

Modules executed in deterministic order:
  1. Core Verdict Schema Validator
  2. Evidence Reference Validator
  3. Claim Grounding Validator
  4. Rule Criteria & Detection Semantics Validator
  5. Organizational Context & Authorization Evidence Validator
  6. Archetype Declarative Validator (dispatched by canonical archetype)
  7. Verdict-to-Reasoning & Semantic Consistency Validator
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.canonical_evidence import EvidenceNormalizationResult
from app.schemas.dynamic_rule_contract import DynamicRuleContract
from app.schemas.evidence_claim import ClaimGroundingResult
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.verdict_validation import VerdictValidationResult
from app.services.confidence_normalizer import ConfidenceNormalizer
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.reasoning_integrity_engine import ReasoningIntegrityEngine
from app.services.verdict_semantics_engine import VerdictSemanticsEngine


@dataclass(frozen=True)
class ArchetypeValidatorProfile:
    module_name: str
    canonical_archetype: str
    requires_endpoint_process_for_tp: bool
    requires_affirmative_auth_for_fp: bool
    allows_siem_reported_detection_tp: bool
    allows_blocked_traffic_as_tp: bool
    min_grounded_claims_for_decisive: int = 1
    required_signal_fields: Tuple[str, ...] = ()


# Declarative validation profiles for all 11 canonical AIS 3.2 archetypes
ARCHETYPE_VALIDATOR_PROFILES: Dict[str, ArchetypeValidatorProfile] = {
    "NETWORK_RECONNAISSANCE": ArchetypeValidatorProfile(
        module_name="NetworkReconnaissanceValidator",
        canonical_archetype="NETWORK_RECONNAISSANCE",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("network.source_ip", "security.event_type", "scan.connection_count", "network.destination_port", "network.destination_ip"),
    ),
    "FIREWALL_SECURITY": ArchetypeValidatorProfile(
        module_name="FirewallSecurityValidator",
        canonical_archetype="FIREWALL_SECURITY",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("network.source_ip", "network.destination_ip", "security.event_type", "security.action", "webCategory"),
    ),
    "ENDPOINT_SECURITY": ArchetypeValidatorProfile(
        module_name="EndpointSecurityValidator",
        canonical_archetype="ENDPOINT_SECURITY",
        requires_endpoint_process_for_tp=True,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=False,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("process.name", "process.command_line", "file.name", "file.hash_sha256", "endpoint.hostname"),
    ),
    "AUTHENTICATION_SECURITY": ArchetypeValidatorProfile(
        module_name="AuthenticationValidator",
        canonical_archetype="AUTHENTICATION_SECURITY",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("user.name", "network.source_ip", "endpoint.hostname", "security.event_type", "auth.result"),
    ),
    "DNS_SECURITY": ArchetypeValidatorProfile(
        module_name="DNSValidator",
        canonical_archetype="DNS_SECURITY",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("network.source_ip", "network.destination_ip", "network.destination_domain", "dns.query_name", "security.event_type"),
    ),
    "DATA_TRANSFER": ArchetypeValidatorProfile(
        module_name="DataTransferValidator",
        canonical_archetype="DATA_TRANSFER",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=False,
        required_signal_fields=("network.source_ip", "network.destination_ip", "network.bytes_out", "sentBytes64", "security.event_type"),
    ),
    "IPS_IDS": ArchetypeValidatorProfile(
        module_name="IPSIDSValidator",
        canonical_archetype="IPS_IDS",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("network.source_ip", "network.destination_ip", "security.event_type", "security.message", "http.url"),
    ),
    "CONFIGURATION_MONITORING": ArchetypeValidatorProfile(
        module_name="ConfigurationMonitoringValidator",
        canonical_archetype="CONFIGURATION_MONITORING",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=False,
        required_signal_fields=("security.event_type", "endpoint.hostname", "user.name", "security.message"),
    ),
    "OPERATIONAL_MONITORING": ArchetypeValidatorProfile(
        module_name="OperationalMonitoringValidator",
        canonical_archetype="OPERATIONAL_MONITORING",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=False,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=False,
        required_signal_fields=("security.event_type", "endpoint.hostname", "endpoint.ip", "security.message"),
    ),
    "THREAT_INTELLIGENCE": ArchetypeValidatorProfile(
        module_name="ThreatIntelligenceValidator",
        canonical_archetype="THREAT_INTELLIGENCE",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=True,
        allows_blocked_traffic_as_tp=True,
        required_signal_fields=("network.source_ip", "network.destination_ip", "security.event_type", "security.action"),
    ),
    "GENERIC_UNKNOWN": ArchetypeValidatorProfile(
        module_name="UnknownRuleSafetyValidator",
        canonical_archetype="GENERIC_UNKNOWN",
        requires_endpoint_process_for_tp=False,
        requires_affirmative_auth_for_fp=True,
        allows_siem_reported_detection_tp=False,
        allows_blocked_traffic_as_tp=False,
        required_signal_fields=("security.event_type",),
    ),
}


class ModularVerdictValidator:
    """
    AIS 3.2 Modular Independent Verdict Validator.
    Replaces universal endpoint-only coupling with rule-contract & archetype-aware validation,
    while delegating legacy CrowdStrike / Prisma SASE cases cleanly to preserve backward compatibility.
    """

    VALIDATOR_VERSION = "3.2.0"

    @classmethod
    def get_module_registry(cls) -> List[Dict[str, Any]]:
        return [
            {
                "module_name": p.module_name,
                "canonical_archetype": p.canonical_archetype,
                "requires_endpoint_process_for_tp": p.requires_endpoint_process_for_tp,
                "requires_affirmative_auth_for_fp": p.requires_affirmative_auth_for_fp,
                "allows_siem_reported_detection_tp": p.allows_siem_reported_detection_tp,
                "allows_blocked_traffic_as_tp": p.allows_blocked_traffic_as_tp,
            }
            for p in ARCHETYPE_VALIDATOR_PROFILES.values()
        ]

    @classmethod
    def validate(
        cls,
        *,
        incident_id: str,
        proposed_verdict: str,
        raw_model_confidence: float,
        preflight: PreflightValidationResult,
        claim_grounding: ClaimGroundingResult,
        normalization_result: EvidenceNormalizationResult,
        legacy_contract: RuleEvidenceContract,
        dynamic_contract: DynamicRuleContract,
        org_context: Optional[Dict[str, Any]] = None,
        model_output: Optional[Dict[str, Any]] = None,
        structured_check: Optional[Dict[str, Any]] = None,
        allow_provisional_contracts: bool = True,
    ) -> VerdictValidationResult:
        """
        Executes modular validation across all checks and returns rich VerdictValidationResult.
        """
        mo = model_output or {}
        rule_id_l = (dynamic_contract.fortisiem_rule_id or "").lower()
        canon_arch = VerdictSemanticsEngine.canonical_archetype(dynamic_contract.rule_archetype)

        # Preserve exact legacy CrowdStrike / Prisma SASE validator behavior
        if (
            canon_arch == "ENDPOINT_SECURITY"
            or "cs_suspicious" in rule_id_l
            or "crowdstrike" in rule_id_l
            or "prisma" in rule_id_l
            or "suspicious_file" in rule_id_l
        ):
            leg = IndependentVerdictValidator.validate_verdict(
                incident_id=incident_id,
                proposed_verdict=proposed_verdict,
                raw_model_confidence=raw_model_confidence,
                preflight=preflight,
                claim_grounding=claim_grounding,
                normalization_result=normalization_result,
                contract=legacy_contract,
                allow_simulation=allow_provisional_contracts,
                model_reason=str(mo.get("reason") or ""),
                contradictory_evidence=mo.get("contradictory_evidence"),
                confidence_scale=mo.get("confidence_scale"),
            )
            leg.validator_module = "LegacyEndpointOrPrismaValidator"
            return leg

        profile = ARCHETYPE_VALIDATOR_PROFILES.get(canon_arch, ARCHETYPE_VALIDATOR_PROFILES["GENERIC_UNKNOWN"])
        raw_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        if raw_prop in ("REQUIRES_ANALYST_ATTENTION", "INCONCLUSIVE", "INSUFFICIENT_EVIDENCE"):
            clean_prop = "REQUIRES_ATTENTION"
        else:
            clean_prop = raw_prop

        reason_codes: List[str] = []
        contradictions: List[str] = list(preflight.detected_contradictions)
        for ce in (mo.get("contradictory_evidence") or []):
            if str(ce).strip():
                contradictions.append(str(ce).strip())
        unsupported_claims: List[Dict[str, Any]] = list(claim_grounding.unsupported_claim_details)
        model_reason = str(mo.get("reason") or "")

        failed_check: Optional[str] = None
        failure_severity: Optional[str] = None
        failure_classification: Optional[str] = None
        evidence_ref: Optional[str] = None

        # 1. Core Verdict Schema Validator
        if structured_check and (structured_check.get("truncated_output") or not structured_check.get("schema_valid", True)):
            is_trunc = bool(structured_check.get("truncated_output"))
            return VerdictValidationResult(
                incident_id=incident_id,
                proposed_verdict=clean_prop if clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION") else "REQUIRES_ATTENTION",
                final_verdict="REQUIRES_ATTENTION",
                validation_status="TRUNCATED_OUTPUT" if is_trunc else "INVALID_MODEL_OUTPUT",
                validation_reason_codes=["OUTPUT_TRUNCATED" if is_trunc else "MODEL_OUTPUT_INVALID"],
                is_decisive_accepted=False,
                evidence_completeness=preflight.evidence_completeness,
                grounding_ratio=claim_grounding.grounding_ratio,
                total_claims_count=claim_grounding.total_claims,
                grounded_claims_count=claim_grounding.grounded_claims,
                unsupported_claims_count=claim_grounding.unsupported_claims,
                missing_evidence_fields=preflight.missing_evidence_fields,
                unsupported_claims=unsupported_claims,
                detected_contradictions=contradictions,
                analyst_action_directive="Model emitted truncated or malformed structured JSON output.",
                contract_id=dynamic_contract.contract_id,
                contract_version=dynamic_contract.contract_version,
                validator_version=cls.VALIDATOR_VERSION,
                raw_model_confidence=raw_model_confidence,
                validator_module="CoreVerdictSchemaValidator",
                failed_check="STRUCTURED_OUTPUT_SCHEMA",
                failure_severity="HIGH",
                failure_classification="SCHEMA_ERROR",
            )

        if clean_prop not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"):
            return VerdictValidationResult(
                incident_id=incident_id,
                proposed_verdict="REQUIRES_ATTENTION",
                final_verdict="REQUIRES_ATTENTION",
                validation_status="INVALID_MODEL_OUTPUT",
                validation_reason_codes=["MODEL_OUTPUT_INVALID"],
                is_decisive_accepted=False,
                evidence_completeness=preflight.evidence_completeness,
                grounding_ratio=claim_grounding.grounding_ratio,
                analyst_action_directive=f"Unsupported verdict label '{proposed_verdict}'.",
                contract_id=dynamic_contract.contract_id,
                contract_version=dynamic_contract.contract_version,
                validator_version=cls.VALIDATOR_VERSION,
                raw_model_confidence=raw_model_confidence,
                validator_module="CoreVerdictSchemaValidator",
                failed_check="VERDICT_ENUM",
                failure_severity="HIGH",
                failure_classification="SCHEMA_ERROR",
            )

        norm_conf = ConfidenceNormalizer.normalize(raw_model_confidence, mo.get("confidence_scale"))
        if not norm_conf.is_valid and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            return VerdictValidationResult(
                incident_id=incident_id,
                proposed_verdict=clean_prop,
                final_verdict="REQUIRES_ATTENTION",
                validation_status="INVALID_MODEL_OUTPUT",
                validation_reason_codes=[norm_conf.interpretation, "MODEL_OUTPUT_INVALID"],
                is_decisive_accepted=False,
                evidence_completeness=preflight.evidence_completeness,
                grounding_ratio=claim_grounding.grounding_ratio,
                analyst_action_directive=norm_conf.error_message or "Invalid confidence score.",
                contract_id=dynamic_contract.contract_id,
                contract_version=dynamic_contract.contract_version,
                validator_version=cls.VALIDATOR_VERSION,
                raw_model_confidence=raw_model_confidence,
                validator_module="CoreVerdictSchemaValidator",
                failed_check="CONFIDENCE_SCALE",
                failure_severity="MEDIUM",
                failure_classification="SCHEMA_ERROR",
            )

        final_verdict = clean_prop
        validation_status = "VALIDATED"
        action_directive = "Verdict validated against dynamic rule contract and canonical evidence."
        is_decisive = False

        # 2. Contract Approval Check (skipped when provisional development/advisory contracts are explicitly permitted)
        if not allow_provisional_contracts and dynamic_contract.approval_state.value != "APPROVED":
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "ABSTAINED"
            reason_codes.append("EVIDENCE_CONTRACT_UNVERIFIED")
            failed_check = "CONTRACT_APPROVAL"
            failure_severity = "MEDIUM"
            failure_classification = "POLICY_GOVERNANCE"
            action_directive = "Rule contract is provisional and requires approval before non-advisory enforcement."

        # 3. Mandatory Evidence Completeness
        if preflight.critical_missing_fields and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "INSUFFICIENT_EVIDENCE"
            reason_codes.append("EVIDENCE_MISSING")
            failed_check = "MANDATORY_EVIDENCE"
            failure_severity = "HIGH"
            failure_classification = "EVIDENCE_INSUFFICIENCY"
            action_directive = f"Missing critical mandatory evidence: {', '.join(preflight.critical_missing_fields)}."

        # 4. Claim Grounding & Evidence References
        if (claim_grounding.has_hallucinations or claim_grounding.unsupported_claims > 0) and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "REJECTED"
            for c in claim_grounding.claims:
                if not c.is_grounded:
                    evidence_ref = ", ".join(c.evidence_ids) if getattr(c, "evidence_ids", None) else c.field
                    if c.grounding_status not in reason_codes:
                        reason_codes.append(c.grounding_status or "UNSUPPORTED_CLAIM")
            if "UNSUPPORTED_CLAIM" not in reason_codes:
                reason_codes.append("UNSUPPORTED_CLAIM")
            failed_check = "CLAIM_GROUNDING"
            failure_severity = "HIGH"
            failure_classification = "UNSUPPORTED_CLAIM"
            action_directive = "One or more factual claims could not be grounded in canonical evidence."

        # 5. Reasoning Integrity Cross-Validation
        reasoning_res = ReasoningIntegrityEngine.evaluate_reasoning_integrity(
            incident_id=incident_id,
            proposed_verdict=clean_prop,
            model_reason=model_reason,
            supporting_claims=claim_grounding.claims,
            normalization_result=normalization_result,
            contradictory_evidence=mo.get("contradictory_evidence"),
        )
        if not reasoning_res.is_valid:
            contradictions.extend(c for c in reasoning_res.detected_contradictions if c not in contradictions)
            reason_codes.extend(rc for rc in reasoning_res.reason_codes if rc not in reason_codes)
            if clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REASONING_CONTRADICTION"
                failed_check = "REASONING_INTEGRITY"
                failure_severity = "HIGH"
                failure_classification = "CONTRADICTION"
                action_directive = reasoning_res.analyst_action_directive

        # 6. Verdict Semantics Consistency Check
        sem_eval = VerdictSemanticsEngine.evaluate_semantics(
            archetype=canon_arch,
            proposed_verdict=clean_prop,
            detection_validity=mo.get("detection_validity"),
            activity_characterization=mo.get("activity_characterization"),
            authorization_status=mo.get("authorization_status"),
            operational_impact=mo.get("operational_impact"),
        )
        if not sem_eval.is_semantically_consistent and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "VERDICT_EVIDENCE_CONFLICT"
            reason_codes.append("SEMANTIC_DIMENSION_CONTRADICTION")
            failed_check = "SEMANTIC_CONSISTENCY"
            failure_severity = "HIGH"
            failure_classification = "CONTRADICTION"
            action_directive = "; ".join(sem_eval.consistency_issues)

        # 7. Archetype-Aware Criteria & Authorization Validation (No endpoint coupling!)
        available_fields = {r.source_field for r in normalization_result.records if r.observed_value not in (None, "", "null")}
        grounded_claims = [c for c in claim_grounding.claims if c.is_grounded]
        has_org_auth = bool(org_context and org_context.get("authorizes_activity") is True)
        authoritative_auth_fields = {
            "authorization.ticket_id", "authorization.change_ticket", "authorization.change_request",
            "itsm.ticket_id", "change_management.ticket", "policy.approved_baseline",
        }
        has_telemetry_auth = any(r.source_field in authoritative_auth_fields for r in normalization_result.records)

        if final_verdict == "TRUE_POSITIVE":
            # Unknown rules require explicit corroborated security/policy evidence
            if canon_arch == "GENERIC_UNKNOWN" and (not dynamic_contract.is_supported_rule) and len(grounded_claims) < 1:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "INSUFFICIENT_EVIDENCE"
                reason_codes.append("UNSUPPORTED_RULE_ABSTENTION")
                failed_check = "UNKNOWN_RULE_SAFETY"
                failure_severity = "MEDIUM"
                failure_classification = "EVIDENCE_INSUFFICIENCY"
                action_directive = "Unclassified rule requires grounded supporting evidence or manual review."
            elif len(grounded_claims) < profile.min_grounded_claims_for_decisive:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "INSUFFICIENT_EVIDENCE"
                reason_codes.append("TP_CRITERIA_UNSATISFIED")
                failed_check = "GROUNDED_CLAIM_MINIMUM"
                failure_severity = "MEDIUM"
                failure_classification = "EVIDENCE_INSUFFICIENCY"
                action_directive = "Decisive TRUE_POSITIVE requires at least one grounded canonical evidence claim."
            elif not (available_fields & set(profile.required_signal_fields) or available_fields):
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "INSUFFICIENT_EVIDENCE"
                reason_codes.append("TP_CRITERIA_UNSATISFIED")
                failed_check = "ARCHETYPE_SIGNAL_PRESENCE"
                failure_severity = "MEDIUM"
                failure_classification = "EVIDENCE_INSUFFICIENCY"
                action_directive = f"Missing expected telemetry fields for {canon_arch}."
            elif has_org_auth and canon_arch in ("NETWORK_RECONNAISSANCE", "CONFIGURATION_MONITORING"):
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                reason_codes.append("BENIGN_CONTEXT_CONTRADICTION")
                failed_check = "ORG_CONTEXT_CONFLICT"
                failure_severity = "HIGH"
                failure_classification = "CONTRADICTION"
                action_directive = "TRUE_POSITIVE conflicts with verified organizational authorization context."

        elif final_verdict == "FALSE_POSITIVE":
            reason_l = model_reason.lower()
            # Invented ticket check (preserved across all archetypes)
            ticket_patterns = set(re.findall(
                r'\b(?:CHG|CR|TICKET|WO|REQ)[-_]?[0-9]{3,}\b|\bRFC[-_]?(?!1918|5737|3330)[0-9]{3,}\b',
                model_reason,
                re.IGNORECASE,
            ))
            invented_tickets = [
                tp for tp in ticket_patterns
                if not any(tp.lower() in str(r.observed_value).lower() for r in normalization_result.records)
            ]
            if invented_tickets:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                reason_codes.append("INVENTED_CHANGE_TICKET")
                failed_check = "INVENTED_CHANGE_TICKET"
                failure_severity = "HIGH"
                failure_classification = "UNSUPPORTED_CLAIM"
                action_directive = f"Rejected unverified ticket reference(s): {', '.join(invented_tickets)}."
            elif len(grounded_claims) < profile.min_grounded_claims_for_decisive:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "INSUFFICIENT_EVIDENCE"
                reason_codes.append("FP_CRITERIA_UNSATISFIED")
                failed_check = "GROUNDED_CLAIM_MINIMUM"
                failure_severity = "MEDIUM"
                failure_classification = "EVIDENCE_INSUFFICIENCY"
                action_directive = "Decisive FALSE_POSITIVE requires at least one grounded canonical evidence claim."
            elif canon_arch == "OPERATIONAL_MONITORING":
                # Operational monitoring FP requires verified maintenance/decommission OR explicit recovery telemetry
                has_recovery_signal = any(
                    term in reason_l for term in ("resumed", "recovered", "no outage", "false alert")
                ) and any(
                    term in str(r.observed_value).lower()
                    for r in normalization_result.records
                    for term in ("resumed", "normal", "ok", "recovered")
                )
                if not (has_org_auth or has_telemetry_auth or has_recovery_signal):
                    final_verdict = "REQUIRES_ATTENTION"
                    validation_status = "REJECTED"
                    reason_codes.append("OPERATIONAL_TP_MISCLASSIFIED_AS_FP")
                    failed_check = "OPERATIONAL_HEALTH_SEMANTICS"
                    failure_severity = "HIGH"
                    failure_classification = "CONTRADICTION"
                    action_directive = (
                        "Operational monitoring rule cannot be dismissed as FALSE_POSITIVE merely for lacking malicious intent; "
                        "requires verified maintenance/exception or explicit telemetry recovery."
                    )
            elif canon_arch == "CONFIGURATION_MONITORING":
                if not (has_org_auth or has_telemetry_auth):
                    final_verdict = "REQUIRES_ATTENTION"
                    validation_status = "INSUFFICIENT_EVIDENCE"
                    reason_codes.append("AUTHORIZATION_UNVERIFIED")
                    failed_check = "CHANGE_AUTHORIZATION_CHECK"
                    failure_severity = "MEDIUM"
                    failure_classification = "EVIDENCE_INSUFFICIENCY"
                    action_directive = "Configuration change FALSE_POSITIVE requires verified change approval or maintenance context."
            elif profile.requires_affirmative_auth_for_fp:
                # For Firewall/Scan/DNS/Data/IPS/Auth/TI: accept FP when either:
                # (a) verified organizational context authorizes the activity, OR
                # (b) authoritative telemetry ticket/exception exists, OR
                # (c) telemetry proves a non-attack condition consistent with rule FP criteria (e.g., benign web category/bogon noise/non-matching)
                #     WITHOUT relying solely on "blocked by firewall" or "internal RFC1918 IP".
                if not (has_org_auth or has_telemetry_auth):
                    # Check if rationale relies on prohibited blanket assumptions
                    bad_blanket = any(
                        p in reason_l
                        for p in (
                            "internal ip so it is benign",
                            "rfc1918 so it is benign",
                            "blocked so it is a false positive",
                            "denied so it is not malicious",
                            "no endpoint execution",
                            "no file activity",
                        )
                    )
                    if bad_blanket:
                        final_verdict = "REQUIRES_ATTENTION"
                        validation_status = "REJECTED"
                        reason_codes.append("UNSAFE_FP_ASSUMPTION")
                        failed_check = "PROHIBITED_FP_ASSUMPTION"
                        failure_severity = "HIGH"
                        failure_classification = "CONTRADICTION"
                        action_directive = "Rejected FALSE_POSITIVE based on prohibited assumption (internal IP / blocked action / absent endpoint logs)."
                    else:
                        # Allow FP if grounded claims show specific benign web/policy/telemetry justification
                        # (e.g. benign web category/CDN, zero bytes, authorized service domain)
                        has_specific_benign_evidence = any(
                            str(c.field or "").lower() in ("webcategory", "http.url", "network.destination_domain", "network.bytes_out", "security.message", "network.source_ip", "network.destination_ip")
                            for c in grounded_claims
                        )
                        if not has_specific_benign_evidence:
                            final_verdict = "REQUIRES_ATTENTION"
                            validation_status = "INSUFFICIENT_EVIDENCE"
                            reason_codes.append("FP_CRITERIA_UNSATISFIED")
                            failed_check = "FP_EVIDENCE_JUSTIFICATION"
                            failure_severity = "MEDIUM"
                            failure_classification = "EVIDENCE_INSUFFICIENCY"
                            action_directive = "FALSE_POSITIVE lacks verified organizational authorization or grounded benign evidence."

        if final_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE") and not reason_codes:
            is_decisive = True
            reason_codes.append("EVIDENCE_VALIDATED")
        elif clean_prop == "REQUIRES_ATTENTION":
            final_verdict = "REQUIRES_ATTENTION"
            is_decisive = False
            if not reason_codes:
                reason_codes.append("EVIDENCE_VALIDATED")

        sig_payload = f"{incident_id}:{dynamic_contract.contract_id}:{clean_prop}:{final_verdict}:{cls.VALIDATOR_VERSION}"
        replay_sig = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:16]

        return VerdictValidationResult(
            incident_id=incident_id,
            proposed_verdict=clean_prop,
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
            validation_audit_trail=list(getattr(claim_grounding, "validation_audit_trail", []) or []),
            detected_contradictions=contradictions,
            field_validation_status=getattr(preflight, "field_validation_status", {}),
            analyst_action_directive=action_directive,
            contract_id=dynamic_contract.contract_id,
            contract_version=dynamic_contract.contract_version,
            validator_version=cls.VALIDATOR_VERSION,
            raw_model_confidence=raw_model_confidence,
            confidence_scale=norm_conf.raw_scale,
            confidence_interpretation=norm_conf.interpretation,
            normalized_confidence_percent=norm_conf.normalized_percent if norm_conf.is_valid else None,
            reasoning_integrity_status=reasoning_res.validation_status if not contradictions else "REASONING_CONTRADICTION",
            reasoning_contradictions=contradictions,
            semantic_review_notes=reasoning_res.semantic_review_notes,
            validated_confidence_display=norm_conf.normalized_percent if is_decisive else 0.0,
            replay_signature=replay_sig,
            validator_module=profile.module_name,
            failed_check=failed_check,
            failure_severity=failure_severity,
            failure_classification=failure_classification,
            evidence_reference=evidence_ref,
            semantic_evaluation=sem_eval.model_dump(mode="json"),
        )
