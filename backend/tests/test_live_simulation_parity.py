import pytest
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.token_budget_service import TokenBudgetService


def test_live_simulation_prompt_section_parity():
    """Verify 100% prompt parity between Live Inference and Simulation Lab."""
    rule = Rule(
        id="rule-parity-01",
        rule_id="RULE-PARITY",
        name="Parity Verification Rule",
        event_type="Authentication",
        severity="Medium",
    )

    pv = PromptVersion(
        id="pv-parity-01",
        prompt_id="rp-parity-01",
        version_number=1,
        status="APPROVED",
        is_template_draft=False,
        tp_indicators="Credential brute force attack pattern",
        fp_indicators="Authorized penetration testing window",
        required_evidence="User account, source IP, failure count",
    )

    live_compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=pv,
        execution_mode=CompilationExecutionMode.LIVE,
    )

    sim_compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=pv,
        execution_mode=CompilationExecutionMode.SIMULATION,
    )

    # All 9 sections must be identical in content and index
    assert len(live_compiled.sections) == len(sim_compiled.sections) == 9
    for live_sec, sim_sec in zip(live_compiled.sections, sim_compiled.sections):
        assert live_sec.section_index == sim_sec.section_index
        assert live_sec.section_id == sim_sec.section_id
        assert live_sec.content == sim_sec.content

    # Output schema must be identical
    assert live_compiled.model_response_schema == sim_compiled.model_response_schema

    # Token budgeting must yield identical results
    test_payload = {
        "incident_id": "INC-PARITY-01",
        "title": "Multiple Failed Logins",
        "events": [{"raw_log": "Logon failed for user admin"}],
        "canonical_evidence": [],
    }

    live_budget = TokenBudgetService.budget_prompt(
        compiled_policy=live_compiled,
        incident_payload=test_payload,
        rag_block="",
    )

    sim_budget = TokenBudgetService.budget_prompt(
        compiled_policy=sim_compiled,
        incident_payload=test_payload,
        rag_block="",
    )

    assert live_budget.can_proceed_to_inference == sim_budget.can_proceed_to_inference == True
    # The only difference in token length is the header string "LIVE" (4 chars) vs "SIMULATION" (10 chars)
    assert abs(live_budget.breakdown.total_prompt_tokens - sim_budget.breakdown.total_prompt_tokens) <= 2
