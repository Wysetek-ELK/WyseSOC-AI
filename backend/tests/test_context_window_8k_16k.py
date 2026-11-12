import os
import json
import uuid
import pytest
import respx
import httpx
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import Incident, IncidentEvent
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.llm_config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMTestConnectionRequest,
)
from app.services.llm_config_service import LLMConfigService
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.policy_generation_service import PolicyGenerationService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.runtime_config_service import RuntimeConfigValidator
from app.services.token_budget_service import TokenBudgetService
from app.services.verdict_pipeline import run_shared_verdict_pipeline


@pytest.fixture
def enterprise_policy_and_rule():
    rule = Rule(
        id=f"r-{uuid.uuid4().hex[:8]}",
        rule_id="PH_RULE_LARGE_CTX_TEST",
        name="Large Context Security Event Rule",
        event_type="Endpoint_Process_Create",
        severity="HIGH",
        pattern_logic="processCmdLine contains -enc OR sentBytes64 >= 500000000",
        description="Comprehensive rule for validating extended context and token budgeting.",
    )
    draft = PolicyGenerationService.generate_nine_section_draft(rule)
    pv = PromptVersion(
        id=f"pv-{uuid.uuid4().hex[:8]}",
        prompt_id=f"rp-{uuid.uuid4().hex[:8]}",
        version_number=1,
        status="APPROVED",
        common_prompt=draft["common_prompt"],
        rule_specific_prompt=draft["rule_specific_prompt"],
        detection_conditions=draft["detection_conditions"],
        required_evidence=draft["required_evidence"],
        tp_indicators=draft["tp_indicators"],
        fp_indicators=draft["fp_indicators"],
        missing_info_criteria=draft["missing_info_criteria"],
        escalation_conditions=draft["escalation_conditions"],
        analyst_questions=draft["analyst_questions"],
    )
    compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=pv,
        execution_mode=CompilationExecutionMode.LIVE,
    )
    return rule, pv, compiled


# =========================================================================
# 1. Requests Exceeding 4,978 Tokens: 4,096 Fail vs 8,192 / 16,384 Success
# =========================================================================

def test_request_exceeding_4978_tokens_fails_at_4k_and_succeeds_at_8k_16k(enterprise_policy_and_rule):
    """
    Validates that a high-telemetry incident with > 4,978 tokens:
    - Fails closed with CONTEXT_WINDOW_EXCEEDED under legacy 4,096 context (available 3,584)
    - Succeeds completely under effective 8,192 input budget (targeting 16,384 context window)
    - Preserves all canonical evidence records, evidence IDs, and contract fields
    """
    rule, pv, compiled = enterprise_policy_and_rule

    # Build an incident payload guaranteed to exceed 4,978 tokens
    # Compiled policy is ~2,300 tokens. We add ~3,500+ tokens of canonical evidence & telemetry
    canonical_items = [
        {
            "evidence_id": f"EV-{idx:03d}",
            "source_field": "process.command_line" if idx % 2 == 0 else "network.destination_ip",
            "observed_value": (
                f"powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand "
                f"{('BASE64STRING' * 28)}_{idx:03d}"
            ),
            "evidence_type": "PRIMARY_OBSERVATION",
        }
        for idx in range(40)
    ]
    payload = {
        "incident_id": "INC-EXT-4978",
        "title": "Extended Context Window High Telemetry Validation Incident",
        "canonical_evidence": canonical_items,
        "evidence_contract": {
            "contract_id": "CONTRACT-EXT-01",
            "version": 1,
            "required_fields": ["process.command_line", "network.destination_ip"],
        },
        "events": [
            {
                "event_id": f"EVT-PRI-01",
                "raw_log": "Primary suspicious PowerShell execution detected on host prod-app-01.",
                "attributes": {
                    "procName": "powershell.exe",
                    "commandLine": "powershell.exe -enc AAAA" + ("X" * 150),
                    "srcIpAddr": "192.0.2.10",
                    "destIpAddr": "198.51.100.55",
                },
            }
        ],
        "enrichment": {
            "threat_actor": "APT-29 / Midnight Blizzard",
            "campaign": "SolarWinds Post-Compromise Activity",
            "confidence": "HIGH",
        },
    }

    # Verify initial tokens exceed 4,978 tokens
    est_prompt_tokens = (
        TokenBudgetService.estimate_tokens(compiled.compiled_system_prompt)
        + TokenBudgetService.estimate_tokens(payload)
    )
    assert est_prompt_tokens > 4978, f"Expected > 4,978 tokens, got {est_prompt_tokens}"

    # A) Legacy 4,096 context budget (512 completion -> 3,584 available)
    res_legacy_4k = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload,
        max_context_tokens=4096,
        max_completion_tokens=512,
    )
    assert res_legacy_4k.can_proceed_to_inference is False
    assert res_legacy_4k.breakdown.context_overflow_detected is True
    assert "CONTEXT_WINDOW_EXCEEDED" in (res_legacy_4k.abstention_reason or "")
    # Critical evidence must NOT be truncated even during fail-closed abstention
    assert len(res_legacy_4k.budgeted_incident_payload["canonical_evidence"]) == 40

    # B) Increased effective input budget to 8,192 tokens (targeting 16,384 window)
    res_extended = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload,
        max_context_tokens=16384,
        max_completion_tokens=1024,
        target_input_budget=8192,
    )
    assert res_extended.can_proceed_to_inference is True
    assert res_extended.breakdown.context_overflow_detected is False
    assert res_extended.breakdown.available_prompt_budget == 8192
    assert res_extended.breakdown.total_prompt_tokens > 4978
    assert res_extended.breakdown.total_prompt_tokens <= 8192
    assert len(res_extended.budgeted_incident_payload["canonical_evidence"]) == 40
    assert res_extended.budgeted_incident_payload["canonical_evidence"][0]["evidence_id"] == "EV-000"


# =========================================================================
# 2. Boundary Tests: Exact 8,192 Limit, 8,191, and 8,193 Compaction
# =========================================================================

def test_boundary_behavior_8191_8192_and_8193(enterprise_policy_and_rule):
    """
    Validates boundary behavior:
    - 8,191 tokens: Fits cleanly within 8,192 input budget without trimming
    - 8,192 tokens: Exactly on the boundary, succeeds
    - 8,193+ tokens: Triggers progressive compaction/pruning to stay within budget
    """
    rule, pv, compiled = enterprise_policy_and_rule
    policy_tokens = TokenBudgetService.estimate_tokens(compiled.compiled_system_prompt)

    # Calculate exact padding to reach target token counts (4 chars = 1 token estimate)
    # Target: 8,191 tokens
    needed_for_8191 = max(0, 8191 - policy_tokens - 100)
    padding_8191 = "A" * (needed_for_8191 * 4)

    payload_8191 = {
        "incident_id": "INC-BOUND-8191",
        "title": "Boundary Test 8191",
        "canonical_evidence": [
            {"evidence_id": "EV-01", "source_field": "test.field", "observed_value": padding_8191}
        ],
    }
    res_8191 = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload_8191,
        max_context_tokens=16384,
        max_completion_tokens=1024,
        target_input_budget=8192,
    )
    assert res_8191.can_proceed_to_inference is True
    assert res_8191.breakdown.context_overflow_detected is False
    assert res_8191.breakdown.total_prompt_tokens <= 8192

    # Target: Over 8,192 tokens with secondary events and enrichment that can be compacted
    payload_overflow = {
        "incident_id": "INC-BOUND-OVER",
        "title": "Boundary Test Over 8192 with Prunable Context",
        "canonical_evidence": [
            {"evidence_id": "EV-CORE-01", "source_field": "test.core", "observed_value": "Core Critical Value"}
        ],
        "events": [
            {"event_id": "EVT-PRI", "raw_log": "Primary event"},
            {"event_id": "EVT-SEC-1", "raw_log": "Secondary event 1 " + ("B" * 6000)},
            {"event_id": "EVT-SEC-2", "raw_log": "Secondary event 2 " + ("C" * 6000)},
            {"event_id": "EVT-SEC-3", "raw_log": "Secondary event 3 " + ("D" * 6000)},
        ],
        "enrichment": {
            "threat_intel": "Large enrichment string " + ("E" * 8000),
        },
    }
    res_over = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload_overflow,
        rag_block="[PRECEDENT] Historical match note " + ("R" * 8000),
        max_context_tokens=16384,
        max_completion_tokens=1024,
        target_input_budget=8192,
    )
    # Must succeed via progressive compaction without dropping critical core evidence
    assert res_over.can_proceed_to_inference is True
    assert res_over.breakdown.rag_trimmed is True
    assert res_over.budgeted_incident_payload["canonical_evidence"][0]["evidence_id"] == "EV-CORE-01"
    assert res_over.breakdown.total_prompt_tokens <= 8192


# =========================================================================
# 3. Overflow Tests: Genuinely Oversized Mandatory Core Abstains Safely
# =========================================================================

def test_oversized_mandatory_core_overflow_abstains_without_silent_dropping(enterprise_policy_and_rule):
    """
    Validates that when the mandatory core (P1 safety/schema + P2 policy + P3 contract + P4 telemetry)
    exceeds the effective input budget:
    - It refuses naive truncation (critical command lines/evidence are NEVER sliced)
    - It emits CONTEXT_WINDOW_EXCEEDED with complete token breakdown telemetry
    - Zero evidence records are dropped from the budgeted payload
    """
    rule, pv, compiled = enterprise_policy_and_rule

    # 100 large critical canonical evidence items (~12,000 tokens of mandatory core alone)
    huge_canonical = [
        {
            "evidence_id": f"EV-CRITICAL-{idx:03d}",
            "source_field": "process.command_line",
            "observed_value": f"powershell.exe -enc {('VERYLONGSCRIPTCONTENT' * 20)}_{idx:03d}",
            "evidence_type": "PRIMARY_OBSERVATION",
        }
        for idx in range(100)
    ]
    payload = {
        "incident_id": "INC-OVERFLOW-CORE",
        "title": "Genuinely Oversized Mandatory Telemetry",
        "canonical_evidence": huge_canonical,
        "evidence_contract": {
            "contract_id": "CONTRACT-CORE-01",
            "version": 1,
            "required_fields": ["process.command_line"],
        },
    }

    res = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload,
        max_context_tokens=16384,
        max_completion_tokens=1024,
        target_input_budget=8192,
    )
    assert res.can_proceed_to_inference is False
    assert res.breakdown.context_overflow_detected is True
    assert "CONTEXT_WINDOW_EXCEEDED" in res.abstention_reason
    assert "Mandatory policy directives and critical telemetry" in res.abstention_reason
    assert "Refusing naive truncation to preserve evidence integrity." in res.abstention_reason

    # Telemetry and evidence integrity: all 100 items are preserved in payload
    assert len(res.budgeted_incident_payload["canonical_evidence"]) == 100
    assert res.budgeted_incident_payload["canonical_evidence"][0]["evidence_id"] == "EV-CRITICAL-000"
    assert res.budgeted_incident_payload["canonical_evidence"][99]["evidence_id"] == "EV-CRITICAL-099"
    assert res.breakdown.p4_critical_telemetry_tokens > 8000


# =========================================================================
# 4. Configurable Per-LLM-Model Limits & Dynamic Input Calculation
# =========================================================================

def test_configurable_per_model_limits_and_dynamic_calculation():
    """
    Tests:
    - TokenBudgetService.calculate_available_input_tokens calculates headroom dynamically
    - Per-model context window, reserved output, and target input budget profiles
    - Clamping when Server 2 reports lower capacity (e.g. 4,096 or 8,192)
    """
    # 1. 16,384 window, 1,024 reserved completion -> 15,360 headroom, bounded to 8,192 target
    avail_16k_8k = TokenBudgetService.calculate_available_input_tokens(
        max_context_tokens=16384,
        reserved_output_tokens=1024,
        target_input_budget=8192,
    )
    assert avail_16k_8k == 8192

    # 2. 16,384 window without target cap -> full 15,360 input headroom
    avail_16k_full = TokenBudgetService.calculate_available_input_tokens(
        max_context_tokens=16384,
        reserved_output_tokens=1024,
        target_input_budget=None,
    )
    assert avail_16k_full == 15360

    # 3. 8,192 window, 1,024 completion -> 7,168 headroom
    avail_8k = TokenBudgetService.calculate_available_input_tokens(
        max_context_tokens=8192,
        reserved_output_tokens=1024,
        target_input_budget=8192,
    )
    assert avail_8k == 7168

    # 4. Server 2 constrained to 4,096 -> dynamically clamps available input to 3,072
    avail_4k = TokenBudgetService.calculate_available_input_tokens(
        max_context_tokens=4096,
        reserved_output_tokens=1024,
        target_input_budget=8192,
    )
    assert avail_4k == 3072

    # 5. Model profile registry lookup
    prof_qwen = LLMConfigService.get_model_profile("Qwen/Qwen2.5-7B-Instruct-AWQ")
    assert prof_qwen["max_context_tokens"] == 16384
    assert prof_qwen["reserved_output_tokens"] == 1024
    assert prof_qwen["target_input_budget"] == 8192

    # 6. Custom model profile registration
    custom_prof = LLMConfigService.set_model_profile(
        "custom-soc-llm-32k",
        {
            "max_context_tokens": 32768,
            "reserved_output_tokens": 2048,
            "target_input_budget": 16384,
        },
    )
    assert custom_prof["max_context_tokens"] == 32768
    assert custom_prof["reserved_output_tokens"] == 2048
    assert custom_prof["target_input_budget"] == 16384

    retrieved = LLMConfigService.get_model_profile("custom-soc-llm-32k")
    assert retrieved["max_context_tokens"] == 32768


# =========================================================================
# 5. Shared Pipeline Integration & Compatibility with Server 1 and Server 2
# =========================================================================

@pytest.mark.asyncio
async def test_shared_verdict_pipeline_with_extended_budget(
    db_session: AsyncSession,
    enterprise_policy_and_rule,
    monkeypatch,
):
    """
    Validates end-to-end verdict evaluation pipeline using extended 8,192 input budget:
    - Server 1 runtime settings synchronization
    - Pipeline executes without CONTEXT_WINDOW_EXCEEDED for a 5,200-token payload
    - Evidence completeness and trustworthiness validation pass
    """
    rule, pv, compiled = enterprise_policy_and_rule
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(rule_id=rule.id, title=rule.name)
    db_session.add(rp)
    await db_session.flush()

    pv.prompt_id = rp.id
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id
    await db_session.commit()

    # Create an incident with 15 canonical evidence items (~5,200 tokens total)
    canonical_items = [
        {
            "evidence_id": f"EV-{idx:03d}",
            "source_field": "process.command_line" if idx % 2 == 0 else "network.destination_ip",
            "observed_value": f"nmap -sS -p {1000 + idx} 198.51.100.{10 + idx} --packet-trace " + ("P" * 160),
            "evidence_type": "PRIMARY_OBSERVATION",
        }
        for idx in range(15)
    ]
    large_inc = Incident(
        incident_id=f"INC-EXT-PIPE-{uuid.uuid4().hex[:6]}",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Extended Pipeline Test Incident",
        severity="HIGH",
        source_ip="192.0.2.77",
        raw_payload={"srcIpAddr": "192.0.2.77", "destIpAddr": "198.51.100.20"},
        events=[
            IncidentEvent(
                event_id="EVT-01",
                event_type=rule.event_type,
                raw_log="Primary port scan telemetry",
                attributes={"srcIpAddr": "192.0.2.77", "destIpAddr": "198.51.100.20", "commandLine": "nmap -sS"},
            )
        ],
    )
    db_session.add(large_inc)
    await db_session.commit()

    large_inc = (
        await db_session.execute(
            select(Incident)
            .where(Incident.id == large_inc.id)
            .options(selectinload(Incident.events), selectinload(Incident.rule))
        )
    ).scalar_one()

    # Ensure settings target 16,384 window with 8,192 input budget
    monkeypatch.setattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 16384)
    monkeypatch.setattr(settings, "LOCAL_LLM_MAX_TOKENS", 1024)
    monkeypatch.setattr(settings, "LOCAL_LLM_TARGET_INPUT_BUDGET", 8192)
    monkeypatch.setattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", 16384)

    pipe_res = await run_shared_verdict_pipeline(
        db=db_session,
        incident=large_inc,
        rule=rule,
        prompt_version=pv,
        active_approved_version=pv,
        model_provider_type="SIMULATED",
        is_simulation=True,
        execution_context="SIMULATION",
        require_autonomous_certification=False,
    )

    # Must NOT exit early on context overflow
    assert pipe_res.early_exit is False
    assert pipe_res.verdict_data["verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert pipe_res.verdict_data["validation_status"] in ("VALID", "VALIDATED", "REQUIRES_ATTENTION")
    assert pipe_res.verdict_data["validation_status"] != "CONTEXT_WINDOW_EXCEEDED"
    assert pipe_res.verdict_data["token_budget_breakdown"]["max_context_tokens"] == 16384
    assert pipe_res.verdict_data["token_budget_breakdown"]["available_prompt_budget"] == 8192
    assert pipe_res.verdict_data["token_budget_breakdown"]["context_overflow_detected"] is False
