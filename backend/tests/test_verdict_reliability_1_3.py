"""
test_verdict_reliability_1_3.py
Regression Test Suite for Verdictum AI — LLM Verdict Reliability 1.3:
Preventing Unjustified False Positives from Process-Name Spoofing, Attacker-Controlled Authorization,
and Unverified Evidence Provenance.

Covers:
1. Rejection of process-name spoofing in suspicious/user-writable directories (SPOOFED_ADMIN_BINARY).
2. Rejection of allowlisted process name without rule-appropriate trusted binary evidence (UNVERIFIED_BINARY_PROVENANCE).
3. Rejection of forged ticket in command line without authoritative ITSM record (UNVERIFIED_COMMAND_LINE_TICKET).
4. Rejection of invalid/revoked digital signature telemetry (INVALID_DIGITAL_SIGNATURE).
5. Rejection of signature metadata only without valid verification status (UNVERIFIED_SIGNATURE_CLAIM).
6. Rejection of out-of-scope maintenance ticket with host mismatch (AUTHORIZATION_SCOPE_MISMATCH).
7. Rejection of unapproved authorization state (PENDING / REJECTED) (AUTHORIZATION_STATE_UNAPPROVED).
8. Rejection of expired/inactive maintenance window (MAINTENANCE_WINDOW_EXPIRED).
9. Acceptance of legitimate administrative binary with trusted system path and signature (EVIDENCE_VALIDATED).
10. Acceptance of legitimate in-scope, approved authorization ticket (EVIDENCE_VALIDATED).
11. Consistent REQUIRES_ATTENTION verdict naming across validators and guardrails.
"""

import pytest
from app.schemas.evidence_claim import ModelSupportingClaim
from app.schemas.verdict_intelligence import ClaimType, UserVisibleVerdict
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.verdict_guardrails_engine import VerdictGuardrailsEngine
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor


def create_record(incident_id: str, field: str, value: str, ev_type: str = "GENERIC", source_system: str = "FortiSIEM") -> CanonicalEvidenceRecord:
    digest = CanonicalEvidenceRecord.generate_digest(field, value)
    rec_id = CanonicalEvidenceRecord.generate_id(incident_id, "EVT-01", field)
    return CanonicalEvidenceRecord(
        evidence_id=rec_id,
        incident_id=incident_id,
        source_system=source_system,
        source_event_id="EVT-01",
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        availability="AVAILABLE",
        integrity_digest=digest,
    )


def build_norm(incident_id: str, records: list) -> EvidenceNormalizationResult:
    by_field = {}
    by_type = {}
    for r in records:
        by_field.setdefault(r.source_field, []).append(r)
        by_type.setdefault(r.evidence_type, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=incident_id,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
    )


# ---------------------------------------------------------------------------
# Test 1: Process-Name Spoofing in Suspicious Directory (SPOOFED_ADMIN_BINARY)
# ---------------------------------------------------------------------------
def test_reject_process_name_spoofing_suspicious_path():
    contract = RuleEvidenceContract(
        contract_id="EC-13-SPOOF-01",
        rule_id="RULE-13-SPOOF-01",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.executable_path", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    records = [
        create_record("INC-13-01", "process.name", "ccmexec.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-01", "process.executable_path", "C:\\Users\\Public\\ccmexec.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-01", "process.command_line", "C:\\Users\\Public\\ccmexec.exe -run", "PROCESS_EXECUTION"),
    ]
    norm = build_norm("INC-13-01", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-01", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Legitimate approved SCCM ccmexec.exe enterprise management software.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "ccmexec.exe",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.executable_path",
                "asserted_value": "C:\\Users\\Public\\ccmexec.exe",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-01", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-01",
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
    assert "SPOOFED_ADMIN_BINARY" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 2: Allowlisted Process Name Without Trusted Binary Evidence (UNVERIFIED_BINARY_PROVENANCE)
# ---------------------------------------------------------------------------
def test_reject_process_name_allowlist_without_trusted_binary_evidence():
    contract = RuleEvidenceContract(
        contract_id="EC-13-UNVER-02",
        rule_id="RULE-13-UNVER-02",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    # Only process name exists; no path, no signature, no hash, no management agent
    records = [
        create_record("INC-13-02", "process.name", "tanclient.exe", "PROCESS_EXECUTION"),
    ]
    norm = build_norm("INC-13-02", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-02", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 88.0,
        "reason": "Authorized Tanium client management agent.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "tanclient.exe",
                "evidence_ids": [records[0].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-02", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-02",
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
    assert "UNVERIFIED_BINARY_PROVENANCE" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 3: Forged Ticket in Command Line Without Authoritative ITSM Record (UNVERIFIED_COMMAND_LINE_TICKET)
# ---------------------------------------------------------------------------
def test_reject_forged_ticket_in_command_line_without_authoritative_auth():
    contract = RuleEvidenceContract(
        contract_id="EC-13-FORGE-03",
        rule_id="RULE-13-FORGE-03",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    # Command line contains self-asserted --ticket CHG-7712, but no independent authorization.ticket_id record exists
    cmd = "powershell.exe -ExecutionPolicy Bypass -File cleanup.ps1 --ticket CHG-7712"
    records = [
        create_record("INC-13-03", "process.command_line", cmd, "PROCESS_EXECUTION"),
    ]
    norm = build_norm("INC-13-03", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-03", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 91.0,
        "reason": "Authorized cleanup script executed under change ticket CHG-7712.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": cmd,
                "evidence_ids": [records[0].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-03", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-03",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=91.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "UNVERIFIED_COMMAND_LINE_TICKET" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 4: Invalid / Revoked Digital Signature (INVALID_DIGITAL_SIGNATURE)
# ---------------------------------------------------------------------------
def test_reject_invalid_digital_signature():
    contract = RuleEvidenceContract(
        contract_id="EC-13-SIG-04",
        rule_id="RULE-13-SIG-04",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="code_signature.status", evidence_type="FILE_INTEGRITY", critical=True),
        ]
    )

    records = [
        create_record("INC-13-04", "process.name", "svchost_updater.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-04", "code_signature.status", "REVOKED", "FILE_INTEGRITY"),
    ]
    norm = build_norm("INC-13-04", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-04", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Authorized Windows update process signed by corporate PKI.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "svchost_updater.exe",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "FILE_INTEGRITY",
                "field": "code_signature.status",
                "asserted_value": "REVOKED",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-04", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-04",
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
    assert "INVALID_DIGITAL_SIGNATURE" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 5: Signature Metadata Only Without Valid Status (UNVERIFIED_SIGNATURE_CLAIM)
# ---------------------------------------------------------------------------
def test_reject_signature_metadata_only_without_verification_status():
    contract = RuleEvidenceContract(
        contract_id="EC-13-META-05",
        rule_id="RULE-13-META-05",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="certificate.issuer", evidence_type="FILE_INTEGRITY", critical=False),
        ]
    )

    # Has certificate issuer metadata, but lacks verified signature status
    records = [
        create_record("INC-13-05", "process.name", "updater.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-05", "certificate.issuer", "CN=Untrusted Root CA", "FILE_INTEGRITY"),
    ]
    norm = build_norm("INC-13-05", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-05", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 89.0,
        "reason": "Authorized software verified vendor signature by trusted certificate authority.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "updater.exe",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "FILE_INTEGRITY",
                "field": "certificate.issuer",
                "asserted_value": "CN=Untrusted Root CA",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-05", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-05",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=89.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "UNVERIFIED_SIGNATURE_CLAIM" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 6: Out-of-Scope Maintenance Ticket (AUTHORIZATION_SCOPE_MISMATCH)
# ---------------------------------------------------------------------------
def test_reject_out_of_scope_maintenance_ticket():
    contract = RuleEvidenceContract(
        contract_id="EC-13-SCOPE-06",
        rule_id="RULE-13-SCOPE-06",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="host.name", evidence_type="SYSTEM_EVENT", critical=True),
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
        ]
    )

    # Ticket target is host-db-01, but alert is on host-dc-01
    records = [
        create_record("INC-13-06", "host.name", "host-dc-01", "SYSTEM_EVENT"),
        create_record("INC-13-06", "authorization.ticket_id", "CHG-4040", "SECURITY_EVENT"),
        create_record("INC-13-06", "authorization.target_host", "host-db-01", "SECURITY_EVENT"),
        create_record("INC-13-06", "authorization.status", "APPROVED", "SECURITY_EVENT"),
    ]
    norm = build_norm("INC-13-06", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-06", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 92.0,
        "reason": "Authorized maintenance approved under change ticket CHG-4040.",
        "supporting_claims": [
            {
                "claim_type": "SYSTEM_EVENT",
                "field": "host.name",
                "asserted_value": "host-dc-01",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-4040",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-06", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-06",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "AUTHORIZATION_SCOPE_MISMATCH" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 7: Unapproved Authorization State (AUTHORIZATION_STATE_UNAPPROVED)
# ---------------------------------------------------------------------------
def test_reject_unapproved_authorization_state():
    contract = RuleEvidenceContract(
        contract_id="EC-13-STATE-07",
        rule_id="RULE-13-STATE-07",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
            EvidenceFieldRequirement(field="authorization.status", evidence_type="SECURITY_EVENT", critical=True),
        ]
    )

    # Ticket exists, but approval state is PENDING_APPROVAL
    records = [
        create_record("INC-13-07", "authorization.ticket_id", "CHG-5050", "SECURITY_EVENT"),
        create_record("INC-13-07", "authorization.status", "PENDING_APPROVAL", "SECURITY_EVENT"),
    ]
    norm = build_norm("INC-13-07", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-07", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Change request submitted under ticket CHG-5050.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-5050",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.status",
                "asserted_value": "PENDING_APPROVAL",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-07", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-07",
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
    assert "AUTHORIZATION_STATE_UNAPPROVED" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 8: Expired Maintenance Window (MAINTENANCE_WINDOW_EXPIRED)
# ---------------------------------------------------------------------------
def test_reject_expired_maintenance_window():
    contract = RuleEvidenceContract(
        contract_id="EC-13-EXP-08",
        rule_id="RULE-13-EXP-08",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
            EvidenceFieldRequirement(field="maintenance.active", evidence_type="SECURITY_EVENT", critical=True),
        ]
    )

    records = [
        create_record("INC-13-08", "authorization.ticket_id", "CHG-6060", "SECURITY_EVENT"),
        create_record("INC-13-08", "maintenance.active", "false", "SECURITY_EVENT"),
    ]
    norm = build_norm("INC-13-08", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-08", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Change activity under ticket CHG-6060 during maintenance window.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-6060",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "maintenance.active",
                "asserted_value": "false",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-08", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-08",
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
    assert "MAINTENANCE_WINDOW_EXPIRED" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 9: Valid Administrative Binary With Trusted System Path and Valid Signature (ACCEPTED)
# ---------------------------------------------------------------------------
def test_accept_legitimate_administrative_binary_with_trusted_evidence():
    contract = RuleEvidenceContract(
        contract_id="EC-13-VAL-09",
        rule_id="RULE-13-VAL-09",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.executable_path", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="code_signature.status", evidence_type="FILE_INTEGRITY", critical=False),
        ]
    )

    records = [
        create_record("INC-13-09", "process.name", "ccmexec.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-09", "process.executable_path", "C:\\Windows\\CCM\\CcmExec.exe", "PROCESS_EXECUTION"),
        create_record("INC-13-09", "code_signature.status", "VALID", "FILE_INTEGRITY"),
    ]
    norm = build_norm("INC-13-09", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-09", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 94.0,
        "reason": "Authorized SCCM client management execution from system path with valid digital signature.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "ccmexec.exe",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.executable_path",
                "asserted_value": "C:\\Windows\\CCM\\CcmExec.exe",
                "evidence_ids": [records[1].evidence_id],
            },
            {
                "claim_type": "FILE_INTEGRITY",
                "field": "code_signature.status",
                "asserted_value": "VALID",
                "evidence_ids": [records[2].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-09", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-09",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=94.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 10: Valid In-Scope, Approved Authorization Ticket (ACCEPTED)
# ---------------------------------------------------------------------------
def test_accept_legitimate_in_scope_and_approved_authorization():
    contract = RuleEvidenceContract(
        contract_id="EC-13-VAL-10",
        rule_id="RULE-13-VAL-10",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="host.name", evidence_type="SYSTEM_EVENT", critical=True),
            EvidenceFieldRequirement(field="authorization.ticket_id", evidence_type="SECURITY_EVENT", critical=True),
            EvidenceFieldRequirement(field="authorization.status", evidence_type="SECURITY_EVENT", critical=True),
        ]
    )

    records = [
        create_record("INC-13-10", "host.name", "host-app-01", "SYSTEM_EVENT"),
        create_record("INC-13-10", "authorization.ticket_id", "CHG-7070", "SECURITY_EVENT"),
        create_record("INC-13-10", "authorization.target_host", "host-app-01", "SECURITY_EVENT"),
        create_record("INC-13-10", "authorization.status", "APPROVED", "SECURITY_EVENT"),
    ]
    norm = build_norm("INC-13-10", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-10", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 95.0,
        "reason": "Authorized maintenance approved under change ticket CHG-7070 on target host host-app-01.",
        "supporting_claims": [
            {
                "claim_type": "SYSTEM_EVENT",
                "field": "host.name",
                "asserted_value": "host-app-01",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-7070",
                "evidence_ids": [records[1].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.status",
                "asserted_value": "APPROVED",
                "evidence_ids": [records[3].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-10", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-10",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 11: Consistent REQUIRES_ATTENTION Verdict Naming
# ---------------------------------------------------------------------------
def test_consistent_verdict_naming_across_validators_and_guardrails():
    # 1. IndependentVerdictValidator accepts REQUIRES_ANALYST_ATTENTION without MODEL_OUTPUT_INVALID
    contract = RuleEvidenceContract(
        contract_id="EC-13-NAME-11",
        rule_id="RULE-13-NAME-11",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="host.name", evidence_type="SYSTEM_EVENT", critical=True),
        ]
    )
    records = [create_record("INC-13-11", "host.name", "host-app-01", "SYSTEM_EVENT")]
    norm = build_norm("INC-13-11", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-13-11", contract, norm)
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-13-11", {"verdict": "REQUIRES_ANALYST_ATTENTION", "supporting_claims": []}, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-13-11",
        proposed_verdict="REQUIRES_ANALYST_ATTENTION",
        raw_model_confidence=60.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )
    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert "MODEL_OUTPUT_INVALID" not in res.validation_reason_codes

    # 2. UserVisibleVerdict accepts REQUIRES_ATTENTION alias
    assert UserVisibleVerdict("REQUIRES_ATTENTION") == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert UserVisibleVerdict.REQUIRES_ATTENTION == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
