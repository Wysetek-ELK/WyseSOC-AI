import pytest
from app.services.tokenizer_service import ModelTokenizerService
from app.services.token_budget_service import TokenBudgetService
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.provenance import classify_execution_provenance
from app.schemas.evidence_contract import (
    RuleEvidenceContract,
    EvidenceFieldRequirement,
)
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.evidence_claim import ClaimGroundingResult, ModelSupportingClaim
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult


@pytest.fixture
def mock_contract():
    return RuleEvidenceContract(
        contract_id="EC-TEST-001",
        rule_id="RULE-TEST-001",
        rule_name="Test Rule",
        version_number=1,
        status="APPROVED",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(
                field="process.command_line",
                evidence_type="PROCESS_EXECUTION",
                requirement_level="CORE",
                critical=True,
                description="Command line arguments",
            ),
        ],
    )


def test_token_budget_boundary_invariant():
    """Verify that exact prompt budget calculation enforces actual_wire + 768 <= active_max_model_len."""
    max_ctx = 4096
    reserved_output = 768
    available = TokenBudgetService.calculate_available_input_tokens(max_ctx, reserved_output)
    assert available == 3328
    assert available + reserved_output == max_ctx


def test_provenance_normalization():
    """Verify that execution_provenance normalizes to PREFLIGHT_ABSTENTION for guards."""
    prov = classify_execution_provenance(model_identifier="PREFLIGHT_ABSTENTION")
    assert prov["execution_provenance"] == "PREFLIGHT_ABSTENTION"
    assert prov["configured_provider"] == "POLICY_GUARD"

    prov_live = classify_execution_provenance(recorded_provenance="LIVE_PROVIDER")
    assert prov_live["execution_provenance"] == "LIVE_PROVIDER"


def test_abstention_with_contradiction_validation_status(mock_contract):
    """Verify that an abstention with contradictory reasoning receives ABSTENTION_WITH_CONTRADICTION, not VALIDATED."""
    preflight = PreflightValidationResult(
        incident_id="INC-TEST-001",
        rule_id="RULE-TEST-001",
        contract_id="EC-TEST-001",
        contract_version=1,
        contract_status="APPROVED",
        preflight_status="COMPLETE",
        required_evidence_count=1,
        available_required_count=1,
        evidence_completeness=1.0,
        missing_evidence_fields=[],
        critical_missing_fields=[],
        detected_contradictions=["Source IP is reported as both internal 10.0.0.1 and external 203.0.113.5"],
    )
    grounding = ClaimGroundingResult(
        incident_id="INC-TEST-001",
        total_claims=1,
        grounded_claims=1,
        unsupported_claims=0,
        grounding_ratio=1.0,
        claims=[
            ModelSupportingClaim(
                claim_type="PROCESS_EXECUTION",
                field="process.command_line",
                asserted_value="cmd.exe /c whoami",
                is_grounded=True,
                grounding_status="GROUNDED",
                cited_evidence_ids=["EV-1"],
            )
        ],
        unsupported_claim_details=[],
    )
    records = [
        CanonicalEvidenceRecord(
            evidence_id="EV-1",
            incident_id="INC-TEST-001",
            source_field="process.command_line",
            observed_value="cmd.exe /c whoami",
            evidence_type="PROCESS_EXECUTION",
            integrity_digest="digest-ev1",
        )
    ]
    norm_result = EvidenceNormalizationResult(
        incident_id="INC-TEST-001",
        total_evidence_count=1,
        available_evidence_count=1,
        records=records,
        evidence_by_type={"PROCESS_EXECUTION": records},
        evidence_by_field={"process.command_line": records},
    )

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-TEST-001",
        proposed_verdict="REQUIRES_ATTENTION",
        raw_model_confidence=50.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=mock_contract,
        model_reason="Telemetry exhibits conflicting network evidence.",
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.validation_status == "ABSTENTION_WITH_CONTRADICTION"
    assert "EVIDENCE_CONTRADICTION" in res.validation_reason_codes or "REASONING_CONTRADICTION" in res.validation_reason_codes


def test_clean_abstention_validation_status(mock_contract):
    """Verify that a sound abstention without contradictions receives VALIDATED."""
    preflight = PreflightValidationResult(
        incident_id="INC-TEST-002",
        rule_id="RULE-TEST-001",
        contract_id="EC-TEST-001",
        contract_version=1,
        contract_status="APPROVED",
        preflight_status="PARTIAL",
        required_evidence_count=2,
        available_required_count=1,
        evidence_completeness=0.5,
        missing_evidence_fields=["process.parent_command_line"],
        critical_missing_fields=[],
        detected_contradictions=[],
    )
    grounding = ClaimGroundingResult(
        incident_id="INC-TEST-002",
        total_claims=1,
        grounded_claims=1,
        unsupported_claims=0,
        grounding_ratio=1.0,
        claims=[
            ModelSupportingClaim(
                claim_type="PROCESS_EXECUTION",
                field="process.command_line",
                asserted_value="notepad.exe",
                is_grounded=True,
                grounding_status="GROUNDED",
                cited_evidence_ids=["EV-1"],
            )
        ],
        unsupported_claim_details=[],
    )
    records = [
        CanonicalEvidenceRecord(
            evidence_id="EV-1",
            incident_id="INC-TEST-002",
            source_field="process.command_line",
            observed_value="notepad.exe",
            evidence_type="PROCESS_EXECUTION",
            integrity_digest="digest-ev1",
        )
    ]
    norm_result = EvidenceNormalizationResult(
        incident_id="INC-TEST-002",
        total_evidence_count=1,
        available_evidence_count=1,
        records=records,
        evidence_by_type={"PROCESS_EXECUTION": records},
        evidence_by_field={"process.command_line": records},
    )

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-TEST-002",
        proposed_verdict="REQUIRES_ATTENTION",
        raw_model_confidence=50.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=mock_contract,
        model_reason="Telemetry is ambiguous and lacks verified authorization context; requires analyst inspection.",
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.validation_status == "VALIDATED"
    assert "EVIDENCE_VALIDATED" in res.validation_reason_codes
