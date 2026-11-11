"""
Phase 9.1 Hardening & Closure Regression Tests.

Covers:
1. Live / HTTP_MOCK / SIMULATED / HISTORICAL / OFFLINE / DEGRADED / Guard provenance separation.
2. Historical execution provenance persistence across Server 2 URL / availability changes.
3. Endpoint health & system monitor honesty (HTTP mocks never report verified Server 2 GPU telemetry).
4. Security hardening: production startup must not auto-seed default hardcoded admin credentials.
5. Pilot RBAC matrix verification across Administrator, SOC Analyst, and Read-Only Viewer.
6. Deployment package script line-ending (LF) and unit consistency validation.
"""

from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.user import User
from app.services.provenance import classify_endpoint_status, classify_execution_provenance
from app.utils.security import create_access_token, get_password_hash


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_approved_rule_and_incident(
    db: AsyncSession,
    *,
    rule_id_str: str,
    incident_id_str: str,
) -> tuple[Rule, Incident, Investigation]:
    rule = Rule(
        rule_id=rule_id_str,
        name=f"Rule {rule_id_str}",
        event_type=rule_id_str,
        severity="HIGH",
        description="Outbound network connection to untrusted remote destination.",
        data_source="FortiSIEM",
        status="ACTIVE",
        pattern_logic='{"condition":"destIp != null"}',
    )
    db.add(rule)
    await db.flush()

    rp = RulePrompt(rule_id=rule.id)
    db.add(rp)
    await db.flush()

    pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        is_template_draft=False,
        common_prompt="Evidence-first SOC analysis.",
        rule_specific_prompt="Validate outbound network telemetry against threat indicators.",
        detection_conditions="Outbound connection observed.",
        required_evidence="srcIp, destIp, destPort",
        tp_indicators="External untrusted IP transfer.",
        fp_indicators="Verified patch CDN endpoint.",
        missing_info_criteria="Abstain if destIp missing.",
        escalation_conditions="High volume exfil.",
        analyst_questions=["Verify host owner?"],
        quality_status="PASSED",
        quality_score=95.0,
    )
    db.add(pv)
    await db.flush()
    rp.active_version_id = pv.id
    db.add(
        RuleIntelligenceSnapshot(
            rule_id=rule.id,
            rule_identifier=rule.rule_id,
            primary_archetype="NETWORK_CONNECTION",
            definition_status="COMPLETE",
            source_provenance="TEST",
        )
    )

    inc = Incident(
        incident_id=incident_id_str,
        rule_id=rule.id,
        title=f"Incident {incident_id_str}",
        event_type=rule_id_str,
        severity="HIGH",
        source_ip="192.0.2.55",
        reporting_device="fw-edge-01",
        raw_payload={"srcIp": "192.0.2.55", "destIp": "198.51.100.77", "destPort": 443},
    )
    db.add(inc)
    await db.flush()
    db.add(
        IncidentEvent(
            incident_id=inc.id,
            event_id=f"EV-{incident_id_str}",
            event_type=rule_id_str,
            raw_log="Outbound traffic srcIp=192.0.2.55 destIp=198.51.100.77 destPort=443",
            attributes={"srcIp": "192.0.2.55", "destIp": "198.51.100.77", "destPort": 443},
        )
    )
    inv = Investigation(incident_id=inc.id, status="PENDING_REVIEW")
    db.add(inv)
    await db.commit()
    return rule, inc, inv


# =========================================================================
# 1. PROVENANCE CLASSIFIER: LIVE / HTTP_MOCK / SIMULATED / HISTORICAL / OFFLINE / DEGRADED
# =========================================================================

def test_provenance_classifier_separates_mock_live_sim_and_historical(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVENANCE", "AUTO")
    monkeypatch.setattr(settings, "TEST_ENVIRONMENT_ID", "")

    mock_ep = classify_endpoint_status(
        is_healthy=True,
        raw_status="ONLINE",
        base_url="http://127.0.0.1:8000/v1",
        metrics_available=True,
    )
    assert mock_ep["endpoint_provenance"] == "HTTP_MOCK"
    assert mock_ep["current_s2_health"] == "HTTP_MOCK"
    assert mock_ep["gpu_telemetry_verified"] is False

    live_ep = classify_endpoint_status(
        is_healthy=True,
        raw_status="ONLINE",
        base_url="http://server2-gpu.example.com:8000/v1",
        metrics_available=True,
    )
    assert live_ep["endpoint_provenance"] == "LIVE_PROVIDER"
    assert live_ep["current_s2_health"] == "ONLINE"
    assert live_ep["gpu_telemetry_verified"] is True

    offline_ep = classify_endpoint_status(
        is_healthy=False,
        raw_status="OFFLINE",
        base_url="http://server2-gpu.example.com:8000/v1",
        metrics_available=False,
    )
    assert offline_ep["endpoint_provenance"] == "OFFLINE"
    assert offline_ep["current_s2_health"] == "OFFLINE"
    assert offline_ep["gpu_telemetry_verified"] is False

    degraded_ep = classify_endpoint_status(
        is_healthy=False,
        raw_status="DEGRADED",
        base_url="http://server2-gpu.example.com:8000/v1",
    )
    assert degraded_ep["endpoint_provenance"] == "DEGRADED"
    assert degraded_ep["current_s2_health"] == "DEGRADED"

    # Historical LIVE_PROVIDER record remains LIVE_PROVIDER even when Server 2 is offline now
    hist_live = classify_execution_provenance(
        is_simulated=False,
        model_identifier="Qwen/Qwen2.5-7B-Instruct-AWQ",
        recorded_provenance="LIVE_PROVIDER",
        source_type="HISTORICAL",
        is_historical_context=True,
    )
    assert hist_live["execution_provenance"] == "LIVE_PROVIDER"
    assert hist_live["historical_execution_provenance"] == "HISTORICAL (LIVE_PROVIDER)"

    # Guard & Simulator classifications
    assert classify_execution_provenance(is_simulated=True, model_identifier="sim")["execution_provenance"] == "SIMULATED"
    assert classify_execution_provenance(model_identifier="POLICY_GUARD")["execution_provenance"] == "POLICY_GUARD"
    assert classify_execution_provenance(eligibility_status="FAILED", error_message="SERVER2_OFFLINE")["execution_provenance"] == "OFFLINE"


# =========================================================================
# 2. ENDPOINT & PILOT PERSISTED MOCK-VS-LIVE PROVENANCE REGRESSION
# =========================================================================

@pytest.mark.asyncio
async def test_pilot_persists_http_mock_provenance_independently_of_current_s2(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, analyst_token: str, monkeypatch
):
    class _MockOpenAI(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/metrics"):
                body = b"vllm:num_requests_running 1\nvllm:gpu_cache_usage_factor 0.2\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(body)
                return
            body = json.dumps({"object": "list", "data": [{"id": "mock-model"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or "0")
            _ = self.rfile.read(length)
            payload = {
                "id": "chatcmpl-p91",
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "verdict": "REQUIRES_ATTENTION",
                            "confidence": 55,
                            "reason": "Evaluated via loopback mock HTTP server for testing.",
                            "supporting_evidence": ["srcIp: 192.0.2.55"],
                            "supporting_claims": [],
                            "missing_evidence": [],
                            "analyst_questions": ["Verify firewall log"],
                        })
                    }
                }],
                "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), _MockOpenAI)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "mock-model")
        monkeypatch.setattr(settings, "LOCAL_LLM_PROVENANCE", "HTTP_MOCK")
        monkeypatch.setattr(settings, "TEST_ENVIRONMENT_ID", "PYTEST_HTTP_MOCK")

        _, inc, inv = await _seed_approved_rule_and_incident(
            db_session, rule_id_str="P91-PROV-001", incident_id_str="INC-P91-MOCK-1"
        )

        # Endpoint monitors must classify loopback HTTP server as HTTP_MOCK and never verify GPU hardware
        s2_live = (await client.get("/api/system/servers/live", headers=_auth_header(analyst_token))).json()
        assert s2_live["server_2"]["details"]["endpoint_provenance"] == "HTTP_MOCK"
        assert s2_live["server_2"]["details"]["gpu_telemetry_verified"] is False
        assert s2_live["server_2"]["gpu_memory_total_gb"] is None

        llm_st = (await client.get("/api/dashboard/llm-status", headers=_auth_header(analyst_token))).json()
        assert llm_st["endpoint_provenance"] == "HTTP_MOCK"
        assert llm_st["gpu_telemetry_verified"] is False
        assert llm_st["test_environment"] == "PYTEST_HTTP_MOCK"

        # Activate pilot in ANALYST_ASSISTED and evaluate against the HTTP_MOCK server
        act = await client.post(
            "/api/pilot/activate",
            json={"mode": "ANALYST_ASSISTED", "change_reason": "Phase 9.1 provenance test"},
            headers=_auth_header(admin_token),
        )
        assert act.status_code == 200

        ev = await client.post(
            f"/api/pilot/evaluate/{inc.incident_id}?source_type=LIVE",
            headers=_auth_header(analyst_token),
        )
        assert ev.status_code == 200
        assert ev.json()["execution_provenance"] == "HTTP_MOCK"

        # Switch Server 2 configuration to an unreachable remote host & clear mock flags
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://198.51.100.250:59999/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_PROVENANCE", "LIVE_PROVIDER")
        monkeypatch.setattr(settings, "TEST_ENVIRONMENT_ID", "")

        # Historical record in /api/pilot/evaluations & /api/investigations MUST remain HTTP_MOCK!
        evals = (await client.get("/api/pilot/evaluations", headers=_auth_header(analyst_token))).json()
        target = next(x for x in evals if x["incident_id"] == inc.incident_id)
        assert target["execution_provenance"] == "HTTP_MOCK"
        assert target["test_environment"] == "PYTEST_HTTP_MOCK"

        met = (await client.get("/api/pilot/metrics", headers=_auth_header(analyst_token))).json()
        assert met["operational"]["http_mock_evaluations_count"] >= 1
        assert met["operational"]["live_provider_evaluations_count"] == 0
        assert met["operational"]["current_s2_health"] == "OFFLINE"

        det = (await client.get(f"/api/investigations/{inv.id}", headers=_auth_header(analyst_token))).json()
        assert det["ai_assurance"]["execution_provenance"] == "HTTP_MOCK"
        assert det["ai_assurance"]["current_s2_health"] == "OFFLINE"
    finally:
        server.shutdown()
        server.server_close()


# =========================================================================
# 3. SECURITY HARDENING & RBAC CONSISTENCY REGRESSIONS
# =========================================================================

@pytest.mark.asyncio
async def test_production_lifespan_never_seeds_default_admin_credentials(tmp_path: Path, monkeypatch):
    """Verify APP_ENV=production never auto-creates admin/AdminPassword123! on empty user table."""
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession, async_sessionmaker, create_async_engine
    import app.main as main_mod
    from app.database import Base

    db_file = tmp_path / "prod_lifespan.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_file}", connect_args={"check_same_thread": False})
    sess_maker = async_sessionmaker(bind=eng, class_=_AsyncSession, expire_on_commit=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(main_mod, "async_engine", eng)
    monkeypatch.setattr(main_mod, "AsyncSessionLocal", sess_maker)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", f"test-prod-{secrets.token_hex(24)}")
    with (
        patch("app.services.migration_service.verify_schema_on_startup", return_value=(True, "ok")),
        patch("app.main.fortisiem_scheduler.start_supervisor"),
        patch("app.main.fortisiem_scheduler.shutdown_worker"),
    ):
        async with main_mod.lifespan(main_mod.app):
            pass

    async with sess_maker() as verify_sess:
        users = (await verify_sess.execute(select(User))).scalars().all()
        assert len(users) == 0, "Production startup must not auto-seed default hardcoded credentials"
    await eng.dispose()


@pytest.mark.asyncio
async def test_pilot_rbac_matrix_all_roles(client: AsyncClient, db_session: AsyncSession, admin_token: str, analyst_token: str):
    viewer = User(
        username="viewer_p91",
        email="viewer_p91@example.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Read Only Viewer",
        role="Read-Only Viewer",
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    viewer_token = create_access_token({"sub": viewer.id, "username": viewer.username, "role": viewer.role})

    # Viewer: read allowed on config/metrics/evaluations, mutations blocked (403)
    assert (await client.get("/api/pilot/config", headers=_auth_header(viewer_token))).status_code == 200
    assert (await client.get("/api/pilot/metrics", headers=_auth_header(viewer_token))).status_code == 200
    assert (await client.post("/api/pilot/activate", json={"mode": "SHADOW", "change_reason": "test"}, headers=_auth_header(viewer_token))).status_code == 403
    assert (await client.post("/api/pilot/run-batch", json={"max_batch": 1, "source_type": "LIVE"}, headers=_auth_header(viewer_token))).status_code == 403

    # Analyst: execution allowed (returns SKIPPED when DISABLED), admin lifecycle config blocked (403)
    assert (await client.post("/api/pilot/activate", json={"mode": "SHADOW", "change_reason": "test"}, headers=_auth_header(analyst_token))).status_code == 403
    batch_res = await client.post("/api/pilot/run-batch", json={"max_batch": 1, "source_type": "LIVE"}, headers=_auth_header(analyst_token))
    assert batch_res.status_code == 200

    # Admin: lifecycle allowed
    assert (await client.post("/api/pilot/activate", json={"mode": "SHADOW", "change_reason": "admin test"}, headers=_auth_header(admin_token))).status_code == 200
    assert (await client.post("/api/pilot/disable", json={"reason": "reset to disabled"}, headers=_auth_header(admin_token))).status_code == 200


# =========================================================================
# 4. INTEGRATION HONESTY & DEPLOYMENT PACKAGE CONSISTENCY REGRESSIONS
# =========================================================================

def test_integration_runner_blocks_loopback_mock_from_live_model_validation(monkeypatch):
    import sys
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    import scripts.run_integration_suite as runner
    import asyncio

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/metrics"):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"vllm:num_requests_running 0\n")
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"object":"list","data":[{"id":"mock-m"}]}')

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or "0")
            _ = self.rfile.read(length)
            body = json.dumps({
                "id": "cmpl",
                "choices": [{"message": {"content": json.dumps({"verdict": "REQUIRES_ATTENTION", "confidence": 50, "reason": "ok"})}}],
            }).encode("utf-8")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "mock-m")
        rep = asyncio.run(runner.run_staging_probes("LIVE_MODEL_VALIDATION"))
        assert rep["overall_status"] == "BLOCKED"
        assert rep["checks"]["server1_to_server2"]["classification"] == "NOT_TESTED"
        assert rep["checks"]["server1_to_server2"]["execution_provenance"] == "HTTP_MOCK"
    finally:
        server.shutdown()
        server.server_close()


def test_deployment_package_lf_and_service_unit_consistency():
    repo_root = Path(__file__).resolve().parents[2]
    dep_dir = repo_root / "deployment"

    for p in dep_dir.rglob("*"):
        if p.is_file() and "__pycache__" not in str(p):
            assert b"\r\n" not in p.read_bytes(), f"Deployment file must use Unix LF line endings: {p}"

    required_units = [
        "ai-verdict-backend",
        "ai-verdict-worker",
        "ai-verdict-scheduler",
        "ai-verdict-frontend",
    ]
    for script_name in ("install_ubuntu.sh", "verify_server1.sh", "start_services.sh", "stop_services.sh", "rollback_server1.sh"):
        text = (dep_dir / "scripts" / script_name).read_text(encoding="utf-8")
        for unit in required_units:
            assert unit in text, f"{script_name} missing service unit {unit}"
