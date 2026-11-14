"""
Phase A Regression Tests: Final Offline Safety Verification (Empirical Verdict Readiness).
Ensures:
1. Signed binaries and approved paths alone CANNOT establish benign authorization.
2. Maintenance start/end timestamps are strictly validated against incident time.
3. Absent authorization attributes are treated as UNKNOWN (not approved).
4. Authoritative evidence provenance is verified; untrusted SIEM sources cannot masquerade as ITSM approvals.
5. No unverified FP can trigger automatic incident closure or suppression.
"""

import pytest
from app.schemas.canonical_evidence import (
    CanonicalEvidenceRecord,
    EvidenceNormalizationResult,
)
from app.schemas.evidence_contract import (
    RuleEvidenceContract,
    EvidenceFieldRequirement,
)
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.verdict_guardrails_engine import (
    VerdictGuardrailsEngine,
    VerdictGuardrailResult,
)
from app.schemas.verdict_intelligence import (
    UserVisibleVerdict,
    EvidenceStatus,
    ClaimType,
    EvidenceSufficiencyAssessmentResult,
    ClaimVerificationResult,
)
from app.services.policy_governance import PolicyRuntimeCertification
from app.services.verdict_pipeline import _governance_fields


def _build_norm(incident_id: str, records):
    field_map = {}
    type_map = {}
    for r in records:
        field_map.setdefault(r.source_field, []).append(r)
        type_map.setdefault(r.evidence_type, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=incident_id,
        records=records,
        evidence_by_field=field_map,
        evidence_by_type=type_map,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        normalization_version="2.0.0",
    )


def _create_record(incident_id: str, field: str, value: str, ev_type: str = "GENERIC_TELEMETRY", source_sys: str = "EDR_AGENT"):
    return CanonicalEvidenceRecord(
        evidence_id=f"EV-{field}-{value}",
        incident_id=incident_id,
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        canonical_type="STRING",
        source_system=source_sys,
        confidence=1.0,
        integrity_digest=f"sha256-{field}-{value}",
    )


# -----------------------------------------------------------------------------
# Test 1: Signed Binaries / System32 Paths Alone CANNOT Establish Authorization
# -----------------------------------------------------------------------------
def test_signed_binary_in_system32_alone_cannot_establish_fp_authorization():
    """
    Requirement 2: Signed binaries and approved paths alone CANNOT establish benign authorization.
    Even if certutil or powershell is signed and in System32, FP must be rejected if no valid ticket/maintenance exists.
    """
    contract = RuleEvidenceContract(
        contract_id="EC-EM-01",
        rule_id="RULE-EM-01",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="code_signature.status", evidence_type="SECURITY_EVENT", critical=False),
            EvidenceFieldRequirement(field="process.executable_path", evidence_type="PROCESS_EXECUTION", critical=False),
        ],
    )

    records = [
        _create_record("INC-EM-01", "process.name", "certutil.exe", "PROCESS_EXECUTION"),
        _create_record("INC-EM-01", "code_signature.status", "VALID", "SECURITY_EVENT"),
        _create_record("INC-EM-01", "process.executable_path", "C:\\Windows\\System32\\certutil.exe", "PROCESS_EXECUTION"),
    ]
    norm = _build_norm("INC-EM-01", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EM-01", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 92.0,
        "reason": "Process is legitimately signed by Microsoft and located in System32, benign activity.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "code_signature.status",
                "asserted_value": "VALID",
                "evidence_ids": [records[1].evidence_id],
            },
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.executable_path",
                "asserted_value": "C:\\Windows\\System32\\certutil.exe",
                "evidence_ids": [records[2].evidence_id],
            },
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EM-01", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EM-01",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    # Must be forced to REQUIRES_ATTENTION because signed binary & system path alone do NOT prove authorization
    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "INSUFFICIENT_EVIDENCE"
    assert "FP_CRITERIA_UNSATISFIED" in res.validation_reason_codes


# -----------------------------------------------------------------------------
# Test 2: Maintenance Start / End Window Matching Against Incident Timestamp
# -----------------------------------------------------------------------------
def test_maintenance_window_expired_by_incident_timestamp():
    """
    Requirement 3: Incident timestamp occurring after scheduled maintenance end
    must reject FP and trigger MAINTENANCE_WINDOW_EXPIRED.
    """
    contract = RuleEvidenceContract(
        contract_id="EC-EM-02",
        rule_id="RULE-EM-02",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.maintenance_window", evidence_type="SECURITY_EVENT", critical=True),
        ],
    )

    # Incident occurred at 2026-11-14 10:00:00 (timestamp 1794650400)
    # Maintenance window ended at 2026-11-14 08:00:00 (timestamp 1794643200)
    records = [
        _create_record("INC-EM-02", "authorization.maintenance_window", "WIN-MW-900", "SECURITY_EVENT"),
        _create_record("INC-EM-02", "incident.time", "1794650400", "EVENT_TIMESTAMP"),
        _create_record("INC-EM-02", "maintenance.start_time", "1794639600", "SECURITY_EVENT"),
        _create_record("INC-EM-02", "maintenance.end_time", "1794643200", "SECURITY_EVENT"),
    ]
    norm = _build_norm("INC-EM-02", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EM-02", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Execution occurred under maintenance window WIN-MW-900.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.maintenance_window",
                "asserted_value": "WIN-MW-900",
                "evidence_ids": [records[0].evidence_id],
            }
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EM-02", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EM-02",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "MAINTENANCE_WINDOW_EXPIRED" in res.validation_reason_codes


def test_maintenance_window_before_start_time_rejected():
    """
    Requirement 3: Incident timestamp occurring before maintenance start time must also reject FP.
    """
    contract = RuleEvidenceContract(
        contract_id="EC-EM-02B",
        rule_id="RULE-EM-02B",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.maintenance_window", evidence_type="SECURITY_EVENT", critical=True),
        ],
    )

    # Incident occurred at 06:00:00 (1794636000), start is 07:00:00 (1794639600)
    records = [
        _create_record("INC-EM-02B", "authorization.maintenance_window", "WIN-MW-901", "SECURITY_EVENT"),
        _create_record("INC-EM-02B", "event.time", "1794636000", "EVENT_TIMESTAMP"),
        _create_record("INC-EM-02B", "maintenance.start_time", "1794639600", "SECURITY_EVENT"),
        _create_record("INC-EM-02B", "maintenance.end_time", "1794643200", "SECURITY_EVENT"),
    ]
    norm = _build_norm("INC-EM-02B", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EM-02B", contract, norm)
    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "maintenance window WIN-MW-901",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.maintenance_window",
                "asserted_value": "WIN-MW-901",
                "evidence_ids": [records[0].evidence_id],
            }
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EM-02B", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EM-02B",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason="maintenance window WIN-MW-901",
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert "MAINTENANCE_WINDOW_EXPIRED" in res.validation_reason_codes


# -----------------------------------------------------------------------------
# Test 3: Absent Authorization Status Treated as UNKNOWN (Not Approved)
# -----------------------------------------------------------------------------
def test_absent_authorization_status_treated_as_unknown():
    """
    Requirement 4: Treat absent authorization attributes as unknown, not approved.
    If ticket ID is present but authorization.status is absent, reject FP with AUTHORIZATION_STATE_UNAPPROVED.
    """
    contract = RuleEvidenceContract(
        contract_id="EC-EM-03",
        rule_id="RULE-EM-03",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
        ],
    )

    # Has ticket ID CHG-5512 but NO authorization.status record
    records = [
        _create_record("INC-EM-03", "authorization.ticket_id", "CHG-5512", "SECURITY_EVENT", "SERVICENOW_API"),
        _create_record("INC-EM-03", "host.name", "SRV-APP-01", "HOST_CONTEXT"),
    ]
    norm = _build_norm("INC-EM-03", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EM-03", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 88.0,
        "reason": "Change ticket CHG-5512 covers the server update.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-5512",
                "evidence_ids": [records[0].evidence_id],
            }
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EM-03", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EM-03",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=88.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "AUTHORIZATION_STATE_UNAPPROVED" in res.validation_reason_codes


# -----------------------------------------------------------------------------
# Test 4: Untrusted SIEM Provenance Masquerading as ITSM Approval
# -----------------------------------------------------------------------------
def test_untrusted_siem_provenance_rejected():
    """
    Requirement 5: Verify authoritative evidence provenance and prevent untrusted SIEM fields
    (e.g. rawsyslog, userpayload, commandline) from masquerading as validated ITSM approvals.
    """
    contract = RuleEvidenceContract(
        contract_id="EC-EM-04",
        rule_id="RULE-EM-04",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
        ],
    )

    # Ticket originates from rawsyslog source system instead of authoritative ITSM API
    records = [
        _create_record("INC-EM-04", "authorization.ticket_id", "CHG-7788", "SECURITY_EVENT", source_sys="rawsyslog"),
        _create_record("INC-EM-04", "authorization.status", "APPROVED", "SECURITY_EVENT", source_sys="rawsyslog"),
    ]
    norm = _build_norm("INC-EM-04", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EM-04", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Change ticket CHG-7788 is approved.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-7788",
                "evidence_ids": [records[0].evidence_id],
            }
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EM-04", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EM-04",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "UNTRUSTED_AUTHORIZATION_PROVENANCE" in res.validation_reason_codes


# -----------------------------------------------------------------------------
# Test 5: Autonomous Closure Hard-Gated on Decisive Validated False Positive
# -----------------------------------------------------------------------------
def test_governance_fields_blocks_closure_for_unverified_verdicts():
    """
    Requirement 6: Ensure no unverified FP triggers automatic incident closure or suppression.
    Even with autonomous_operation_eligible=True:
    - REQUIRES_ATTENTION verdict -> auto_incident_closure_allowed MUST be False.
    - Non-decisive FP -> auto_incident_closure_allowed MUST be False.
    - Decisive TP -> auto_incident_closure_allowed MUST be False (TP requires investigation, not closure).
    - ONLY validated decisive FALSE_POSITIVE -> auto_incident_closure_allowed is True.
    """
    cert = PolicyRuntimeCertification(
        rule_id="RULE-EM-01",
        prompt_version_id="PV-01",
        prompt_version_status="APPROVED",
        policy_governance_mode="AUTONOMOUS_OPERATION_ELIGIBLE",
        structural_approval_eligible=True,
        empirical_validation_eligible=True,
        autonomous_operation_eligible=True,
        empirical_validation_status="CERTIFIED",
        active_policy_digest="sha256-test-cert",
    )

    # 1. Abstained / unverified FP forced to REQUIRES_ATTENTION
    meta_abstained = _governance_fields(cert, final_verdict="REQUIRES_ATTENTION", is_decisive=False)
    assert meta_abstained["auto_incident_closure_allowed"] is False
    assert meta_abstained["requires_human_review"] is True

    # 2. Non-decisive FP
    meta_non_decisive_fp = _governance_fields(cert, final_verdict="FALSE_POSITIVE", is_decisive=False)
    assert meta_non_decisive_fp["auto_incident_closure_allowed"] is False

    # 3. Decisive TP
    meta_decisive_tp = _governance_fields(cert, final_verdict="TRUE_POSITIVE", is_decisive=True)
    assert meta_decisive_tp["auto_incident_closure_allowed"] is False

    # 4. Decisive validated FP -> ONLY here is closure allowed
    meta_decisive_fp = _governance_fields(cert, final_verdict="FALSE_POSITIVE", is_decisive=True)
    assert meta_decisive_fp["auto_incident_closure_allowed"] is True
    assert meta_decisive_fp["requires_human_review"] is False
