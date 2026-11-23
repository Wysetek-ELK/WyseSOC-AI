import pytest
import json
import zipfile
from typing import Dict, Any, List

from app.models.rule import Rule
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.evidence_preflight import PreflightValidationResult
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.policy_compiler_service import PolicyCompilerService, CompilationExecutionMode
from app.services.token_budget_service import TokenBudgetService
from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    IncidentAdapter,
)

def _make_rec(ev_id: str, field: str, value: Any, ev_type: str) -> CanonicalEvidenceRecord:
    return CanonicalEvidenceRecord(
        evidence_id=ev_id,
        incident_id="INC-TEST",
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        integrity_digest=f"digest-{ev_id}",
    )

def _make_norm(records: List[CanonicalEvidenceRecord]) -> EvidenceNormalizationResult:
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

def test_stage4_signature_status_value_contradiction():
    """file.signature_status = SIGNED must not support an unsigned-binary claim."""
    rec = _make_rec("EV-SIG-1", "file.signature_status", "SIGNED", "FILE_CONTEXT")
    norm_result = _make_norm([rec])
    raw_verdict = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "Process binary is unsigned.",
        "supporting_claims": [
            {
                "claim_type": "FILE_CONTEXT",
                "field": "file.signature_status",
                "asserted_value": "UNSIGNED",
                "claim_text": "The binary is not digitally signed and unverified.",
                "cited_evidence_ids": ["EV-SIG-1"],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-TEST", raw_verdict, norm_result)
    assert len(grounding.claims) == 1
    claim = grounding.claims[0]
    assert not claim.is_grounded
    assert claim.grounding_status in ("UNSUPPORTED_PREDICATE", "EVIDENCE_VALUE_MISMATCH")
    assert "contradiction" in claim.reason.lower() or "signature" in claim.reason.lower()

def test_stage4_filename_alone_cannot_prove_reputation():
    """A filename alone (e.g. calc.exe) must not prove trusted reputation."""
    rec = _make_rec("EV-PROC-1", "process.file_name", "calc.exe", "PROCESS_EXECUTION")
    norm_result = _make_norm([rec])
    raw_verdict = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 95.0,
        "reason": "calc.exe is a trusted Microsoft system utility.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.file_name",
                "asserted_value": "calc.exe",
                "claim_text": "The file is a known legitimate and trusted program.",
                "cited_evidence_ids": ["EV-PROC-1"],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-TEST", raw_verdict, norm_result)
    assert len(grounding.claims) == 1
    claim = grounding.claims[0]
    assert not claim.is_grounded
    assert claim.grounding_status == "UNSUPPORTED_PREDICATE"
    assert "Filename alone does not prove trusted reputation" in claim.reason

def test_stage4_security_action_block_cannot_prove_malice():
    """A blocked process alone must not establish malicious execution."""
    rec = _make_rec("EV-ACT-1", "security.action", "block", "SECURITY_EVENT")
    norm_result = _make_norm([rec])
    raw_verdict = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "Execution blocked by agent proves malicious attack.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "security.action",
                "asserted_value": "block",
                "claim_text": "Agent blocked malicious execution.",
                "cited_evidence_ids": ["EV-ACT-1"],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-TEST", raw_verdict, norm_result)
    assert len(grounding.claims) == 1
    claim = grounding.claims[0]
    assert not claim.is_grounded
    assert claim.grounding_status == "UNSUPPORTED_PREDICATE"
    assert "A blocked process alone does not establish malicious execution" in claim.reason

def test_stage4_direct_forensic_attack_evidence_grounds_malice_without_ti():
    """Confirmed malicious behavior may be supported by direct forensic evidence without external TI feed."""
    rec = _make_rec("EV-CMD-1", "process.command_line", "vssadmin.exe delete shadows /all /quiet", "PROCESS_EXECUTION")
    norm_result = _make_norm([rec])
    raw_verdict = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 95.0,
        "reason": "Shadow copy deletion LOLBin command indicates ransomware activity.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": "vssadmin.exe delete shadows /all /quiet",
                "claim_text": "Direct forensic attack command line attempting shadow copy deletion.",
                "cited_evidence_ids": ["EV-CMD-1"],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-TEST", raw_verdict, norm_result)
    assert len(grounding.claims) == 1
    claim = grounding.claims[0]
    assert claim.is_grounded
    assert claim.grounding_status == "GROUNDED"

def test_stage4_network_file_download_incompatible_with_process_execution():
    """Network file downloads must not be interpreted as operating-system process execution."""
    rec = _make_rec("EV-NET-1", "file.name", "payload.exe", "NETWORK_FILE_DOWNLOAD")
    norm_result = _make_norm([rec])
    raw_verdict = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "Host executed malware payload.exe.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "file.name",
                "asserted_value": "payload.exe",
                "claim_text": "Process executed on endpoint.",
                "cited_evidence_ids": ["EV-NET-1"],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-TEST", raw_verdict, norm_result)
    assert len(grounding.claims) == 1
    claim = grounding.claims[0]
    assert not claim.is_grounded
    assert claim.grounding_status == "INCOMPATIBLE_EVIDENCE_TYPE"

def test_stage4_reasoning_contradiction_recorded_on_safe_abstention():
    """Reasoning contradictions (e.g. missing hash claim when present) are recorded even on safe abstention."""
    rec = _make_rec("EV-HASH-1", "file.hash_sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "FILE_HASH")
    norm_result = _make_norm([rec])
    contract = EmpiricalBenchmarkHarness._create_rule_contract("RULE-1", "Test Rule")
    preflight = EvidencePreflightValidator.validate_preflight("INC-TEST", contract, norm_result, allow_simulation=True)
    grounding = ModelClaimExtractor.extract_and_ground_claims(
        "INC-TEST",
        {"verdict": "REQUIRES_ATTENTION", "confidence": 50.0, "reason": "Missing file.hash_sha256 in telemetry."},
        norm_result,
    )
    
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-TEST",
        proposed_verdict="REQUIRES_ATTENTION",
        raw_model_confidence=50.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason="Missing file.hash_sha256 in telemetry so requires attention.",
    )
    
    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.reasoning_integrity_status == "REASONING_CONTRADICTION"
    assert len(val_res.reasoning_contradictions) > 0
    assert "file.hash_sha256" in val_res.reasoning_contradictions[0]

def test_stage3_policy_modular_optimization_parity():
    """Modular optimization saves tokens while strictly preserving all security invariants."""
    rule_id = "b2f1f1e4-117b-4b0e-87ca-65869898630b"
    rule = Rule(
        id=rule_id,
        rule_id=rule_id,
        name="Prisma SASE: Suspicious File Threat Detection",
        event_type="Prisma_SASE_Suspicious_File_Threat_Detection_",
        severity="HIGH",
        description="Palo Alto Prisma SASE Suspicious File Threat Detection",
    )
    pv = EmpiricalBenchmarkHarness._lookup_approved_prompt_version(rule_id)
    assert pv is not None
    
    std_policy = PolicyCompilerService.compile_policy(
        rule=rule, prompt_version=pv, modular_optimization=False
    )
    mod_policy = PolicyCompilerService.compile_policy(
        rule=rule, prompt_version=pv, modular_optimization=True
    )
    
    assert mod_policy.compiler_version == "v3.0.0-modular"
    # Verify invariants preserved
    assert "SECTION 1: COMMON SOC BASELINE PROTOCOL" in mod_policy.compiled_system_prompt
    assert "SECTION 2: RULE-SPECIFIC INVESTIGATION DIRECTIVE" in mod_policy.compiled_system_prompt
    assert "SECTION 4: MANDATORY EVIDENCE REQUIREMENTS" in mod_policy.compiled_system_prompt
    assert "SECTION 5: TRUE POSITIVE INDICATORS" in mod_policy.compiled_system_prompt
    assert "SECTION 6: FALSE POSITIVE INDICATORS" in mod_policy.compiled_system_prompt
    assert "SECTION 7: ABSTENTION CRITERIA" in mod_policy.compiled_system_prompt
    assert "SECTION 10: INSTRUCTION BOUNDARIES & UNTRUSTED DATA DELIMITERS" in mod_policy.compiled_system_prompt
    assert "SECTION 11: STRICT STRUCTURED JSON OUTPUT REQUIREMENTS" in mod_policy.compiled_system_prompt
    
    # Token savings confirmed
    assert mod_policy.total_estimated_tokens < std_policy.total_estimated_tokens
    print(f"Standard: {std_policy.total_estimated_tokens}, Modular: {mod_policy.total_estimated_tokens}")

def test_stage2_context_expansion_8192_allows_prisma_sase_dispatched_inference():
    """All 3 historical Prisma SASE incidents fit safely within 8,192 tokens with >= 768 completion headroom."""
    rule_id = "b2f1f1e4-117b-4b0e-87ca-65869898630b"
    rule_name = "Prisma SASE Suspicious File Threat Detection"
    mock_rule = Rule(id=rule_id, rule_id=rule_id, name=rule_name, event_type="Prisma_SASE_Suspicious_File_Threat_Detection_", severity="HIGH")
    approved_pv = EmpiricalBenchmarkHarness._lookup_approved_prompt_version(rule_id)
    contract = EmpiricalBenchmarkHarness._create_rule_contract(rule_id, rule_name)
    
    with zipfile.ZipFile("fixtures/Incident json.zip", "r") as zf:
        for inc_id in ("132499009", "132499023", "132499745"):
            fname = f"Incident json/Prisma SASE Suspicious File Threat Detection/incidentId_{inc_id}.json"
            with zf.open(fname) as f:
                raw_json = json.load(f)
            
            inc_obj = IncidentAdapter(raw_json, inc_id)
            compiled_policy = PolicyCompilerService.compile_policy(
                rule=mock_rule, prompt_version=approved_pv, modular_optimization=True
            )
            payload_dict = {
                "incident_id": inc_id,
                "rule_id": rule_id,
                "canonical_evidence": [],
                "evidence_contract": {"contract_id": contract.contract_id, "required_fields": []},
            }
            budgeted = TokenBudgetService.budget_prompt(
                compiled_policy=compiled_policy,
                incident_payload=payload_dict,
                rag_block="",
                max_context_tokens=8192,
                max_completion_tokens=768,
                reserved_overhead_tokens=50,
                model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
            )
            assert budgeted.can_proceed_to_inference is True
            headroom = 8192 - budgeted.breakdown.total_prompt_tokens
            assert headroom >= 768
