import pytest
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.token_budget_service import TokenBudgetService


def test_token_budgeting_priority_trimming():
    rule = Rule(id="r-tb-01", rule_id="RULE-TB-01", name="Token Budget Test Rule", event_type="Process")
    pv = PromptVersion(
        id="pv-tb-01", prompt_id="rp-tb-01", version_number=1, status="APPROVED",
        tp_indicators="Suspicious LOLBin execution with encoded parameters",
    )
    compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv, execution_mode=CompilationExecutionMode.LIVE)

    rag_text = (
        "<VERIFIED_HISTORICAL_PRECEDENTS>\n"
        "[PRECEDENT 1] Confirmed malware download via powershell.\n"
        "[PRECEDENT 2] Another confirmed malicious cradle.\n"
        "</VERIFIED_HISTORICAL_PRECEDENTS>"
    )

    incident_payload = {
        "incident_id": "INC-TB-01",
        "title": "Suspicious PowerShell Invocations",
        "events": [
            {"event_id": "EVT-01", "cmdline": "powershell.exe -enc AAAA", "raw_log": "Primary event"},
            {"event_id": "EVT-02", "cmdline": "powershell.exe -enc BBBB", "raw_log": "Secondary event 1"},
            {"event_id": "EVT-03", "cmdline": "powershell.exe -enc CCCC", "raw_log": "Secondary event 2"},
        ],
        "canonical_evidence": [
            {"evidence_id": "EV-01", "field": "process.cmdline", "observed_value": "powershell.exe -enc AAAA"}
        ],
        "enrichment": {
            "threat_intel": "Known bad IOC hash reported in VirusTotal",
            "geo_location": "US / California",
        }
    }

    # Case 1: Ample budget (4096 context, 1024 completion -> 3072 available)
    ample_res = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=incident_payload,
        rag_block=rag_text,
        max_context_tokens=4096,
        max_completion_tokens=1024,
    )
    assert ample_res.can_proceed_to_inference is True
    assert ample_res.breakdown.rag_trimmed is False
    assert ample_res.budgeted_rag_block == rag_text
    assert "enrichment" in ample_res.budgeted_incident_payload
    assert len(ample_res.budgeted_incident_payload["events"]) == 3

    # Case 2: Tight budget where RAG must be trimmed first
    # Total prompt without RAG is ~1872 tokens. With RAG it is ~1930 tokens.
    # Set available budget to 1900 tokens (max_context 2900, completion 1000)
    tight_res = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=incident_payload,
        rag_block=rag_text,
        max_context_tokens=2900,
        max_completion_tokens=1000,
    )
    # RAG must be trimmed first (P7 trimmed)
    assert tight_res.breakdown.rag_trimmed is True
    assert tight_res.budgeted_rag_block == ""
    assert tight_res.can_proceed_to_inference is True

    # Case 3: Extreme budget overrun where even mandatory core exceeds budget
    # Set max_context to 600 tokens (available 512 tokens), while compiled system prompt alone is > 1500 tokens
    overflow_res = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=incident_payload,
        rag_block=rag_text,
        max_context_tokens=600,
        max_completion_tokens=100,
    )
    assert overflow_res.can_proceed_to_inference is False
    assert overflow_res.breakdown.context_overflow_detected is True
    assert "CONTEXT_WINDOW_EXCEEDED" in overflow_res.abstention_reason
    # Verify critical evidence IDs were NOT naively sliced or corrupted
    assert overflow_res.budgeted_incident_payload["canonical_evidence"][0]["evidence_id"] == "EV-01"
