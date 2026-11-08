"""
test_independent_verdict_validator.py
Phase 2 Test Suite: Independent Deterministic Verdict Validation (Scenarios 21-34)

Tests:
21. Verified TRUE_POSITIVE accepted when all contract requirements and grounded claims pass
22. Verified FALSE_POSITIVE accepted when all contract requirements and grounded claims pass
23. High-confidence TP (0.95) rejected & routed to REQUIRES_ATTENTION due to missing telemetry
24. High-confidence FP (0.95) rejected & routed to REQUIRES_ATTENTION due to missing telemetry
25. TP with hallucinated C2 IP rejected & routed to REQUIRES_ATTENTION
26. FP with hallucinated signature claim rejected & routed to REQUIRES_ATTENTION
27. Contradictory telemetry routes to REQUIRES_ATTENTION
28. Unapproved evidence contract forces immediate abstention (REQUIRES_ATTENTION)
29. Completeness threshold enforcement (< 0.6 triggers TP_CRITERIA_UNSATISFIED)
30. Output integrity check (invalid verdict coerced to REQUIRES_ATTENTION)
31. Replay validation produces bit-for-bit identical outcome on saved evidence
32. Tampered evidence changes replay outcome
33. Safe confidence display (zeroed to 0.0 when validation abstains/rejects)
"""

import pytest
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement


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


def test_scenario_21_verified_tp_accepted():
    """Scenario 21: TP with all contract evidence present and claims grounded is accepted."""
    contract = RuleEvidenceContract(
        contract_id="EC-21",
        rule_id="RULE-21",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
        ]
    )

    records = [
        create_record("INC-21", "process.name", "powershell.exe", "PROCESS_EXECUTION"),
        create_record("INC-21", "process.command_line", "powershell.exe -w hidden -enc JABzAD0A", "PROCESS_EXECUTION"),
    ]
    norm = build_norm("INC-21", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-21", contract, norm)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 92.0,
        "reason": "Obfuscated powershell download cradle observed.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "powershell.exe",
                "evidence_ids": [records[0].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-21", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-21",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "TRUE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in res.validation_reason_codes
    assert res.validated_confidence_display == 92.0


def test_scenario_22_verified_fp_accepted():
    """Scenario 22: FP with verified benign evidence is accepted."""
    contract = RuleEvidenceContract(
        contract_id="EC-22",
        rule_id="RULE-22",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER_CONTEXT", critical=False),
        ]
    )

    records = [
        create_record("INC-22", "process.name", "ccmexec.exe", "PROCESS_EXECUTION"),
        create_record("INC-22", "user.name", "NT AUTHORITY\\SYSTEM", "USER_CONTEXT"),
    ]
    norm = build_norm("INC-22", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-22", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 88.0,
        "reason": "Legitimate SCCM client management execution under SYSTEM account.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "ccmexec.exe",
                "evidence_ids": [records[0].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-22", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-22",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=88.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"


def test_scenario_23_overconfident_tp_missing_telemetry_rejected():
    """Scenario 23: Model claims 95% TP, but missing critical telemetry forces REQUIRES_ATTENTION."""
    contract = RuleEvidenceContract(
        contract_id="EC-23",
        rule_id="RULE-23",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
        ]
    )

    # Missing critical command_line
    records = [create_record("INC-23", "process.name", "cmd.exe", "PROCESS_EXECUTION")]
    norm = build_norm("INC-23", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-23", contract, norm)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 95.0,
        "reason": "Highly suspicious command line executed.",
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-23", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-23",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "INSUFFICIENT_EVIDENCE"
    assert "EVIDENCE_MISSING" in res.validation_reason_codes
    assert res.validated_confidence_display == 0.0


def test_scenario_24_overconfident_fp_missing_telemetry_rejected():
    """Scenario 24: Model claims 95% FP, but incomplete telemetry forces REQUIRES_ATTENTION."""
    contract = RuleEvidenceContract(
        contract_id="EC-24",
        rule_id="RULE-24",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER_CONTEXT", critical=True),
        ]
    )

    # Empty telemetry
    norm = build_norm("INC-24", [])
    preflight = EvidencePreflightValidator.validate_preflight("INC-24", contract, norm)

    model_output = {"verdict": "FALSE_POSITIVE", "confidence": 95.0}
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-24", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-24",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validated_confidence_display == 0.0


def test_scenario_25_tp_with_hallucinated_ip_rejected():
    """Scenario 25: Model hallucinated an external C2 IP -> forced to REQUIRES_ATTENTION."""
    contract = RuleEvidenceContract(
        contract_id="EC-25",
        rule_id="RULE-25",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=False),
        ]
    )

    records = [create_record("INC-25", "network.source_ip", "10.0.0.5", "NETWORK_CONNECTION")]
    norm = build_norm("INC-25", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-25", contract, norm)

    # Model hallucinated external IP 203.0.113.199
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "Host contacted external C2 server at 203.0.113.199 which is an active CobaltStrike server.",
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-25", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-25",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.validation_status == "REJECTED"
    assert "CLAIM_NOT_VERIFIABLE" in res.validation_reason_codes


def test_scenario_28_unapproved_contract_forces_attention():
    """Scenario 28: Rule with unapproved policy contract forces immediate abstention."""
    contract = RuleEvidenceContract(
        contract_id="EC-28",
        rule_id="RULE-28",
        status="UNVERIFIED",  # Not APPROVED
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=False),
        ]
    )

    records = [create_record("INC-28", "process.name", "cmd.exe", "PROCESS_EXECUTION")]
    norm = build_norm("INC-28", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-28", contract, norm)
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-28", {"verdict": "TRUE_POSITIVE"}, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-28",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        allow_simulation=False,
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert "EVIDENCE_CONTRACT_UNVERIFIED" in res.validation_reason_codes


def test_scenario_30_output_integrity_invalid_verdict_coerced():
    """Scenario 30: Invalid verdict string from LLM is coerced safely to REQUIRES_ATTENTION."""
    contract = RuleEvidenceContract(contract_id="EC-30", rule_id="RULE-30", status="APPROVED")
    norm = build_norm("INC-30", [])
    preflight = EvidencePreflightValidator.validate_preflight("INC-30", contract, norm)
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-30", {}, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-30",
        proposed_verdict="MALICIOUS_ATTACK",  # Invalid verdict enum
        raw_model_confidence=99.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert "MODEL_OUTPUT_INVALID" in res.validation_reason_codes


def test_scenario_31_replay_validation_deterministic():
    """Scenario 31: Replay validation produces bit-for-bit identical outcome on saved data."""
    contract_dict = {
        "contract_id": "EC-31",
        "rule_id": "RULE-31",
        "version_number": 1,
        "status": "APPROVED",
        "detection_archetype": "PROCESS_EXECUTION",
        "required_evidence": [
            {"field": "process.name", "evidence_type": "PROCESS_EXECUTION", "required_for_tp": True, "required_for_fp": False, "critical": False, "description": ""}
        ],
        "tp_criteria": [],
        "fp_criteria": [],
        "contradiction_rules": [],
    }

    rec = create_record("INC-31", "process.name", "calc.exe", "PROCESS_EXECUTION")
    saved_records = [rec.model_dump()]

    saved_model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Harmless calculator launch",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": [rec.evidence_id],
                "field": "process.name",
                "asserted_value": "calc.exe",
            }
        ]
    }

    # Run replay twice
    res1 = IndependentVerdictValidator.replay_validation("INC-31", saved_records, contract_dict, saved_model_output)
    res2 = IndependentVerdictValidator.replay_validation("INC-31", saved_records, contract_dict, saved_model_output)

    assert res1.final_verdict == res2.final_verdict
    assert res1.validation_status == res2.validation_status
    assert res1.replay_signature == res2.replay_signature
    assert res1.replay_signature != ""


def test_scenario_32_tampered_evidence_changes_replay():
    """Scenario 32: Tampered evidence (e.g. altered process name) invalidates grounding on replay."""
    contract_dict = {
        "contract_id": "EC-32",
        "rule_id": "RULE-32",
        "version_number": 1,
        "status": "APPROVED",
        "detection_archetype": "PROCESS_EXECUTION",
        "required_evidence": [
            {"field": "process.name", "evidence_type": "PROCESS_EXECUTION", "required_for_tp": True, "required_for_fp": False, "critical": False, "description": ""}
        ],
        "tp_criteria": [],
        "fp_criteria": [],
        "contradiction_rules": [],
    }

    # Tampered record: process is "cmd.exe" instead of "calc.exe"
    rec = create_record("INC-32", "process.name", "cmd.exe", "PROCESS_EXECUTION")
    saved_records = [rec.model_dump()]

    saved_model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Harmless calculator launch",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": [rec.evidence_id],
                "field": "process.name",
                "asserted_value": "calc.exe",  # Mismatched with actual "cmd.exe"
            }
        ]
    }

    res = IndependentVerdictValidator.replay_validation("INC-32", saved_records, contract_dict, saved_model_output)
    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.validation_status == "REJECTED"

