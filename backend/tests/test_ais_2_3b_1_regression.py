"""
AIS 2.3b.1 Regression Test Suite:
Wire Token Reservation & Semantic Verdict Grounding Integrity.

Validates the 6 mandatory negative tests and invariants:
1. Unsigned binary claimed from filename alone -> UNSUPPORTED_PREDICATE & decisive rejection.
2. Benign file asserted from recognizable filename alone -> UNSUPPORTED_PREDICATE & decisive rejection.
3. Malicious activity claimed from security-action block alone -> TP_CRITERIA_UNSATISFIED & decisive rejection.
4. Hash reported missing despite available canonical evidence -> EVIDENCE_CONTRADICTION / REASONING_CONTRADICTION.
5. Incompatible process/file alias citations -> INCOMPATIBLE_EVIDENCE_TYPE & rejection.
6. Prompt exceeding 3,328-token actual wire limit -> CONTEXT_WINDOW_EXCEEDED preflight abstention with 0 GPU waste.
7. Dispatched wire prompt <= 3,328 tokens and 768 completion reserve on live incidents 132438483 and 132527297.
8. Preflight abstentions record proposed_verdict = None, never representing fallback as model output.
"""

import pytest
import json
import zipfile
from typing import Dict, Any, List

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.evidence_claim import ModelSupportingClaim
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.tokenizer_service import ModelTokenizerService
from app.services.token_budget_service import TokenBudgetService
from app.services.policy_compiler_service import PolicyCompilerService, CompilationExecutionMode
from app.services.empirical_benchmark_harness import IncidentAdapter, EmpiricalBenchmarkHarness, BenchmarkIncidentResult
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.model_payload_allowlist import build_model_facing_payload
from app.models.rule import Rule


def _create_mock_norm_result(records: List[CanonicalEvidenceRecord]) -> EvidenceNormalizationResult:
    by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
    by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
    for r in records:
        by_type.setdefault(r.evidence_type, []).append(r)
        by_field.setdefault(r.source_field, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=records[0].incident_id if records else "INC-TEST",
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
        field_validation_status={r.source_field: "PRESENT_VALID" for r in records},
    )


def _create_mock_contract() -> RuleEvidenceContract:
    return RuleEvidenceContract(
        contract_id="EC-TEST-01",
        rule_id="RULE-TEST-01",
        rule_name="Test Contract",
        version_number=1,
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="security.action", evidence_type="SECURITY_EVENT", critical=True),
        ],
    )


def _create_mock_preflight(incident_id: str, contract: RuleEvidenceContract, norm_result: EvidenceNormalizationResult) -> PreflightValidationResult:
    return EvidencePreflightValidator.validate_preflight(incident_id, contract, norm_result, allow_simulation=True)


def test_negative_1_unsigned_binary_claimed_from_filename_alone():
    """
    Test 1: Unsigned binary claimed from filename alone.
    Assertion: 'Executing binary is not signed' cited on process.name.
    Expected: UNSUPPORTED_PREDICATE and fail-closed decisive rejection.
    """
    rec = CanonicalEvidenceRecord(
        evidence_id="EV-01-proc",
        incident_id="INC-01",
        source_field="process.name",
        observed_value="UltraViewer_Service.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest="digest01",
    )
    norm_result = _create_mock_norm_result([rec])
    contract = _create_mock_contract()
    preflight = _create_mock_preflight("INC-01", contract, norm_result)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "The executing binary is not signed.",
        "supporting_claims": [
            {
                "claim_type": "OBSERVED_FACT",
                "field": "process.name",
                "asserted_value": "UltraViewer_Service.exe",
                "claim_text": "Executing binary is not signed.",
                "cited_evidence_ids": ["EV-01-proc"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-01", model_output, norm_result)
    assert len(grounding.claims) == 1
    assert grounding.claims[0].is_grounded is False
    assert grounding.claims[0].grounding_status == "UNSUPPORTED_PREDICATE"
    assert "only provides a file/process identifier" in grounding.claims[0].reason

    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-01",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.validation_status == "REJECTED"
    assert "UNSUPPORTED_PREDICATE" in val_res.validation_reason_codes
    assert "UNSUPPORTED_CLAIM" in val_res.validation_reason_codes
    assert val_res.is_decisive_accepted is False


def test_negative_2_benign_file_asserted_from_recognizable_filename():
    """
    Test 2: Benign file asserted from recognizable filename.
    Assertion: 'Known benign administrative tool' cited on process.name.
    Expected: UNSUPPORTED_PREDICATE and decisive FP rejection.
    """
    rec = CanonicalEvidenceRecord(
        evidence_id="EV-02-proc",
        incident_id="INC-02",
        source_field="process.name",
        observed_value="powershell.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest="digest02",
    )
    norm_result = _create_mock_norm_result([rec])
    contract = _create_mock_contract()
    preflight = _create_mock_preflight("INC-02", contract, norm_result)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Known benign administrative script execution.",
        "supporting_claims": [
            {
                "claim_type": "OBSERVED_FACT",
                "field": "process.name",
                "asserted_value": "powershell.exe",
                "claim_text": "Known benign administrative utility.",
                "cited_evidence_ids": ["EV-02-proc"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-02", model_output, norm_result)
    assert len(grounding.claims) == 1
    assert grounding.claims[0].is_grounded is False
    assert grounding.claims[0].grounding_status == "UNSUPPORTED_PREDICATE"

    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-02",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.validation_status == "REJECTED"
    assert "UNSUPPORTED_PREDICATE" in val_res.validation_reason_codes
    assert val_res.is_decisive_accepted is False


def test_negative_3_malicious_activity_claimed_from_security_action_block_alone():
    """
    Test 3: Malicious activity claimed from security-action block alone.
    Assertion: Grounded claim on security.action = block without genuine adversary tradecraft.
    Expected: TP_CRITERIA_UNSATISFIED and decisive TP rejection.
    """
    rec_block = CanonicalEvidenceRecord(
        evidence_id="EV-03-act",
        incident_id="INC-03",
        source_field="security.action",
        observed_value="block",
        evidence_type="SECURITY_EVENT",
        integrity_digest="digest03",
    )
    rec_proc = CanonicalEvidenceRecord(
        evidence_id="EV-03-proc",
        incident_id="INC-03",
        source_field="process.name",
        observed_value="test.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest="digest03b",
    )
    norm_result = _create_mock_norm_result([rec_block, rec_proc])
    contract = _create_mock_contract()
    preflight = _create_mock_preflight("INC-03", contract, norm_result)

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 80.0,
        "reason": "Process was blocked by endpoint protection.",
        "supporting_claims": [
            {
                "claim_type": "OBSERVED_FACT",
                "field": "security.action",
                "asserted_value": "block",
                "claim_text": "Action blocked by endpoint control.",
                "cited_evidence_ids": ["EV-03-act"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-03", model_output, norm_result)
    assert grounding.claims[0].is_grounded is True

    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-03",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=80.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.validation_status in ("INSUFFICIENT_EVIDENCE", "REJECTED")
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes
    assert val_res.is_decisive_accepted is False


def test_negative_4_hash_reported_missing_despite_available_canonical_evidence():
    """
    Test 4: Hash reported missing despite available canonical evidence.
    Telemetry has file.hash_sha256 = 'abc...'. Model claims 'Missing file.hash_sha256'.
    Expected: EVIDENCE_CONTRADICTION and REASONING_CONTRADICTION flagged.
    """
    rec_hash = CanonicalEvidenceRecord(
        evidence_id="EV-04-hash",
        incident_id="INC-04",
        source_field="file.hash_sha256",
        observed_value="10ff43f2d4a991c83caefce1c4442fa95258d0d93f168dde339f52322aa371e9",
        evidence_type="FILE_HASH",
        integrity_digest="digest04",
    )
    rec_proc = CanonicalEvidenceRecord(
        evidence_id="EV-04-proc",
        incident_id="INC-04",
        source_field="process.name",
        observed_value="test.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest="digest04b",
    )
    norm_result = _create_mock_norm_result([rec_hash, rec_proc])
    contract = _create_mock_contract()
    preflight = _create_mock_preflight("INC-04", contract, norm_result)

    model_reason = "Missing file.hash_sha256 in incident telemetry. Cannot verify binary."
    model_output = {
        "verdict": "REQUIRES_ATTENTION",
        "confidence": 50.0,
        "reason": model_reason,
        "supporting_claims": [],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-04", model_output, norm_result)

    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-04",
        proposed_verdict="REQUIRES_ATTENTION",
        raw_model_confidence=50.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_reason,
    )

    assert "EVIDENCE_CONTRADICTION" in val_res.validation_reason_codes
    assert "REASONING_CONTRADICTION" in val_res.validation_reason_codes
    assert any("file.hash_sha256" in c for c in val_res.detected_contradictions)


def test_negative_5_incompatible_process_file_alias_citations():
    """
    Test 5: Incompatible process/file alias citations.
    Model cites NETWORK_CONNECTION evidence with claim_type PROCESS_EXECUTION.
    Expected: INCOMPATIBLE_EVIDENCE_TYPE and is_grounded = False.
    """
    rec_net = CanonicalEvidenceRecord(
        evidence_id="EV-05-net",
        incident_id="INC-05",
        source_field="network.source_ip",
        observed_value="10.0.0.1",
        evidence_type="NETWORK_CONNECTION",
        integrity_digest="digest05",
    )
    norm_result = _create_mock_norm_result([rec_net])

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 75.0,
        "reason": "Process executed on network address.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "network.source_ip",
                "asserted_value": "10.0.0.1",
                "claim_text": "Binary executed on source IP.",
                "cited_evidence_ids": ["EV-05-net"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-05", model_output, norm_result)
    assert len(grounding.claims) == 1
    assert grounding.claims[0].is_grounded is False
    assert grounding.claims[0].grounding_status == "INCOMPATIBLE_EVIDENCE_TYPE"


def test_negative_6_prompt_exceeding_3328_token_wire_limit():
    """
    Test 6: Prompt exceeding 3,328-token actual wire limit.
    Expected: CONTEXT_WINDOW_EXCEEDED preflight abstention with can_proceed = False.
    """
    # Create massive un-trimmable policy
    massive_policy_text = "SECTION 2: MANDATORY DIRECTIVE.\n" + ("CRITICAL FORENSIC REQUIREMENT " * 800)
    rule = Rule(
        id="RULE-OVERFLOW-01",
        rule_id="RULE-OVERFLOW-01",
        name="Massive Rule",
        event_type="OVERFLOW",
        severity="HIGH",
    )
    compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=None)
    compiled.compiled_system_prompt = massive_policy_text

    payload = {
        "incident_id": "INC-OVERFLOW",
        "canonical_evidence": [],
        "evidence_contract": {"contract_id": "EC-OF", "required_fields": ["field1"]},
    }

    budgeted = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload,
        max_context_tokens=4096,
        max_completion_tokens=768,
        model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
    )

    assert budgeted.can_proceed_to_inference is False
    assert budgeted.breakdown.context_overflow_detected is True
    assert "CONTEXT_WINDOW_EXCEEDED" in budgeted.abstention_reason
    assert budgeted.breakdown.available_prompt_budget == 3328
    assert budgeted.breakdown.max_completion_tokens == 768


def test_live_incidents_wire_tokens_and_completion_reserve():
    """
    Test 7: Dispatched wire prompt <= 3,328 tokens and 768 completion reserve
    on live benchmark incidents 132438483 and 132527297.
    """
    for inc_id in ("132438483", "132527297"):
        with zipfile.ZipFile("fixtures/Incident json.zip", "r") as zf:
            name = f"Incident json/Crowdstrike Suspicious Activity/IncidnetId_{inc_id}.json"
            with zf.open(name) as f:
                raw_inc = json.load(f)

        inc_obj = IncidentAdapter(raw_inc, inc_id)
        norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc_obj, None)
        contract = EmpiricalBenchmarkHarness._create_rule_contract(
            "0974a66e-ede2-4a6a-821b-6283a99c8aa4", "Crowdstrike: Suspicious Activity"
        )
        mock_rule = Rule(
            id="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
            rule_id="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
            name="Crowdstrike: Suspicious Activity",
            event_type="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
            severity="MEDIUM",
            description="Empirical benchmark rule for Crowdstrike: Suspicious Activity",
        )
        compiled_policy = PolicyCompilerService.compile_policy(
            rule=mock_rule,
            prompt_version=None,
            execution_mode=CompilationExecutionMode.LIVE,
            raise_on_unapproved=False,
        )
        payload_dict = build_model_facing_payload(
            incident=inc_obj,
            rule=mock_rule,
            events=inc_obj.events,
            max_events=10,
        )
        payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_res.records]
        payload_dict["evidence_contract"] = {
            "contract_id": contract.contract_id,
            "version": contract.version_number,
            "required_fields": [r.field for r in contract.required_evidence],
        }
        rule_spec = {
            "id": mock_rule.id,
            "rule_id": mock_rule.rule_id,
            "name": mock_rule.name,
            "severity": mock_rule.severity,
            "description": mock_rule.description or "",
        }
        rule_overhead = TokenBudgetService.estimate_tokens(rule_spec)
        budgeted = TokenBudgetService.budget_prompt(
            compiled_policy=compiled_policy,
            incident_payload=payload_dict,
            rag_block="",
            max_context_tokens=4096,
            max_completion_tokens=768,
            reserved_overhead_tokens=rule_overhead,
            model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
        )

        assert budgeted.can_proceed_to_inference is True
        assert budgeted.breakdown.total_prompt_tokens <= 3328, (
            f"Incident {inc_id} wire tokens ({budgeted.breakdown.total_prompt_tokens}) exceeds wire ceiling (3,328)"
        )
        # Verify 768 completion reserve fits within 4096 physical ceiling
        assert budgeted.breakdown.total_prompt_tokens + 768 <= 4096


def test_preflight_abstention_never_represents_fallback_as_model_verdict():
    """
    Test 8: Preflight abstention records raw_proposed_verdict = None.
    Never represents preflight fallback as a model-proposed verdict.
    """
    result = EmpiricalBenchmarkHarness._create_rule_contract("R1", "Test")
    # Simulate a result on preflight abstention
    res = BenchmarkIncidentResult(
        incident_id="INC-PREFLIGHT-01",
        rule_id="R1",
        rule_name="Test Rule",
        ground_truth_label="VERIFIED_TP",
        raw_proposed_verdict=None,
        raw_proposed_confidence=0.0,
        raw_proposed_reason="CONTEXT_WINDOW_EXCEEDED",
        final_authoritative_verdict="REQUIRES_ATTENTION",
        is_decisive_accepted=False,
        validation_status="CONTEXT_WINDOW_EXCEEDED",
        validation_reason_codes=["CONTEXT_WINDOW_EXCEEDED"],
        trust_score=0,
        raw_trust_score=0.0,
        schema_compliant=True,
        grounding_ratio=0.0,
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        finish_reason="abstained_preflight",
    )

    metrics = EmpiricalBenchmarkHarness.calculate_cohort_metrics([res])
    assert metrics.real_gpu_dispatched_count == 0
    assert metrics.preflight_abstained_count == 1
    assert metrics.model_no_inference_count == 1
    assert metrics.model_proposed_tp_count == 0
    assert metrics.model_proposed_attention_count == 0
    assert metrics.validator_decisive_accepted_count == 0
    assert metrics.decisive_decisions_count == 0
    assert metrics.overall_accuracy is None
    assert "No decisive predictions accepted" in metrics.selective_accuracy_detail
