"""
test_evidence_preflight.py
Phase 2 Test Suite: Pre-Inference Evidence Validation (P2-REQ-03)

Tests:
1. Complete evidence satisfying all contract requirements
2. Partial evidence missing non-critical field allows inference
3. Critical evidence missing blocks inference and forces immediate abstention
4. Unverified contract blocks inference and forces immediate human deferral
5. Contradictory telemetry (loopback C2) flagged in preflight
6. Semantic alias recognition for evidence fields
"""

import pytest
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult


def create_record(incident_id: str, field: str, value: str, ev_type: str = "GENERIC") -> CanonicalEvidenceRecord:
    digest = CanonicalEvidenceRecord.generate_digest(field, value)
    rec_id = CanonicalEvidenceRecord.generate_id(incident_id, "EVT1", field)
    return CanonicalEvidenceRecord(
        evidence_id=rec_id,
        incident_id=incident_id,
        source_system="FortiSIEM",
        source_event_id="EVT1",
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        availability="AVAILABLE",
        integrity_digest=digest,
    )


def build_norm_result(incident_id: str, records: list) -> EvidenceNormalizationResult:
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


def test_preflight_complete_evidence():
    """All contract evidence present -> COMPLETE status, can proceed."""
    contract = RuleEvidenceContract(
        contract_id="EC-01",
        rule_id="RULE-01",
        version_number=1,
        status="APPROVED",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    records = [
        create_record("INC-01", "process.name", "powershell.exe", "PROCESS_EXECUTION"),
        create_record("INC-01", "process.command_line", "powershell.exe -enc AAAA", "PROCESS_EXECUTION"),
    ]
    norm = build_norm_result("INC-01", records)

    res = EvidencePreflightValidator.validate_preflight("INC-01", contract, norm)
    assert res.preflight_status == "COMPLETE"
    assert res.can_proceed_to_inference is True
    assert res.must_abstain_immediately is False
    assert res.evidence_completeness == 1.0
    assert len(res.missing_evidence_fields) == 0


def test_preflight_partial_evidence():
    """Non-critical field missing -> PARTIAL status, can proceed."""
    contract = RuleEvidenceContract(
        contract_id="EC-02",
        rule_id="RULE-02",
        version_number=1,
        status="APPROVED",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER_CONTEXT", critical=False),
        ]
    )

    records = [
        create_record("INC-02", "process.name", "cmd.exe", "PROCESS_EXECUTION"),
        create_record("INC-02", "process.command_line", "cmd.exe /c calc", "PROCESS_EXECUTION"),
    ]
    norm = build_norm_result("INC-02", records)

    res = EvidencePreflightValidator.validate_preflight("INC-02", contract, norm)
    assert res.preflight_status == "PARTIAL"
    assert res.can_proceed_to_inference is True
    assert res.must_abstain_immediately is False
    assert res.evidence_completeness < 1.0
    assert "user.name" in res.missing_evidence_fields
    assert len(res.critical_missing_fields) == 0


def test_preflight_critical_missing_blocks_inference():
    """Critical field missing -> INSUFFICIENT status, blocks inference, must abstain immediately."""
    contract = RuleEvidenceContract(
        contract_id="EC-03",
        rule_id="RULE-03",
        version_number=1,
        status="APPROVED",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
        ]
    )

    # Missing critical command_line
    records = [
        create_record("INC-03", "process.name", "svchost.exe", "PROCESS_EXECUTION"),
    ]
    norm = build_norm_result("INC-03", records)

    res = EvidencePreflightValidator.validate_preflight("INC-03", contract, norm)
    assert res.preflight_status == "INSUFFICIENT"
    assert res.can_proceed_to_inference is False
    assert res.must_abstain_immediately is True
    assert "process.command_line" in res.critical_missing_fields
    assert res.safe_next_action == "DEFER_TO_HUMAN_ANALYST"


def test_preflight_unverified_contract_blocks():
    """Contract not in APPROVED status -> UNVERIFIABLE, blocks inference immediately."""
    contract = RuleEvidenceContract(
        contract_id="EC-04",
        rule_id="RULE-04",
        version_number=1,
        status="UNVERIFIED",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
        ]
    )

    records = [create_record("INC-04", "process.name", "cmd.exe")]
    norm = build_norm_result("INC-04", records)

    res = EvidencePreflightValidator.validate_preflight("INC-04", contract, norm, allow_simulation=False)
    assert res.preflight_status == "UNVERIFIABLE"
    assert res.can_proceed_to_inference is False
    assert res.must_abstain_immediately is True


def test_preflight_contradictory_loopback():
    """Source and destination both loopback 127.0.0.1 -> CONTRADICTORY flagged."""
    contract = RuleEvidenceContract(
        contract_id="EC-05",
        rule_id="RULE-05",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=False),
            EvidenceFieldRequirement(field="network.destination_ip", evidence_type="NETWORK_CONNECTION", critical=False),
        ]
    )

    records = [
        create_record("INC-05", "network.source_ip", "127.0.0.1", "NETWORK_CONNECTION"),
        create_record("INC-05", "network.destination_ip", "127.0.0.1", "NETWORK_CONNECTION"),
    ]
    norm = build_norm_result("INC-05", records)

    res = EvidencePreflightValidator.validate_preflight("INC-05", contract, norm)
    assert res.preflight_status == "CONTRADICTORY"
    assert len(res.detected_contradictions) > 0


def test_preflight_semantic_field_alias():
    """Semantic aliases satisfy requirements (e.g. process.file_path satisfies process.name)."""
    contract = RuleEvidenceContract(
        contract_id="EC-06",
        rule_id="RULE-06",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    records = [
        create_record("INC-06", "process.file_path", "C:\\Windows\\System32\\calc.exe", "PROCESS_EXECUTION"),
    ]
    norm = build_norm_result("INC-06", records)

    res = EvidencePreflightValidator.validate_preflight("INC-06", contract, norm)
    assert res.preflight_status == "COMPLETE"
    assert res.can_proceed_to_inference is True

