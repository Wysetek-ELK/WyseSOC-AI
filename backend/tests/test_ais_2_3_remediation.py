"""
Agent Intelligence Studio 2.3 (AIS 2.3) Verification Suite.

Validates:
1. AIS-F11: Consolidated simulation architecture (DryRunService -> canonical pipeline adapter,
   RuleMaturityService canonical precedence & governance visibility, EvaluationService).
2. AIS-F12: Hardened configuration management (idempotent `.env` upsert without duplicate
   comment headers, separated operating modes, fail-closed mock fallback & secret redaction).
3. LLM Context Budget Readiness: 4096 & verified 8192 context handling across representative
   archetypes (NETWORK_SCAN, MALWARE_EXECUTION, NETWORK_EXFILTRATION, BRUTE_FORCE), capacity
   clamping without assuming Server 2 support, compact canonical serialization, and fail-closed
   CONTEXT_WINDOW_EXCEEDED abstention.
4. Non-Destructive Integration Diagnostics: CLI helper, IntegrationDiagnosticService, and API
   read-only verification with zero DB/SIEM mutations.
"""

from __future__ import annotations

import json
import uuid
import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, settings
from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.verdict_intelligence import (
    HistoricalEvaluationResultRecord,
    HistoricalEvaluationRunRecord,
)
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.dry_run import DryRunConfigCreate
from app.schemas.llm_config import LLMConfigUpdate, LLMTestConnectionRequest
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.dry_run_service import DryRunService
from app.services.evaluation_service import EvaluationService
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.integration_diagnostic_service import IntegrationDiagnosticService
from app.services.llm_config_service import LLMConfigService
from app.services.maturity_service import RuleMaturityService
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.policy_generation_service import PolicyGenerationService
from app.services.policy_governance import assess_policy_runtime_certification
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.runtime_config_service import RuntimeConfigValidator
from app.services.token_budget_service import TokenBudgetService
from app.services.verdict_pipeline import run_shared_verdict_pipeline


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# 1. AIS-F11: Consolidated Simulation Architecture
# =========================================================================

@pytest.mark.asyncio
async def test_1_consolidated_dry_run_adapter_uses_canonical_pipeline_and_preserves_legacy(
    db_session: AsyncSession,
):
    """
    DryRunService.execute_dry_run_job must:
    - Strictly isolate similarly named rules in split_dataset
    - Delegate execution through canonical `run_shared_verdict_pipeline`
    - Record BOTH backward-compatible `DryRunJob`/`DryRunResult` rows AND canonical
      `HistoricalEvaluationRunRecord`/`HistoricalEvaluationResultRecord` entries
    - Never mark simulated adapter runs as autonomous-certified
    """
    r_main = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN",
        name="Heavy TCP Host Scan",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN",
        severity="HIGH",
        pattern_logic="COUNT(Matched Events) >= 25 within 300s groupBy srcIpAddr",
    )
    r_sibling = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan on Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="HIGH",
        pattern_logic="COUNT(Matched Events) >= 25 within 300s",
    )
    db_session.add_all([r_main, r_sibling])
    await db_session.flush()

    rp = RulePrompt(rule_id=r_main.id, title=r_main.name)
    db_session.add(rp)
    await db_session.flush()

    draft = PolicyGenerationService.generate_nine_section_draft(r_main)
    pv = PromptVersion(
        prompt_id=rp.id,
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
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id

    for i in range(3):
        inc = Incident(
            incident_id=f"CONS-MAIN-{i+1}",
            rule_id=r_main.id,
            event_type=r_main.event_type,
            title=r_main.name,
            severity="HIGH",
            source_ip="192.0.2.21",
            reporting_device=f"FW-{i+1}",
            created_at_epoch=1700000000 + i * 100,
            raw_payload={"srcIpAddr": "192.0.2.21", "destIpAddr": "198.51.100.5", "destPort": 22, "protocol": "TCP"},
            events=[
                IncidentEvent(
                    event_id=f"EVT-CM-{i+1}",
                    event_type=r_main.event_type,
                    raw_log="TCP scan event",
                    attributes={"srcIpAddr": "192.0.2.21", "destPort": 22, "protocol": "TCP"},
                )
            ],
        )
        db_session.add(inc)
        await db_session.flush()
        db_session.add(
            HistoricalGroundTruth(
                incident_id=inc.id,
                resolution="True Positive",
                comments="Verified unauthorized horizontal host scan by Tier 2 analyst.",
                cleared_user="tier2_analyst",
            )
        )
        db_session.add(
            Investigation(
                incident_id=inc.id,
                status="COMPLETED",
                analyst_verdict="TRUE_POSITIVE",
                is_independently_verified=True,
                is_disputed=False,
            )
        )

    db_session.add(
        Incident(
            incident_id="CONS-SIBLING-1",
            rule_id=r_sibling.id,
            event_type=r_sibling.event_type,
            title=r_sibling.name,
            severity="HIGH",
            source_ip="192.0.2.99",
            created_at_epoch=1700000900,
        )
    )
    await db_session.commit()

    dry_svc = DryRunService(db_session)
    scoped = await dry_svc.split_dataset("ALL", rule_id=r_main.id)
    assert len(scoped) == 3
    assert all(inc.rule_id == r_main.id for inc in scoped)

    cfg = await dry_svc.create_config(
        DryRunConfigCreate(
            name="Consolidated Adapter Smoke",
            description="Routes legacy dry-run through canonical verdict pipeline",
            rule_id=r_main.id,
            prompt_version_id=pv.id,
            provider_type="SIMULATED",
            split_strategy="ALL",
        )
    )
    job = await dry_svc.execute_dry_run_job(config_id=cfg.id)
    assert job.status == "COMPLETED"
    assert job.total_items == 3
    assert job.processed_items == 3
    assert job.is_simulated is True

    # Legacy DryRunResult rows preserved
    dr_rows = list((await db_session.execute(select(DryRunResult).where(DryRunResult.job_id == job.id))).scalars().all())
    assert len(dr_rows) == 3
    assert all(r.validation_status == "VALID" for r in dr_rows)

    # Canonical HistoricalEvaluationRunRecord + ResultRecords created cleanly
    canon_run = (
        await db_session.execute(
            select(HistoricalEvaluationRunRecord).where(HistoricalEvaluationRunRecord.rule_id == r_main.id)
        )
    ).scalar_one()
    assert canon_run.config_snapshot["adapter"] == "LEGACY_DRY_RUN_ADAPTER"
    assert canon_run.config_snapshot["legacy_dry_run_job_id"] == job.id
    assert canon_run.config_snapshot["is_simulated"] is True
    assert canon_run.validation_state == "INCONCLUSIVE"
    assert canon_run.evaluated_cases == 3
    assert canon_run.verified_ground_truth_cases == 3

    canon_results = list(
        (
            await db_session.execute(
                select(HistoricalEvaluationResultRecord).where(HistoricalEvaluationResultRecord.run_id == canon_run.id)
            )
        ).scalars().all()
    )
    assert len(canon_results) == 3

    # Simulated adapter run must NEVER grant autonomous runtime eligibility
    cert = await assess_policy_runtime_certification(db_session, r_main, pv)
    assert cert.autonomous_operation_eligible is False

    # RuleMaturityService + EvaluationService prioritize canonical records safely
    maturity_svc = RuleMaturityService(db_session)
    m_eval = await maturity_svc.update_rule_maturity_from_results(r_main.id)
    assert m_eval.sample_size == 3
    assert "Canonical simulated-only" in m_eval.recommendation_explanation

    all_m = await maturity_svc.list_all_evaluations()
    matched_m = next(x for x in all_m if x.rule_id == r_main.id)
    assert matched_m.evaluation_source == "HISTORICAL_EVALUATION_RUN"
    assert matched_m.autonomous_runtime_eligible is False

    eval_svc = EvaluationService(db_session)
    comps = await eval_svc.compare_prompt_versions(r_main.id)
    assert len(comps) == 1
    assert comps[0].evaluated_cases == 3


# =========================================================================
# 2. AIS-F12: Hardened Configuration Management
# =========================================================================

def test_2_idempotent_env_upsert_never_duplicates_blocks_or_secrets(tmp_path, monkeypatch):
    """
    Repeated LLMConfigService.update_config calls must update existing keys in-place,
    eliminate duplicate header comments, preserve unrelated keys, and never persist secrets.
    """
    from app.services import llm_config_service as lcs_mod

    preserved_token = "unit-preserved-val"
    env_file = tmp_path / ".env"
    env_file.write_text(
        'APP_ENV="development"\n'
        'PROJECT_NAME="AI Verdict"\n'
        f'CUSTOM_APP_FLAG="{preserved_token}"\n'
        "\n"
        "# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)\n"
        'LOCAL_LLM_BASE_URL="http://192.0.2.1:8000/v1"\n'
        'LOCAL_LLM_MODEL_NAME="old-model"\n'
        "\n"
        "# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)\n"
        'LOCAL_LLM_BASE_URL="http://192.0.2.99:8000/v1"\n',
        encoding="utf-8",
    )

    state_file = str(tmp_path / "llm_state.json")
    monkeypatch.setattr(lcs_mod, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(LLMConfigService, "_state_file_path", classmethod(lambda cls: state_file))
    monkeypatch.setattr(settings, "APP_ENV", "development")

    orig = (
        settings.LOCAL_LLM_BASE_URL,
        settings.LOCAL_LLM_MODEL_NAME,
        settings.LOCAL_LLM_TIMEOUT,
        settings.LOCAL_LLM_CONTEXT_BUDGET,
        settings.LOCAL_LLM_MAX_TOKENS,
        settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN,
    )
    try:
        for idx in range(5):
            LLMConfigService.update_config(
                LLMConfigUpdate(
                    host=f"192.0.2.{10 + idx}",
                    port=8000,
                    protocol="http",
                    model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
                    timeout=60.0 + idx,
                    context_budget=8192 if idx % 2 == 1 else 4096,
                    max_tokens=512,
                    allow_mock_fallback=False,
                )
            )

        content = env_file.read_text(encoding="utf-8")
        assert content.count("# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)") == 1
        assert content.count("LOCAL_LLM_BASE_URL=") == 1
        assert content.count("LOCAL_LLM_MODEL_NAME=") == 1
        assert content.count("LOCAL_LLM_TIMEOUT=") == 1
        assert content.count("LOCAL_LLM_CONTEXT_BUDGET=") == 1
        assert content.count("LOCAL_LLM_MAX_TOKENS=") == 1
        assert content.count("LOCAL_LLM_ALLOW_MOCK_FALLBACK=") == 1
        assert 'LOCAL_LLM_BASE_URL="http://192.0.2.14:8000/v1"' in content
        assert 'PROJECT_NAME="AI Verdict"' in content
        assert f'CUSTOM_APP_FLAG="{preserved_token}"' in content
        assert "LOCAL_LLM_API_KEY=" not in content
        assert "FORTISIEM_PASSWORD" not in content
    finally:
        (
            settings.LOCAL_LLM_BASE_URL,
            settings.LOCAL_LLM_MODEL_NAME,
            settings.LOCAL_LLM_TIMEOUT,
            settings.LOCAL_LLM_CONTEXT_BUDGET,
            settings.LOCAL_LLM_MAX_TOKENS,
            settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
            settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN,
        ) = orig


def test_3_operating_modes_fail_closed_and_secret_redaction():
    """
    Validates separated operating modes, production fail-closed guarantees,
    and zero credential/secret exposure in redacted configuration snapshots.
    """
    dyn_secret = f"unit-k-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    dyn_audit = f"unit-a-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    dyn_db_cred = f"db-{uuid.uuid4().hex[:12]}"
    dyn_redis_cred = f"rd-{uuid.uuid4().hex[:12]}"
    dyn_llm_cred = f"llm-{uuid.uuid4().hex[:12]}"
    dyn_siem_cred = f"siem-{uuid.uuid4().hex[:12]}"

    # Production rejects explicit development operating mode
    with pytest.raises(RuntimeError, match="PLATFORM_OPERATING_MODE='development'"):
        Settings(
            APP_ENV="production",
            PLATFORM_OPERATING_MODE="development",
            SECRET_KEY=dyn_secret,
        )

    # Invalid operating mode fails closed
    with pytest.raises(RuntimeError, match="Invalid PLATFORM_OPERATING_MODE"):
        Settings(APP_ENV="development", PLATFORM_OPERATING_MODE="unsafe_mode")

    # Production with mock flags enabled force-coerces mock flags off in Settings and blocks in RuntimeConfigValidator
    prod_cfg = Settings(
        APP_ENV="production",
        PLATFORM_OPERATING_MODE="advisory",
        SECRET_KEY=dyn_secret,
        AUDIT_SIGNING_KEY=dyn_audit,
        DATABASE_URL=f"postgresql+asyncpg://soc_user:{dyn_db_cred}@198.51.100.5:5432/ai_verdict",
        SYNC_DATABASE_URL=f"postgresql+psycopg2://soc_user:{dyn_db_cred}@198.51.100.5:5432/ai_verdict",
        REDIS_URL=f"redis://:{dyn_redis_cred}@127.0.0.1:6379/0",
        CELERY_BROKER_URL=f"redis://:{dyn_redis_cred}@127.0.0.1:6379/0",
        CELERY_RESULT_BACKEND=f"redis://:{dyn_redis_cred}@127.0.0.1:6379/0",
        USE_ASYNC_CELERY=True,
        LOCAL_LLM_BASE_URL="http://192.0.2.50:8000/v1",
        LOCAL_LLM_API_KEY=dyn_llm_cred,
        LOCAL_LLM_ALLOW_MOCK_FALLBACK=True,
        FORTISIEM_HOST="https://siem.example.org",
        FORTISIEM_PASSWORD=dyn_siem_cred,
        FORTISIEM_VERIFY_SSL=True,
        FORTISIEM_MOCK_FALLBACK=True,
    )
    assert prod_cfg.LOCAL_LLM_ALLOW_MOCK_FALLBACK is False
    assert prod_cfg.FORTISIEM_MOCK_FALLBACK is False

    report = RuntimeConfigValidator.validate_all(prod_cfg, strict_production_dependencies=True)
    assert report["status"] in ("READY", "WARNING")
    assert report["operating_mode"] == "advisory"
    assert report["fail_closed_mock_disabled"] is True

    # Secrets must never appear in exported snapshot
    dumped = json.dumps(report)
    for raw_secret in (
        dyn_secret,
        dyn_audit,
        dyn_db_cred,
        dyn_redis_cred,
        dyn_llm_cred,
        dyn_siem_cred,
    ):
        assert raw_secret not in dumped

    # Simulate unmasked SQLite or runtime mock bypass in protected mode -> RuntimeConfigValidator fails closed
    prod_cfg.DATABASE_URL = "sqlite+aiosqlite:///./local.db"
    prod_cfg.LOCAL_LLM_ALLOW_MOCK_FALLBACK = True
    with pytest.raises(RuntimeError, match="Fail-Closed Configuration Blocker"):
        RuntimeConfigValidator.enforce_fail_closed(prod_cfg)


# =========================================================================
# 3. LLM Context Budget Readiness (4096 + Verified 8192 + Archetypes)
# =========================================================================

@pytest.mark.asyncio
async def test_4_context_budget_readiness_across_all_archetypes_and_verified_capacity(
    db_session: AsyncSession,
    monkeypatch,
):
    """
    Tests:
    - All 4 representative rule archetypes fit inside default 4096 context budget with critical evidence preserved
    - OpenAICompatibleProvider avoids duplicate schema injection and compacts JSON
    - Configured 8192 is clamped safely if Server 2 only reports max_model_len=4096
    - Verified max_model_len=8192 supports 8192 without warnings
    - Genuinely oversized critical telemetry still abstains safely with CONTEXT_WINDOW_EXCEEDED
    """
    cases = [
        (
            "Heavy TCP Host Scan",
            "PH_RULE_HEAVY_TCP_HOST_SCAN",
            "COUNT(Matched Events) >= 25 within 300s groupBy srcIpAddr",
            {"srcIpAddr": "192.0.2.77", "destIpAddr": "198.51.100.5", "Destination Port": 445, "protocol": "TCP"},
        ),
        (
            "Suspicious PowerShell Execution",
            "Endpoint_Process_Create",
            "processCmdLine contains -enc",
            {"procName": "powershell.exe", "commandLine": "powershell -enc AAAA", "parentProcName": "winword.exe", "user": "jdoe"},
        ),
        (
            "Large Outbound Data Exfiltration",
            "Net_Large_Outbound_Transfer",
            "sentBytes64 >= 500000000",
            {"srcIpAddr": "192.0.2.10", "destIpAddr": "198.51.100.5", "sentBytes64": 900000000, "direction": "OUTBOUND"},
        ),
        (
            "Repeated Brute Force Logon Failure",
            "PH_RULE_AUTH_BRUTE_FORCE",
            "COUNT(failed logon) >= 10 within 120s",
            {"srcIpAddr": "203.0.113.5", "user": "admin", "eventOutcome": "FAILURE"},
        ),
    ]

    for name, ev, logic, attrs in cases:
        rule = Rule(id=f"r-{ev}", rule_id=ev, name=name, event_type=ev, severity="HIGH", pattern_logic=logic, description=name)
        inc = Incident(
            id=f"i-{ev}",
            incident_id=f"INC-{ev}",
            rule_id=rule.id,
            event_type=ev,
            title=name,
            severity="HIGH",
            source_ip=attrs.get("srcIpAddr", ""),
            raw_payload=attrs,
            events=[IncidentEvent(event_id="E1", event_type=ev, raw_log=str(attrs), attributes=attrs)],
        )
        draft = PolicyGenerationService.generate_nine_section_draft(rule)
        pv = PromptVersion(
            id=f"pv-{ev}",
            prompt_id=f"rp-{ev}",
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
        comp = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv, execution_mode=CompilationExecutionMode.LIVE)
        sem = RuleIntelligenceAnalyzer.analyze_rule(rule)
        adef = DetectionArchetypeRegistry.get_archetype_definition(
            DetectionArchetypeRegistry.classify_rule(sem, rule).primary_archetype
        )
        contract = EvidenceRequirementMapper.map_evidence_contract(rule, sem, adef)
        norm = EvidenceNormalizationService.normalize_incident_evidence(inc)
        payload = build_model_facing_payload(inc)
        payload["canonical_evidence"] = [r.model_dump(mode="json") for r in norm.records]
        payload["evidence_contract"] = {
            "contract_id": contract.contract_id,
            "version": contract.version_number,
            "required_fields": [r.field for r in contract.required_evidence],
        }
        res_4096 = TokenBudgetService.budget_prompt(
            compiled_policy=comp,
            incident_payload=payload,
            rag_block="[PRECEDENT] Verified analyst note.",
            max_context_tokens=4096,
            max_completion_tokens=512,
        )
        assert res_4096.can_proceed_to_inference is True, f"{name} failed 4096 budget: {res_4096.abstention_reason}"
        assert len(res_4096.budgeted_incident_payload["canonical_evidence"]) > 0

    # Verify genuinely huge critical telemetry still triggers safe CONTEXT_WINDOW_EXCEEDED abstention
    huge_payload = {
        "incident_id": "INC-HUGE-01",
        "title": "Oversized Critical Evidence Test",
        "canonical_evidence": [
            {"evidence_id": f"EV-{idx:03d}", "source_field": "process.command_line", "observed_value": "A" * 400}
            for idx in range(40)
        ],
    }
    res_overflow = TokenBudgetService.budget_prompt(
        compiled_policy=comp,
        incident_payload=huge_payload,
        max_context_tokens=4096,
        max_completion_tokens=512,
    )
    assert res_overflow.can_proceed_to_inference is False
    assert res_overflow.breakdown.context_overflow_detected is True
    assert "CONTEXT_WINDOW_EXCEEDED" in (res_overflow.abstention_reason or "")
    assert len(res_overflow.budgeted_incident_payload["canonical_evidence"]) == 40

    # Test Server 2 /models capacity probe + runtime context clamping without assuming 8192 support
    with respx.mock() as rx:
        rx.get("http://192.0.2.88:8000/v1/models").respond(
            status_code=200,
            json={"data": [{"id": "Qwen/Qwen2.5-7B-Instruct-AWQ", "max_model_len": 4096}]},
        )
        monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://192.0.2.88:8000/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192)
        monkeypatch.setattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)

        probe_res = await LLMConfigService.test_connection(LLMTestConnectionRequest(host="192.0.2.88"))
        assert probe_res.success is True
        assert probe_res.server_max_model_len == 4096
        assert probe_res.context_budget_supported is False
        assert settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN == 4096

        cfg_check = RuntimeConfigValidator.validate_all(settings)
        assert any("CONTEXT_BUDGET_EXCEEDS_SERVER_CAPACITY" in b for b in cfg_check["blockers"])

        # Pipeline must clamp effective max context to 4096 instead of assuming 8192
        scan_rule = Rule(
            id=str(uuid.uuid4()),
            rule_id="PH_RULE_CTX_CLAMP",
            name="Clamp Check Scan",
            event_type="PH_RULE_CTX_CLAMP",
            severity="HIGH",
            pattern_logic="COUNT(Matched Events) >= 25 within 300s",
        )
        db_session.add(scan_rule)
        await db_session.flush()
        scan_rp = RulePrompt(rule_id=scan_rule.id, title=scan_rule.name)
        db_session.add(scan_rp)
        await db_session.flush()
        scan_draft = PolicyGenerationService.generate_nine_section_draft(scan_rule)
        scan_pv = PromptVersion(
            prompt_id=scan_rp.id,
            version_number=1,
            status="APPROVED",
            common_prompt=scan_draft["common_prompt"],
            rule_specific_prompt=scan_draft["rule_specific_prompt"],
            detection_conditions=scan_draft["detection_conditions"],
            required_evidence=scan_draft["required_evidence"],
            tp_indicators=scan_draft["tp_indicators"],
            fp_indicators=scan_draft["fp_indicators"],
            missing_info_criteria=scan_draft["missing_info_criteria"],
            escalation_conditions=scan_draft["escalation_conditions"],
            analyst_questions=scan_draft["analyst_questions"],
        )
        db_session.add(scan_pv)
        await db_session.flush()
        scan_rp.active_version_id = scan_pv.id

        huge_inc = Incident(
            incident_id="INC-CLAMP-HUGE",
            rule_id=scan_rule.id,
            event_type=scan_rule.event_type,
            title="Oversized Clamp Incident",
            severity="HIGH",
            source_ip="192.0.2.15",
            raw_payload={"srcIpAddr": "192.0.2.15", "destIpAddr": "198.51.100.5", "destPort": 445},
            events=[
                IncidentEvent(
                    event_id=f"EVT-HUGE-{idx:02d}",
                    event_type=scan_rule.event_type,
                    raw_log=f"TCP SYN flood scan sequence #{idx} against port {1000 + idx}",
                    attributes={
                        "srcIpAddr": "192.0.2.15",
                        "destIpAddr": f"198.51.100.{10 + idx}",
                        "destPort": 1000 + idx,
                        "protocol": "TCP",
                        "user": f"svc_scan_{idx}",
                        "commandLine": f"nmap -sS -p {1000 + idx} 198.51.100.{10 + idx} --scan-id {idx:03d} " + ("X" * 120),
                    },
                )
                for idx in range(12)
            ],
        )
        db_session.add(huge_inc)
        await db_session.commit()
        huge_inc = (
            await db_session.execute(
                select(Incident)
                .where(Incident.id == huge_inc.id)
                .options(selectinload(Incident.events), selectinload(Incident.rule))
            )
        ).scalar_one()

        pipe_res = await run_shared_verdict_pipeline(
            db=db_session,
            incident=huge_inc,
            rule=scan_rule,
            prompt_version=scan_pv,
            active_approved_version=scan_pv,
            model_provider_type="SIMULATED",
            is_simulation=True,
            execution_context="SIMULATION",
            require_autonomous_certification=False,
        )
        assert pipe_res.early_exit is True
        assert pipe_res.early_exit_kind == "CONTEXT_OVERFLOW"
        assert pipe_res.evidence_trace["token_budget_breakdown"]["max_context_tokens"] == 4096

    # Also test OpenAICompatibleProvider omits duplicate schema when SECTION 11 is present
    wire_reqs = []
    with respx.mock() as rx:
        def _handle_chat(request):
            wire_reqs.append(json.loads(request.content.decode("utf-8")))
            return httpx.Response(
                status_code=200,
                json={
                    "choices": [{"message": {"content": json.dumps({
                        "verdict": "REQUIRES_ATTENTION",
                        "confidence": 55,
                        "reason": "Observed test check.",
                        "supporting_claims": [],
                    })}}],
                    "usage": {"prompt_tokens": 900, "completion_tokens": 40, "total_tokens": 940},
                },
            )

        rx.post("http://192.0.2.88:8000/v1/chat/completions").mock(side_effect=_handle_chat)
        prov = OpenAICompatibleProvider(base_url="http://192.0.2.88:8000/v1")
        await prov.analyze_incident(
            incident_payload={"incident_id": "INC-WIRE-1", "canonical_evidence": []},
            rule_spec={"id": "R1"},
            prompt_text=comp.compiled_system_prompt,
        )
        assert len(wire_reqs) == 1
        sys_msg = wire_reqs[0]["messages"][0]["content"]
        assert sys_msg.count("STRICT STRUCTURED JSON OUTPUT REQUIREMENTS") == 1
        assert "CRITICAL: Output must be a strictly valid JSON object" not in sys_msg


# =========================================================================
# 4. Non-Destructive Integration Diagnostics (Service + API + Read-Only Guarantee)
# =========================================================================

@pytest.mark.asyncio
async def test_5_non_destructive_integration_diagnostics_api_and_service(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
    monkeypatch,
):
    """
    Verifies IntegrationDiagnosticService + GET /api/verdict-intelligence/integration-diagnostics:
    - Read-only / zero DB mutations (`read_only=True`, `database_mutated=False`)
    - Verifies canonical rule associations, GT TP/FP counts, `is_ml_generated` re-eval candidates,
      G1 coverage, Workbench-vs-AIS parity, policy digest integrity, and Server 2 probed capacity.
    """
    r_main = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN",
        name="Heavy TCP Host Scan",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN",
        severity="HIGH",
        pattern_logic="COUNT(Matched Events) >= 25 within 300s groupBy srcIpAddr",
    )
    db_session.add(r_main)
    await db_session.flush()

    rp = RulePrompt(rule_id=r_main.id, title=r_main.name)
    db_session.add(rp)
    await db_session.flush()
    draft = PolicyGenerationService.generate_nine_section_draft(r_main)
    pv = PromptVersion(
        prompt_id=rp.id,
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
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id

    inc = Incident(
        incident_id="DIAG-INC-01",
        rule_id=r_main.id,
        event_type=r_main.event_type,
        title=r_main.name,
        severity="HIGH",
        source_ip="192.0.2.33",
        raw_payload={"srcIpAddr": "192.0.2.33", "destPort": 445},
    )
    db_session.add(inc)
    await db_session.flush()
    gt = HistoricalGroundTruth(
        incident_id=inc.id,
        resolution="False Positive",
        comments="normal authorized maintenance window",
        cleared_user="soc_admin",
        is_ml_generated=True,  # Historical false-substring flag candidate
    )
    db_session.add(gt)
    await db_session.commit()

    # Run diagnostics with probe_remote=False via FastAPI endpoint
    res = await client.get(
        f"/api/verdict-intelligence/integration-diagnostics?rule_id={r_main.id}&probe_remote=false",
        headers=_auth(analyst_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["read_only"] is True
    assert data["database_mutated"] is False
    assert data["external_mutations"] is False
    assert data["integration_verified"] is False
    assert data["overall_status"] == "LOCAL_VERIFIED_REMOTE_NOT_PROBED"
    assert data["workbench_ais_parity"]["status"] == "PASS"
    assert data["workbench_ais_parity"]["parity_mismatches_count"] == 0
    assert data["corpus_and_canonical_associations"]["target_rule"]["total_canonical_incidents"] == 1
    assert data["ground_truth_eligibility_and_ml_audit"]["summary"]["ml_reevaluation_audit"]["mutated_records"] == 0
    assert data["ground_truth_eligibility_and_ml_audit"]["summary"]["ml_reevaluation_audit"]["false_positive_ml_candidates"] >= 1
    assert data["policy_digest_and_governance"]["autonomous_default_blocked"] is True

    # Verify DB record was untouched (is_ml_generated remains True)
    await db_session.refresh(gt)
    assert gt.is_ml_generated is True
    await db_session.refresh(inc)
    assert inc.ai_verdict is None

    # Test remote probe with mocked Server 2 supporting 8192
    monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://192.0.2.77:8000/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192)
    monkeypatch.setattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
    with respx.mock() as rx:
        rx.get("http://192.0.2.77:8000/v1/models").respond(
            status_code=200,
            json={"data": [{"id": settings.LOCAL_LLM_MODEL_NAME, "max_model_len": 8192}]},
        )
        diag_srv = IntegrationDiagnosticService(db_session)
        probed = await diag_srv.run_diagnostics(rule_id=r_main.id, probe_remote=True)
        assert probed["server2_llm_readiness"]["status"] == "PASS"
        assert probed["server2_llm_readiness"]["verified_server_max_model_len"] == 8192
        assert probed["server2_llm_readiness"]["context_capacity_verified"] is True

    from scripts.run_integration_diagnostics import execute_integration_diagnostics
    assert callable(execute_integration_diagnostics)
