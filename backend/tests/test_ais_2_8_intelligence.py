import json
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.analyst_feedback import AnalystVerdictReview, BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.schemas.evidence_contract import EvidenceFieldRequirement, RuleEvidenceContract
from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner
from app.services.ais28_policy_candidates import get_experimental_candidate_policy
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness
from app.services.evidence_intelligence_service import EvidenceIntelligenceEngine, RuleDefinitionBuilder
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.llm_config_service import LLMConfigService
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider, robust_parse_model_verdict_json
from app.services.system_monitor_service import InferenceHealthMonitor
from app.services.tokenizer_service import ModelTokenizerService


def test_ws1_ws3_qwen3_profile_tokenizer_and_think_stripping():
    prof = LLMConfigService.get_model_profile("Qwen/Qwen3-14B-AWQ")
    assert prof["max_context_tokens"] == 8192
    assert prof["reserved_output_tokens"] == 768
    assert prof["target_input_budget"] == 7424

    tokens_qwen3 = ModelTokenizerService.count_wire_prompt_tokens("System prompt", "User JSON payload", "Qwen/Qwen3-14B-AWQ")
    tokens_qwen25 = ModelTokenizerService.count_wire_prompt_tokens("System prompt", "User JSON payload", "Qwen/Qwen2.5-7B-Instruct-AWQ")
    assert tokens_qwen3 > tokens_qwen25

    raw_with_think = '<think>\nreasoning step\n</think>\n{"verdict":"TRUE_POSITIVE","confidence":88,"reason":"Unauthorized UltraViewer","supporting_claims":[]}'
    parsed, err = robust_parse_model_verdict_json(raw_with_think)
    assert err is None
    assert parsed is not None
    assert parsed["verdict"] == "TRUE_POSITIVE"
    assert parsed["confidence"] == 88


@pytest.mark.asyncio
@respx.mock
async def test_ws1_test_connection_distinguishes_model_mismatch(client: AsyncClient, admin_token: str, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ")
    respx.get("http://192.0.2.88:8000/v1/models").respond(
        status_code=200,
        json={"data": [{"id": "Qwen/Qwen2.5-7B-Instruct-AWQ", "max_model_len": 8192}]},
    )
    res = await client.post(
        "/api/llm/test-connection",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"host": "192.0.2.88", "port": 8000, "timeout": 2.0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["endpoint_reachable"] is True
    assert data["runtime_healthy"] is True
    assert data["configured_model_available"] is False
    assert data["model_mismatch"] is True
    assert data["runtime_status_detail"] == "MODEL_MISMATCH"


def test_ws2_prometheus_parser_no_synthetic_vram_and_reads_real_dcgm():
    mon = InferenceHealthMonitor(db=None)
    vllm_only = (
        "vllm:num_requests_running 1\n"
        "vllm:num_requests_waiting 2\n"
        "vllm:gpu_cache_usage_factor 0.35\n"
        "vllm:avg_generation_throughput_tok_per_s 24.6\n"
    )
    parsed_vllm = mon._parse_vllm_metrics(vllm_only)
    assert parsed_vllm["active_requests"] == 1
    assert parsed_vllm["waiting_requests"] == 2
    assert parsed_vllm["kv_cache_usage_percent"] == 35.0
    assert parsed_vllm.get("hardware_telemetry_present") is None

    dcgm_text = (
        "DCGM_FI_DEV_GPU_UTIL 42.5\n"
        "DCGM_FI_DEV_GPU_TEMP 58\n"
        "DCGM_FI_DEV_FB_USED 13295\n"
        "DCGM_FI_DEV_FB_FREE 2065\n"
    )
    parsed_hw = mon._parse_vllm_metrics(dcgm_text)
    assert parsed_hw["hardware_telemetry_present"] is True
    assert parsed_hw["hw_gpu_percent"] == 42.5
    assert parsed_hw["hw_temp_c"] == 58.0
    assert 14.9 <= parsed_hw["hw_vram_total_gb"] <= 15.1


def test_ws5_ws6_ws9_ws14_rule_evidence_intelligence_and_validator():
    rule = Rule(
        id="cs-rule-uuid",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        name="Crowdstrike: Suspicious Activity",
        event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        severity="MEDIUM",
        status="ACTIVE",
        data_source="CrowdStrike Falcon",
        pattern_logic='Event Type IN EppDetectionSummaryEvent AND File Name CONTAINS UltraViewer',
        raw_rule_text='Name: Crowdstrike: Suspicious Activity\nPattern:\nEvent Type IN EppDetectionSummaryEvent',
    )
    payload = {
        "incident_id": "132474210",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "source_ip": "192.168.10.25",
        "reporting_device": "PC-TSI-DC",
        "events": [
            {
                "event_id": "EVT-1",
                "event_type": "EppDetectionSummaryEvent",
                "attributes": {
                    "File Name": "UltraViewer_Service.exe",
                    "Command Line": '"C:\\Program Files (x86)\\UltraViewer\\UltraViewer_Service.exe"',
                    "Host Name": "PC-TSI-DC",
                    "User": "SYSTEM",
                    "srcIpAddr": "192.168.10.25",
                    "destIpAddr": "104.26.10.15",
                },
            }
        ],
    }

    class _IncAdapter:
        def __init__(self, d):
            self.id = d["incident_id"]
            self.incident_id = d["incident_id"]
            self.title = "Crowdstrike: Suspicious Activity"
            self.description = ""
            self.event_type = d["event_type"]
            self.severity = "MEDIUM"
            self.category = ""
            self.source_ip = d["source_ip"]
            self.reporting_device = d["reporting_device"]
            self.reporting_ip = ""
            self.raw_payload = d
            self.events = []

    norm = EvidenceNormalizationService.normalize_incident_evidence(_IncAdapter(payload))
    intel = EvidenceIntelligenceEngine.enrich_incident_evidence(payload, norm.records)
    assert intel["network_classification"]["source_ip"]["classification"] == "RFC1918_PRIVATE"
    assert intel["network_classification"]["destination_ip"]["classification"] == "PUBLIC_ROUTABLE"
    assert intel["endpoint_process_classification"]["path_classification"]["path_zone"] == "PROGRAM_FILES"
    assert intel["endpoint_process_classification"]["digital_signature_status"] == "NOT_REPORTED_IN_TELEMETRY"
    assert intel["endpoint_process_classification"]["command_line_present"] is True

    rule_spec = RuleDefinitionBuilder.build_complete_rule_spec(rule, norm.records, payload)
    assert rule_spec["rule_definition_completeness"] == "COMPLETE"
    assert any(p["status"] == "MATCHED" for p in rule_spec["predicate_evaluations"])

    # Validator catches path & signature & IP contradictions from AIS 2.7
    ev_ids = [r.evidence_id for r in norm.records[:2]]
    contract = EmpiricalBenchmarkHarness._create_rule_contract("PH_RULE_CS_SUSPICIOUS_ACTIVITY", rule.name)
    preflight = EvidencePreflightValidator.validate_preflight("132474210", contract, norm)
    bad_out = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 85.0,
        "reason": (
            "UltraViewer_Service.exe executed from an unusual temporary directory and is an unsigned binary "
            "with missing command line, contacting internal IP 104.26.10.15."
        ),
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": "UltraViewer_Service.exe",
                "claim_text": "UltraViewer_Service.exe observed on PC-TSI-DC",
                "cited_evidence_ids": ev_ids,
            }
        ],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("132474210", bad_out, norm)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id="132474210",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=bad_out["reason"],
    )
    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert "PATH_MISCLASSIFICATION" in val_res.validation_reason_codes
    assert "UNSUPPORTED_SIGNATURE_CLAIM" in val_res.validation_reason_codes
    assert "IP_CLASSIFICATION_CONTRADICTION" in val_res.validation_reason_codes

    # Experimental candidate policies remain isolated candidates with proper SASE fields
    cs_cand = get_experimental_candidate_policy("PH_RULE_CS_SUSPICIOUS_ACTIVITY")
    prisma_cand = get_experimental_candidate_policy("PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE")
    assert cs_cand.status == "EXPERIMENTAL_CANDIDATE"
    assert prisma_cand.status == "EXPERIMENTAL_CANDIDATE"
    assert "file.name" in prisma_cand.required_evidence
    assert "process.file_name" not in prisma_cand.required_evidence


@pytest.mark.asyncio
async def test_ws5_ws10_runner_equal_rule_parity_and_evidence_intel_without_leakage():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        rule = Rule(
            id="rule-prisma-uuid",
            rule_id="PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
            name="Prisma SASE: Suspicious File Threat Detection",
            event_type="PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
            severity="MEDIUM",
            status="ACTIVE",
            pattern_logic="Event Type IN PaloAlto_Prisma_Traffic AND File Name IS NOT NULL",
            raw_rule_text="Pattern:\nEvent Type IN PaloAlto_Prisma_Traffic",
        )
        db.add(rule)
        rp = RulePrompt(id="rp-prisma", rule_id=rule.id, active_version_id="pv-prisma-v1")
        db.add(rp)
        pv = PromptVersion(
            id="pv-prisma-v1",
            prompt_id=rp.id,
            version_number=1,
            status="APPROVED",
            common_prompt="Approved policy",
            rule_specific_prompt="Check file threat",
            detection_conditions="Prisma SASE download",
            required_evidence="file.name, network.source_ip",
            tp_indicators="Confirmed malware",
            fp_indicators="Verified web static asset",
            missing_info_criteria="Missing hash",
            escalation_conditions="Malware payload",
            analyst_questions=[],
        )
        db.add(pv)
        inc = Incident(
            id="inc-prisma-1",
            incident_id="132596403",
            rule_id=rule.id,
            title="Prisma SASE: Suspicious File Threat Detection",
            event_type="PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
            severity="MEDIUM",
            customer="Tosoh",
            source_ip="10.20.30.40",
            ai_verdict={"verdict": "TRUE_POSITIVE", "reason": "SECRET_AI_VERDICT"},
        )
        db.add(inc)
        db.add(
            IncidentEvent(
                incident_id=inc.id,
                event_id="evt-p1",
                event_type="PaloAlto_Prisma_Traffic",
                raw_log="filename=setup_payload.exe url=https://cdn.example.invalid/setup_payload.exe",
                attributes={
                    "File Name": "setup_payload.exe",
                    "srcIpAddr": "10.20.30.40",
                    "destIpAddr": "198.51.100.42",
                    "requestUrl": "https://cdn.example.invalid/setup_payload.exe",
                },
            )
        )
        db.add(HistoricalGroundTruth(incident_id=inc.id, resolution="True Positive", cleared_reason="SECRET_CLEAR"))
        db.add(
            AnalystVerdictReview(
                incident_id=inc.id,
                rule_id=rule.id,
                reviewer_id="admin",
                analyst_verdict="INCONCLUSIVE",
                analyst_notes="SECRET_GT2_NOTE",
                review_mode="BENCHMARK_CERTIFICATION",
                is_locked=True,
                is_draft=False,
            )
        )
        cohort = BenchmarkCohort(
            id="cohort-28-1",
            cohort_key="AIS_2_6E_FROZEN_20",
            name="Frozen 20",
            version="2.6e",
            is_frozen=True,
            required_reviewers=2,
            excluded_from_learning=True,
        )
        db.add(cohort)
        await db.flush()
        db.add(
            BenchmarkCohortItem(
                cohort_id=cohort.id,
                incident_db_id=inc.id,
                fortisiem_incident_id="132596403",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                customer="Tosoh",
                raw_evidence_sha256="a" * 64,
                canonical_evidence_sha256="b" * 64,
                rule_definition_sha256="c" * 64,
                is_priority=True,
                priority_rank=1,
            )
        )
        await db.commit()

        captured = []

        async def _fake_transport(*, system_instruction, user_content, model_name, max_tokens, temperature):
            captured.append((system_instruction, user_content))
            return {
                "ok": True,
                "http_status": 200,
                "request_timestamp_utc": "2026-11-26T00:00:00Z",
                "response_timestamp_utc": "2026-11-26T00:00:01Z",
                "latency_ms": 120.0,
                "outbound_payload": {},
                "http_body_sha256": "x" * 64,
                "vllm_response_id": "cmpl-test",
                "vllm_created": 1,
                "model_returned": model_name,
                "finish_reason": "stop",
                "prompt_tokens": 500,
                "completion_tokens": 60,
                "total_tokens": 560,
                "raw_response_text": json.dumps({
                    "incident_id": "132596403",
                    "verdict": "REQUIRES_ATTENTION",
                    "confidence": 65,
                    "reason": "Executable downloaded over HTTPS with download-only network telemetry and no hash verdict.",
                    "supporting_claims": [],
                    "supporting_evidence": ["file.name: setup_payload.exe"],
                    "contradictory_evidence": [],
                    "missing_evidence": ["file.hash", "endpoint execution telemetry"],
                    "analyst_questions": ["Check gateway threat logs"],
                }),
                "raw_response_sha256": "y" * 64,
                "raw_vllm_envelope": {},
            }

        res = await AIS27BenchmarkRunner.run_single_incident_three_mode(
            db=db,
            cohort_key="AIS_2_6E_FROZEN_20",
            fortisiem_incident_id="132596403",
            transport_override=_fake_transport,
            neutral_prompt_version="V2",
            include_complete_rule_def=True,
            include_evidence_intelligence=True,
            use_candidate_policy=True,
        )

        assert len(captured) == 2
        # Mode A and Mode B receive IDENTICAL user_content containing complete rule logic & evidence intelligence
        assert captured[0][1] == captured[1][1]
        assert "SECRET_GT2_NOTE" not in captured[0][1]
        assert "SECRET_CLEAR" not in captured[0][1]
        assert "SECRET_AI_VERDICT" not in captured[0][1]
        assert "PaloAlto_Prisma_Traffic" in captured[0][1]
        assert "evidence_intelligence" in captured[0][1]
        assert "AIS 2.8 Experimental Candidate Policy" in captured[1][0]
        assert res["experiment_config"]["use_candidate_policy"] is True
        assert res["mode_a"]["validated"]["validated_verdict"] == "REQUIRES_ATTENTION"
        assert res["mode_c"]["validated_verdict"] == "REQUIRES_ATTENTION"
    await engine.dispose()
