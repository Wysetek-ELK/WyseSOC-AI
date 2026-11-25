import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.analyst_feedback import AnalystVerdictReview, BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner


@pytest.mark.asyncio
async def test_ais27_runner_three_mode_isolation_and_layer_separation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        rule = Rule(
            id="rule-cs-pg-uuid",
            rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
            name="Crowdstrike: Suspicious Activity",
            event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
            severity="MEDIUM",
            status="ACTIVE",
            pattern_logic="Event Type IN EppDetectionSummaryEvent",
        )
        db.add(rule)
        rp = RulePrompt(
            id="rp-cs-pg",
            rule_id=rule.id,
            active_version_id="pv-cs-v3",
        )
        db.add(rp)
        pv = PromptVersion(
            id="pv-cs-v3",
            prompt_id=rp.id,
            version_number=3,
            status="APPROVED",
            common_prompt="Policy baseline v3",
            rule_specific_prompt="Investigate CrowdStrike suspicious activity",
            detection_conditions="EppDetectionSummaryEvent",
            required_evidence="process.file_name, endpoint.hostname",
            tp_indicators="Unauthorized remote tool",
            fp_indicators="Approved IT change ticket",
            missing_info_criteria="Missing command line",
            escalation_conditions="Ransomware",
            analyst_questions=["Is binary signed?"],
        )
        db.add(pv)

        inc = Incident(
            id="inc-db-uuid-1",
            incident_id="132474210",
            rule_id=rule.id,
            title="Crowdstrike: Suspicious Activity",
            event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
            severity="MEDIUM",
            customer="Tosoh",
            reporting_device="PC-TSI-DC",
            ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "SECRET_AI_VERDICT"},
        )
        db.add(inc)
        db.add(
            IncidentEvent(
                incident_id=inc.id,
                event_id="evt-1",
                event_type="EppDetectionSummaryEvent",
                raw_log='{"FileName":"UltraViewer_Service.exe","CommandLine":"UltraViewer_Service.exe"}',
                attributes={
                    "File Name": "UltraViewer_Service.exe",
                    "Command": '"C:\\Program Files (x86)\\UltraViewer\\UltraViewer_Service.exe"',
                    "Host Name": "PC-TSI-DC",
                    "User": "SYSTEM",
                },
            )
        )
        db.add(
            HistoricalGroundTruth(
                incident_id=inc.id,
                resolution="False Positive",
                cleared_reason="SECRET_HISTORICAL_CLOSURE_REASON",
            )
        )
        db.add(
            AnalystVerdictReview(
                incident_id=inc.id,
                rule_id=rule.id,
                reviewer_id="admin",
                analyst_verdict="TRUE_POSITIVE",
                analyst_notes="SECRET_GT2_HUMAN_RATIONALE",
                review_mode="BENCHMARK_CERTIFICATION",
                is_locked=True,
                is_draft=False,
            )
        )
        cohort = BenchmarkCohort(
            id="cohort-1",
            cohort_key="AIS_2_6E_FROZEN_20",
            name="Frozen 20",
            version="2.6e",
            is_frozen=True,
            required_reviewers=2,
            excluded_from_learning=True,
        )
        db.add(cohort)
        db.add(
            BenchmarkCohortItem(
                cohort_id=cohort.id,
                incident_db_id=inc.id,
                fortisiem_incident_id="132474210",
                rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
                rule_name="Crowdstrike: Suspicious Activity",
                customer="Tosoh",
                is_priority=True,
                priority_rank=1,
            )
        )
        await db.commit()

        captured_prompts = []

        async def fake_transport(*, system_instruction, user_content, model_name, max_tokens, temperature):
            captured_prompts.append((system_instruction, user_content))
            idx = len(captured_prompts)
            if idx == 1:
                reply = json.dumps({
                    "incident_id": "132474210",
                    "rule_id": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
                    "verdict": "REQUIRES_ATTENTION",
                    "confidence": 55.0,
                    "confidence_scale": "PERCENT_0_100",
                    "reason": "UltraViewer observed without IT change authorization.",
                    "supporting_claims": [],
                    "supporting_evidence": [],
                    "contradictory_evidence": [],
                    "missing_evidence": ["IT authorization"],
                    "analyst_questions": [],
                })
            else:
                reply = json.dumps({
                    "incident_id": "132474210",
                    "rule_id": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
                    "verdict": "FALSE_POSITIVE",
                    "confidence": 85.0,
                    "confidence_scale": "PERCENT_0_100",
                    "reason": "Claiming approved enterprise deployment tool without evidence.",
                    "supporting_claims": [],
                    "supporting_evidence": [],
                    "contradictory_evidence": [],
                    "missing_evidence": [],
                    "analyst_questions": [],
                })
            return {
                "ok": True,
                "http_status": 200,
                "request_timestamp_utc": "2026-11-25T05:00:00Z",
                "response_timestamp_utc": "2026-11-25T05:00:01Z",
                "latency_ms": 1000.0,
                "outbound_payload": {"model": model_name},
                "http_body_sha256": f"req-{idx}",
                "vllm_response_id": f"cmpl-test-{idx}",
                "vllm_created": 1795580000,
                "model_returned": model_name,
                "finish_reason": "stop",
                "prompt_tokens": 3000 + idx * 100,
                "completion_tokens": 90,
                "total_tokens": 3090 + idx * 100,
                "raw_response_text": reply,
                "raw_response_sha256": f"resp-{idx}",
                "raw_vllm_envelope": {"id": f"cmpl-test-{idx}"},
            }

        res = await AIS27BenchmarkRunner.run_single_incident_three_mode(
            db=db,
            cohort_key="AIS_2_6E_FROZEN_20",
            fortisiem_incident_id="132474210",
            transport_override=fake_transport,
        )

        # Exactly 2 transport calls (Mode A + Mode B; 0 for Mode C)
        assert len(captured_prompts) == 2
        for sys_p, usr_p in captured_prompts:
            combined = sys_p + "\n" + usr_p
            assert "SECRET_GT2_HUMAN_RATIONALE" not in combined
            assert "SECRET_HISTORICAL_CLOSURE_REASON" not in combined
            assert "SECRET_AI_VERDICT" not in combined

        # Policy identity came from DB (v3 pv-cs-v3)
        assert res["rule_identity"]["approved_prompt_version_id"] == "pv-cs-v3"
        assert res["rule_identity"]["approved_version_number"] == 3

        # Layer separation: Mode B raw=FALSE_POSITIVE, Mode C abstains REQUIRES_ATTENTION (empty claims)
        assert res["mode_a"]["parsed"]["verdict" if "verdict" in res["mode_a"]["parsed"] else "parsed_verdict"] == "REQUIRES_ATTENTION"
        assert res["mode_b"]["parsed"]["parsed_verdict"] == "FALSE_POSITIVE"
        assert res["mode_c"]["input_mode_b_verdict"] == "FALSE_POSITIVE"
        assert res["mode_c"]["validated_verdict"] == "REQUIRES_ATTENTION"

    await engine.dispose()
