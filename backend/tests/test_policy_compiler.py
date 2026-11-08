import pytest
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.compiled_policy import CompilationExecutionMode, PolicySectionType
from app.services.policy_compiler_service import (
    PolicyCompilerService,
    UnapprovedPolicyError,
)


def test_nine_section_deterministic_compilation():
    rule = Rule(
        id="test-rule-uuid",
        rule_id="RULE-CS-01",
        name="CrowdStrike Falcon Suspicious Process",
        event_type="Process-Creation",
        severity="High",
        pattern_logic="process = 'powershell.exe' and cmdline contains '-enc'",
    )

    pv = PromptVersion(
        id="pv-uuid-01",
        prompt_id="rp-uuid-01",
        version_number=3,
        status="APPROVED",
        is_template_draft=False,
        common_prompt="ENTERPRISE SOC LEVEL-2 PROTOCOL",
        rule_specific_prompt="INVESTIGATE SUSPICIOUS POWERSHELL DIRECTIVE",
        detection_conditions="Detection Pattern: process = 'powershell.exe'",
        required_evidence="1. Process cmdline\n2. Parent process",
        tp_indicators="- Encoded commands\n- Download cradles",
        fp_indicators="- Administrative IT scripts",
        missing_info_criteria="- Truncated command line",
        escalation_conditions="- Ransomware precursor",
        analyst_questions=["What is the parent process?", "Who is the user?"],
    )

    compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=pv,
        execution_mode=CompilationExecutionMode.LIVE,
        raise_on_unapproved=True,
    )

    assert compiled.compiler_version == "v3.0.0"
    assert compiled.is_approved is True
    assert compiled.policy_status == "APPROVED"
    assert compiled.execution_mode == CompilationExecutionMode.LIVE
    assert len(compiled.sections) == 9

    # Verify strict section ordering 1 to 9
    expected_order = [
        PolicySectionType.COMMON_SOC_BASELINE,
        PolicySectionType.RULE_SPECIFIC_DIRECTIVE,
        PolicySectionType.DETECTION_CONDITIONS,
        PolicySectionType.REQUIRED_EVIDENCE,
        PolicySectionType.TRUE_POSITIVE_INDICATORS,
        PolicySectionType.FALSE_POSITIVE_INDICATORS,
        PolicySectionType.ABSTENTION_CRITERIA,
        PolicySectionType.ESCALATION_CONDITIONS,
        PolicySectionType.ANALYST_QUESTIONS,
    ]
    for idx, (sec, exp_type) in enumerate(zip(compiled.sections, expected_order), start=1):
        assert sec.section_index == idx
        assert sec.section_id == exp_type
        assert len(sec.content) > 0
        assert sec.is_trusted is True

    # Verify Section 10 instruction boundaries and Section 11 JSON schema in compiled prompt
    assert "## SECTION 10: INSTRUCTION BOUNDARIES & UNTRUSTED DATA DELIMITERS" in compiled.compiled_system_prompt
    assert "<UNTRUSTED_INCIDENT_DATA>" in compiled.compiled_system_prompt
    assert "<VERIFIED_HISTORICAL_PRECEDENTS>" in compiled.compiled_system_prompt
    assert "## SECTION 11: STRICT STRUCTURED JSON OUTPUT REQUIREMENTS" in compiled.compiled_system_prompt

    # Verify deterministic digest
    assert len(compiled.compilation_digest) == 64  # SHA-256 hex string


def test_live_mode_rejects_unapproved_draft():
    rule = Rule(
        id="test-rule-uuid",
        rule_id="RULE-CS-02",
        name="Suspicious LOLBin",
        event_type="Process-Creation",
    )

    draft_pv = PromptVersion(
        id="pv-uuid-draft",
        prompt_id="rp-uuid-02",
        version_number=1,
        status="DRAFT",
        is_template_draft=True,
        tp_indicators="Suspicious commands",
    )

    # In LIVE mode with raise_on_unapproved=True, must raise UnapprovedPolicyError
    with pytest.raises(UnapprovedPolicyError) as exc_info:
        PolicyCompilerService.compile_policy(
            rule=rule,
            prompt_version=draft_pv,
            execution_mode=CompilationExecutionMode.LIVE,
            raise_on_unapproved=True,
        )
    assert "Only APPROVED policies may execute in LIVE triage mode" in str(exc_info.value)

    # With raise_on_unapproved=False, must return compiled object with is_approved=False
    res = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=draft_pv,
        execution_mode=CompilationExecutionMode.LIVE,
        raise_on_unapproved=False,
    )
    assert res.is_approved is False
    assert res.policy_status == "DRAFT"


def test_simulation_mode_allows_draft_compilation():
    rule = Rule(
        id="test-rule-uuid",
        rule_id="RULE-CS-03",
        name="Draft Simulation Test",
        event_type="Process-Creation",
    )

    draft_pv = PromptVersion(
        id="pv-uuid-draft",
        prompt_id="rp-uuid-03",
        version_number=2,
        status="DRAFT",
        is_template_draft=True,
        tp_indicators="Draft malicious criteria",
    )

    compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=draft_pv,
        execution_mode=CompilationExecutionMode.SIMULATION,
        raise_on_unapproved=True,  # Should not raise in SIMULATION mode
    )
    assert compiled.execution_mode == CompilationExecutionMode.SIMULATION
    assert compiled.policy_status == "DRAFT"
    assert "Execution Mode: SIMULATION" in compiled.compiled_system_prompt


def test_compilation_digest_uniqueness_and_determinism():
    rule = Rule(id="r1", rule_id="RULE-01", name="Rule One", event_type="Web")
    pv1 = PromptVersion(
        id="pv1", prompt_id="rp1", version_number=1, status="APPROVED",
        tp_indicators="Indicator A"
    )
    pv2 = PromptVersion(
        id="pv1", prompt_id="rp1", version_number=1, status="APPROVED",
        tp_indicators="Indicator B (Modified)"
    )

    res1 = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv1, execution_mode=CompilationExecutionMode.LIVE)
    res1_replay = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv1, execution_mode=CompilationExecutionMode.LIVE)
    res2 = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv2, execution_mode=CompilationExecutionMode.LIVE)

    # Determinism: identical input produces identical digest
    assert res1.compilation_digest == res1_replay.compilation_digest

    # Uniqueness: modified section produces different digest
    assert res1.compilation_digest != res2.compilation_digest

