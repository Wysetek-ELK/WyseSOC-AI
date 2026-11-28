"""
AIS 3.1 Regression & Integrity Suite:
- Exposure taxonomy (`VERIFIED_NO_DETECTED_EXPOSURE` vs `HISTORICAL_LABEL_EXISTS_BUT_MASKED` vs `CONFIRMED_EXPOSURE`)
- Dynamic vendor resolution for multi-rule cohorts (non-CS / non-Prisma)
- Frozen manifest integrity & ground-truth isolation
- Token budget audit & context window integrity
- Checkpointed idempotent benchmark execution & crash-safe resume
- Separated Raw LLM vs Validated Application verdicts & mathematically exact metrics
- RBAC enforcement on AIS 3.1 endpoints & exact wire prompt capture
"""

import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.analyst_feedback import AnalystVerdictReview, BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.learning import LearningRecord
from app.models.rule import Rule
from app.models.user import User
from app.services.ais31_benchmark_service import AIS31BenchmarkService
from app.services.ground_truth_certification_service import (
    GroundTruthCertificationService,
    _classify_item_exposure,
    _resolve_cohort_item_vendor,
)
from app.utils.security import create_access_token, get_password_hash


def test_vendor_resolution_and_exposure_taxonomy():
    assert _resolve_cohort_item_vendor("PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT") == "FortiSIEM"
    assert _resolve_cohort_item_vendor("PH_RULE_FGT_Config_Change") == "FortiGate"
    assert _resolve_cohort_item_vendor("PH_Rule_MISP_MalwareIP_Inbound") == "MISP Threat Intel"
    assert _resolve_cohort_item_vendor("PH_RULE_CS_SUSPICIOUS_ACTIVITY") == "CrowdStrike"
    assert _resolve_cohort_item_vendor("PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE") == "Prisma SASE"

    # Empty historical GT + no operational AI -> VERIFIED_NO_DETECTED_EXPOSURE
    inc_clean = Incident(id="i1", incident_id="101", title="Scan", severity="MEDIUM", customer="GDC_NOC")
    inc_clean.ground_truth = HistoricalGroundTruth(incident_id="i1", resolution="")
    st, flag, _, _ = _classify_item_exposure(
        inc=inc_clean, in_learning=False, in_other_cohort=False, has_unmasked_ai_notes=False, has_prompt_capture=False
    )
    assert st == "VERIFIED_NO_DETECTED_EXPOSURE"
    assert flag is False

    # Non-empty historical GT (masked) -> HISTORICAL_LABEL_EXISTS_BUT_MASKED
    inc_hist = Incident(id="i2", incident_id="102", title="Scan", severity="MEDIUM", customer="GDC_NOC")
    inc_hist.ground_truth = HistoricalGroundTruth(incident_id="i2", resolution="True Positive", is_ml_generated=True)
    st2, flag2, _, _ = _classify_item_exposure(
        inc=inc_hist, in_learning=False, in_other_cohort=False, has_unmasked_ai_notes=False, has_prompt_capture=False
    )
    assert st2 == "HISTORICAL_LABEL_EXISTS_BUT_MASKED"
    assert flag2 is False

    # In LearningRecord -> CONFIRMED_EXPOSURE
    st3, flag3, _, _ = _classify_item_exposure(
        inc=inc_clean, in_learning=True, in_other_cohort=False, has_unmasked_ai_notes=False, has_prompt_capture=False
    )
    assert st3 == "CONFIRMED_EXPOSURE"
    assert flag3 is True


@pytest.mark.asyncio
async def test_ais31_manifest_isolation_resume_and_separated_metrics():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        rule = Rule(
            id="rule-scan-1",
            rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
            name="Heavy TCP Host Scan On Fixed Port",
            event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
            severity="MEDIUM",
            status="ACTIVE",
            pattern_logic="Event Type = PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT AND COUNT(destIpAddr) >= 100",
        )
        db.add(rule)

        cohort = BenchmarkCohort(
            id="coh-30",
            cohort_key="AIS_3_0_INDEPENDENT_HOLDOUT_100",
            name="AIS 3.0 Holdout",
            version="3.0",
            is_frozen=True,
            required_reviewers=2,
            excluded_from_learning=True,
        )
        db.add(cohort)

        for idx, (fid, gt_v) in enumerate([("5001", "TRUE_POSITIVE"), ("5002", "FALSE_POSITIVE"), ("5003", "INCONCLUSIVE")], start=1):
            inc = Incident(
                id=f"inc-{fid}",
                incident_id=fid,
                rule_id=rule.id,
                event_type=rule.event_type,
                title=rule.name,
                severity="MEDIUM",
                customer="GDC_NOC",
                source_ip=f"172.25.24.{idx}",
                ai_verdict={"verdict": "REQUIRES_ATTENTION", "reason": "SECRET_OP_AI_LEAK"},
            )
            db.add(inc)
            db.add(
                IncidentEvent(
                    incident_id=inc.id,
                    event_id=f"evt-{fid}",
                    event_type="FortiGate-traffic-forward",
                    raw_log=f'srcip=172.25.24.{idx} dstip=8.8.4.4 dstport=443 proto=6 action="client-rst"',
                    attributes={"srcIpAddr": f"172.25.24.{idx}", "destIpAddr": "8.8.4.4", "destIpPort": "443"},
                )
            )
            db.add(
                HistoricalGroundTruth(
                    incident_id=inc.id,
                    resolution="True Positive",
                    cleared_reason="SECRET_HIST_GT_LEAK",
                )
            )
            db.add(
                AnalystVerdictReview(
                    incident_id=inc.id,
                    rule_id=rule.id,
                    reviewer_id="admin",
                    analyst_verdict=gt_v,
                    analyst_notes="SECRET_HUMAN_GT2_NOTE",
                    review_mode="BENCHMARK_CERTIFICATION",
                    is_locked=True,
                    is_draft=False,
                )
            )
            db.add(
                BenchmarkCohortItem(
                    cohort_id=cohort.id,
                    incident_db_id=inc.id,
                    fortisiem_incident_id=fid,
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    customer="GDC_NOC",
                    is_priority=False,
                    priority_rank=idx,
                    certification_status="GT2_SINGLE_REVIEW",
                )
            )
        await db.commit()

        # 1. Frozen manifest (inference domain excludes human reviews)
        inf_man = await AIS31BenchmarkService.build_frozen_manifest(db, "AIS_3_0_INDEPENDENT_HOLDOUT_100", include_ground_truth=False)
        assert "restricted_ground_truth" not in inf_man
        assert inf_man["original_population"] == 3
        assert inf_man["eligible_count"] == 3
        assert len(inf_man["manifest_sha256"]) == 64

        # 2. Token audit passes offline cleanly without needing approved PromptVersion
        tok_audit = await AIS31BenchmarkService.audit_token_budgets(db, "AIS_3_0_INDEPENDENT_HOLDOUT_100")
        assert tok_audit["total_items"] == 3
        assert tok_audit["overflow_count"] == 0
        assert tok_audit["all_fit_safely"] is True

        # 3. Simulated failing first call on 5002 to verify checkpoint + resume idempotence
        seen_calls = []

        async def test_transport(*, system_instruction, user_content, model_name, max_tokens, temperature):
            combined = system_instruction + "\n" + user_content
            assert "SECRET_OP_AI_LEAK" not in combined
            assert "SECRET_HIST_GT_LEAK" not in combined
            assert "SECRET_HUMAN_GT2_NOTE" not in combined

            fid = "5001" if '"5001"' in user_content else ("5002" if '"5002"' in user_content else "5003")
            seen_calls.append(fid)
            if fid == "5002" and seen_calls.count("5002") <= 2:
                return {"ok": False, "error_type": "HTTP_ERROR", "http_status": 503, "error_message": "transient", "latency_ms": 10.0}

            verdict_map = {"5001": "TRUE_POSITIVE", "5002": "FALSE_POSITIVE", "5003": "REQUIRES_ATTENTION"}
            reply = json.dumps({
                "incident_id": fid,
                "rule_id": "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
                "verdict": verdict_map[fid],
                "confidence": 85.0,
                "confidence_scale": "PERCENT_0_100",
                "reason": f"Observed network traffic on port 443 for {fid}.",
                "supporting_claims": [],
                "supporting_evidence": [],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
            })
            return {
                "ok": True,
                "http_status": 200,
                "request_timestamp_utc": "2026-11-28T10:00:00Z",
                "response_timestamp_utc": "2026-11-28T10:00:01Z",
                "latency_ms": 500.0,
                "vllm_response_id": f"cmpl-{fid}",
                "model_returned": "Qwen/Qwen3-14B-AWQ",
                "finish_reason": "stop",
                "prompt_tokens": 1200,
                "completion_tokens": 80,
                "total_tokens": 1280,
                "raw_response_text": reply,
                "raw_vllm_envelope": {"id": f"cmpl-{fid}"},
            }

        run = await AIS31BenchmarkService.create_or_resume_run(
            db,
            cohort_key="AIS_3_0_INDEPENDENT_HOLDOUT_100",
            run_type="CUSTOM",
            run_key="TEST-RUN-RESUME-1",
            transport_override=test_transport,
        )
        assert run.benchmark_grade == "PROVISIONAL_SINGLE_REVIEW_BENCHMARK"

        first_exec = await AIS31BenchmarkService.execute_run(db, run_id=run.id, transport_override=test_transport)
        assert first_exec["status"] == "PARTIAL"
        assert first_exec["completed_count"] == 2
        assert first_exec["failed_count"] == 1

        # Resume same run_key: 5001 & 5003 MUST NOT re-run; only 5002 executes and succeeds
        resumed_run = await AIS31BenchmarkService.create_or_resume_run(
            db,
            cohort_key="AIS_3_0_INDEPENDENT_HOLDOUT_100",
            run_type="CUSTOM",
            run_key="TEST-RUN-RESUME-1",
            transport_override=test_transport,
        )
        assert resumed_run.id == run.id
        second_exec = await AIS31BenchmarkService.execute_run(db, run_id=run.id, transport_override=test_transport)
        assert second_exec["status"] == "COMPLETED"
        assert second_exec["completed_count"] == 3
        assert second_exec["failed_count"] == 0
        assert second_exec["executed_in_call"] == 1

        # 4. Evaluate separated raw LLM vs validated application metrics
        eval_rep = await AIS31BenchmarkService.evaluate_run_against_ground_truth(db, run.id)
        assert eval_rep["raw_llm_metrics"]["conclusive_accuracy_pct"] == 100.0
        assert eval_rep["raw_llm_metrics"]["conclusive_count"] == 2
        assert eval_rep["raw_llm_metrics"]["inconclusive_count"] == 1
        # Because supporting_claims=[], validator rejects decisive TP/FP -> app conclusive=0, conclusive_accuracy=None (N/A)
        assert eval_rep["application_metrics"]["conclusive_count"] == 0
        assert eval_rep["application_metrics"]["conclusive_accuracy_pct"] is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_ais31_rbac_and_wire_prompt_access(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    analyst = User(
        username="ais31_analyst",
        email="ais31_analyst@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        role="SOC Analyst",
        is_active=True,
        customer="GDC_NOC",
    )
    db_session.add(analyst)
    await db_session.flush()
    analyst_token = create_access_token(
        data={"sub": str(analyst.id), "username": analyst.username, "role": analyst.role, "customer": analyst.customer}
    )
    await db_session.commit()

    # Unauthenticated -> 401
    r_unauth = await client.get("/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/manifest")
    assert r_unauth.status_code == 401

    # Non-admin analyst -> 403 on manifest, token-audit, and run execution
    for path, method in [
        ("/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/manifest", "GET"),
        ("/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/token-audit", "GET"),
        ("/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/runs", "POST"),
    ]:
        res = await client.request(method, path, headers={"Authorization": f"Bearer {analyst_token}"})
        assert res.status_code == 403

    # Latest summary returns graceful empty state when no run exists
    sum_res = await client.get(
        "/api/ground-truth/ais31/latest-summary?cohort_key=AIS_3_0_INDEPENDENT_HOLDOUT_100",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sum_res.status_code == 200
    assert sum_res.json()["has_run"] is False


def test_alembic_017_migration_upgrade_and_downgrade(tmp_path):
    """Verify Alembic migration 017 applies cleanly on a fresh SQLite DB."""
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect

    db_file = tmp_path / "test_mig.db"
    eng = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(eng)
    # Drop AIS 3.1 tables to test upgrade idempotently from 016 state
    with eng.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS ais31_benchmark_results")
        conn.exec_driver_sql("DROP TABLE IF EXISTS ais31_benchmark_runs")

    mig_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "017_ais31_holdout_benchmark.py"
    spec = importlib.util.spec_from_file_location("mig017", str(mig_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    from alembic import op as alembic_op
    with eng.begin() as conn:
        mc = MigrationContext.configure(conn)
        with alembic_op.Operations.context(mc):
            mod.upgrade()

    insp = inspect(eng)
    tables = set(insp.get_table_names())
    assert "ais31_benchmark_runs" in tables
    assert "ais31_benchmark_results" in tables
    eng.dispose()


@pytest.mark.asyncio
async def test_ais31_raw_payload_fallback_preserves_evidence_and_strips_leakage(tmp_path):
    """
    When `Incident.events` is empty (aggregated FortiSIEM incidents), AIS 3.1 MUST fall back to
    sanitized `Incident.raw_payload` while strictly stripping `incidentReso`, `incidentComments`,
    and historical ML `confidence`.
    """
    db_file = tmp_path / "ais31_fallback_test.db"
    from sqlalchemy.ext.asyncio import async_sessionmaker
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        rule = Rule(
            id="r-fb-1",
            rule_id="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
            name="Website access policy violation: Same Source and Destination",
            event_type="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
            severity="MEDIUM",
        )
        db.add(rule)
        inc = Incident(
            id="inc-fb-1",
            incident_id="991001",
            rule_id="r-fb-1",
            event_type="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
            title="Synthetic Policy Violation",
            severity="MEDIUM",
            raw_payload={
                "incidentId": 991001,
                "incidentTitle": "Synthetic website Advertising access",
                "incidentSrc": "srcIpAddr:172.25.25.1, ",
                "incidentTarget": "destIpAddr:142.250.134.148, destName:example.test, ",
                "incidentDetailJson": {"webCategory": "Advertising", "incidentCount": 14},
                "incidentReso": "True Positive",
                "incidentComments": "Resolution set by Machine Learning",
                "confidence": "90",
            },
        )
        db.add(inc)
        cohort = BenchmarkCohort(
            id="coh-fb-1",
            cohort_key="TEST_FALLBACK_COHORT",
            name="Test Fallback Cohort",
            description="Synthetic",
            version=1,
            is_frozen=True,
            required_reviewers=2,
            excluded_from_learning=True,
        )
        db.add(cohort)
        item = BenchmarkCohortItem(
            id="item-fb-1",
            cohort_id="coh-fb-1",
            incident_db_id="inc-fb-1",
            fortisiem_incident_id="991001",
            rule_id="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
            rule_name="Website access policy violation",
            priority_rank=1,
            eligibility_status="ELIGIBLE",
        )
        db.add(item)
        await db.commit()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        loaded_item = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.id == "item-fb-1")
                .options(selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events), selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule))
            )
        ).scalar_one()

        prep = await AIS31BenchmarkService._prepare_incident_wire_payload(
            db=db, item=loaded_item, inc=loaded_item.incident, verify_remote_tokenize=False
        )
        assert prep["events_total"] == 1
        assert prep["events_budgeted"] == 1
        wc = prep["user_content"]
        assert "142.250.134.148" in wc
        assert "Advertising" in wc
        assert "incidentReso" not in wc
        assert "True Positive" not in wc
        assert "Resolution set by Machine Learning" not in wc
        assert '"confidence":"90"' not in wc

    await engine.dispose()

