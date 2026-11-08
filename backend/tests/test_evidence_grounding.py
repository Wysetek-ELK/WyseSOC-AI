"""
test_evidence_grounding.py
Phase 2 Test Suite: Structured LLM Evidence Claims & Grounding (Scenarios 11-20)

Tests:
11. Model cites existing evidence ID with matching value (GROUNDED)
12. Model cites nonexistent evidence ID (EVIDENCE_REFERENCE_NOT_FOUND)
13. Model cites evidence ID from another incident (rejected)
14. Model cites valid evidence ID with fabricated/mismatched value (EVIDENCE_VALUE_MISMATCH)
15. Model asserts process name not in telemetry (CLAIM_NOT_VERIFIABLE, hallucination)
16. Model asserts SHA-256 hash not in telemetry (CLAIM_NOT_VERIFIABLE, hallucination)
17. Model asserts IP not in telemetry (CLAIM_NOT_VERIFIABLE, hallucination)
18. Model asserts parent-child relationship not in telemetry (ungrounded)
19. Model output with empty claims list (graceful default)
20. Model output with malformed/unparseable claims
"""

import pytest
from app.services.model_claim_extractor import ModelClaimExtractor
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult


def create_evidence(incident_id: str, field: str, value: str, ev_type: str = "GENERIC", ev_id: str = None) -> CanonicalEvidenceRecord:
    digest = CanonicalEvidenceRecord.generate_digest(field, value)
    rec_id = ev_id or CanonicalEvidenceRecord.generate_id(incident_id, "EVT1", field)
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


def test_scenario_11_valid_evidence_id_match():
    """Scenario 11: Model cites existing evidence ID with matching value -> GROUNDED."""
    rec = create_evidence("INC-11", "process.name", "svchost.exe", "PROCESS_EXECUTION", "EV-INC-11-EVT1-proc")
    norm = build_norm("INC-11", [rec])

    verdict_output = {
        "verdict": "FALSE_POSITIVE",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": ["EV-INC-11-EVT1-proc"],
                "field": "process.name",
                "asserted_value": "svchost.exe",
            }
        ]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-11", verdict_output, norm)
    assert res.total_claims == 1
    assert res.grounded_claims == 1
    assert res.unsupported_claims == 0
    assert res.grounding_ratio == 1.0
    assert res.claims[0].is_grounded is True
    assert res.claims[0].grounding_status == "GROUNDED"


def test_scenario_12_nonexistent_evidence_id():
    """Scenario 12: Model cites nonexistent evidence ID -> EVIDENCE_REFERENCE_NOT_FOUND."""
    rec = create_evidence("INC-12", "process.name", "svchost.exe", "PROCESS_EXECUTION")
    norm = build_norm("INC-12", [rec])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": ["EV-INC-12-GHOST-ID"],
                "field": "process.name",
                "asserted_value": "powershell.exe",
            }
        ]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-12", verdict_output, norm)
    assert res.total_claims == 1
    assert res.grounded_claims == 0
    assert res.unsupported_claims == 1
    assert res.claims[0].is_grounded is False
    assert res.claims[0].grounding_status == "EVIDENCE_REFERENCE_NOT_FOUND"


def test_scenario_13_evidence_id_from_other_incident():
    """Scenario 13: Model cites evidence ID belonging to another incident -> rejected."""
    rec_other = create_evidence("INC-OTHER-99", "process.name", "cmd.exe", "PROCESS_EXECUTION", "EV-INC-OTHER-99-EVT1-proc")
    norm = build_norm("INC-13", [rec_other])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": ["EV-INC-OTHER-99-EVT1-proc"],
                "field": "process.name",
                "asserted_value": "cmd.exe",
            }
        ]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-13", verdict_output, norm)
    assert res.claims[0].is_grounded is False
    assert res.claims[0].grounding_status == "EVIDENCE_REFERENCE_NOT_FOUND"


def test_scenario_14_evidence_value_mismatch():
    """Scenario 14: Model cites valid evidence ID but fabricated value -> EVIDENCE_VALUE_MISMATCH."""
    rec = create_evidence("INC-14", "process.name", "notepad.exe", "PROCESS_EXECUTION", "EV-INC-14-EVT1-proc")
    norm = build_norm("INC-14", [rec])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "evidence_ids": ["EV-INC-14-EVT1-proc"],
                "field": "process.name",
                "asserted_value": "mimikatz.exe",  # Fabricated value
            }
        ]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-14", verdict_output, norm)
    assert res.claims[0].is_grounded is False
    assert res.claims[0].grounding_status == "EVIDENCE_VALUE_MISMATCH"


def test_scenario_15_hallucinated_process_name():
    """Scenario 15: Model free-text asserts process name not in telemetry -> ungrounded hallucination."""
    rec = create_evidence("INC-15", "process.name", "explorer.exe", "PROCESS_EXECUTION")
    norm = build_norm("INC-15", [rec])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "reason": "The attacker executed psexec.exe to perform lateral movement across the network.",
        "supporting_evidence": ["psexec.exe execution observed"]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-15", verdict_output, norm)
    assert res.has_hallucinations is True
    assert any("psexec.exe" in c.asserted_value and not c.is_grounded for c in res.claims)


def test_scenario_16_hallucinated_sha256_hash():
    """Scenario 16: Model free-text asserts SHA-256 hash not in telemetry -> ungrounded hallucination."""
    rec = create_evidence("INC-16", "process.name", "cmd.exe", "PROCESS_EXECUTION")
    norm = build_norm("INC-16", [rec])

    fake_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "reason": f"Matched malicious binary with SHA256 {fake_hash}.",
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-16", verdict_output, norm)
    assert res.has_hallucinations is True
    assert any(c.field == "file.hash_sha256" and not c.is_grounded for c in res.claims)


def test_scenario_17_hallucinated_external_ip():
    """Scenario 17: Model free-text asserts C2 external IP not in telemetry -> ungrounded hallucination."""
    rec = create_evidence("INC-17", "network.source_ip", "10.0.0.5", "NETWORK_CONNECTION")
    norm = build_norm("INC-17", [rec])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "reason": "Outbound beaconing to Russian command and control server at 198.51.100.44.",
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-17", verdict_output, norm)
    assert res.has_hallucinations is True
    assert any("198.51.100.44" in str(c.asserted_value) and not c.is_grounded for c in res.claims)


def test_scenario_18_hallucinated_parent_child_relationship():
    """Scenario 18: Model claims parent-child relationship not in telemetry."""
    rec = create_evidence("INC-18", "process.name", "powershell.exe", "PROCESS_EXECUTION")
    norm = build_norm("INC-18", [rec])

    verdict_output = {
        "verdict": "TRUE_POSITIVE",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_LINEAGE",
                "field": "process.parent_name",
                "asserted_value": "winword.exe",
            }
        ]
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-18", verdict_output, norm)
    assert res.claims[0].is_grounded is False
    assert res.has_hallucinations is True


def test_scenario_19_empty_claims():
    """Scenario 19: Model output with empty claims list defaults safely."""
    norm = build_norm("INC-19", [])
    verdict_output = {
        "verdict": "REQUIRES_ATTENTION",
        "reason": "Insufficient information to evaluate.",
        "supporting_claims": [],
        "supporting_evidence": []
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-19", verdict_output, norm)
    assert res.total_claims == 0
    assert res.grounding_ratio == 1.0
    assert res.has_hallucinations is False


def test_scenario_20_malformed_claims_handling():
    """Scenario 20: Model output with non-dict claims items handled gracefully."""
    norm = build_norm("INC-20", [])
    verdict_output = {
        "verdict": "REQUIRES_ATTENTION",
        "supporting_claims": ["not-a-dict", 1234, None],  # Malformed items
        "reason": "Clean reason"
    }

    res = ModelClaimExtractor.extract_and_ground_claims("INC-20", verdict_output, norm)
    # Should not crash
    assert isinstance(res.claims, list)

