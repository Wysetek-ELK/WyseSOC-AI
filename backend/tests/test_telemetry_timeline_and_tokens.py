import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident
from app.models.token_usage import TokenUsageRecord
from app.models.telemetry_timeline import TelemetryTimelineRecord
from app.services.token_analytics_service import TokenAnalyticsService
from app.services.telemetry_timeline_service import TelemetryTimelineService
from app.services.ai_verdict_service import VerdictTriageAgent
from app.services.fortisiem_service import FortiSIEMService


@pytest.mark.asyncio
async def test_token_analytics_service_bifurcation(db_session: AsyncSession):
    """
    Verifies that TokenAnalyticsService records and accurately calculates
    bifurcated tokens (prompt vs completion) broken down by process and model.
    """
    svc = TokenAnalyticsService(db_session)

    # 1. Record triage token usage
    await svc.record_token_usage(
        process_type="INCIDENT_TRIAGE",
        model_identifier="Qwen 2.5 7B Instruct AWQ",
        prompt_tokens=850,
        completion_tokens=150,
        latency_ms=1200,
        incident_id="INC-TEST-100",
        rule_id="RULE-WEB-POL",
    )

    # 2. Record simulation token usage
    await svc.record_token_usage(
        process_type="SIMULATION_REPLAY",
        model_identifier="Qwen 2.5 7B Instruct AWQ",
        prompt_tokens=600,
        completion_tokens=100,
        latency_ms=800,
        process_id="JOB-DRY-RUN-1",
    )

    analytics = await svc.get_bifurcated_analytics(window_days=7)

    assert analytics["storage_location"] == "Server 1 Persistent Database"
    assert analytics["totals"]["total_tokens"] >= 1700
    assert analytics["totals"]["prompt_tokens"] >= 1450
    assert analytics["totals"]["completion_tokens"] >= 250
    assert analytics["totals"]["total_calls"] >= 2

    # Check process bifurcation
    proc_types = [p["process_type"] for p in analytics["by_process"]]
    assert "INCIDENT_TRIAGE" in proc_types
    assert "SIMULATION_REPLAY" in proc_types

    # Check model bifurcation
    models = [m["model_identifier"] for m in analytics["by_model"]]
    assert "Qwen 2.5 7B Instruct AWQ" in models

    # Check recent ledger
    assert len(analytics["recent_ledger"]) >= 2
    ledger_incident_ids = [item["incident_id"] for item in analytics["recent_ledger"] if item["incident_id"]]
    assert "INC-TEST-100" in ledger_incident_ids


@pytest.mark.asyncio
async def test_token_analytics_api_endpoint(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """
    Verifies that GET /api/tokens/analytics returns HTTP 200 with bifurcated token breakdown.
    """
    svc = TokenAnalyticsService(db_session)
    await svc.record_token_usage(
        process_type="INCIDENT_TRIAGE",
        model_identifier="Qwen 2.5 7B Instruct AWQ",
        prompt_tokens=900,
        completion_tokens=120,
        incident_id="INC-API-TEST",
    )

    res = await client.get(
        "/api/tokens/analytics?window_days=30",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "totals" in data
    assert "by_process" in data
    assert "by_model" in data
    assert "recent_ledger" in data
    assert data["totals"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_incident_historical_telemetry_timeline_on_server_1(
    client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch
):
    """
    Verifies that an incident's complete lifecycle and raw event milestones
    are archived on Server 1 and retrieved through GET /api/incidents/{id}/timeline.
    """
    # Ingest fixture incident
    f_svc = FortiSIEMService(db_session)
    await f_svc.pull_and_ingest("132438483", force_refresh=True)

    # Evaluate incident with mock provider
    ai_agent = VerdictTriageAgent(db_session)
    await ai_agent.evaluate_incident("132438483", username="test_analyst", allow_simulated_fallback=True)

    # Query timeline service directly
    timeline_svc = TelemetryTimelineService(db_session)
    timeline_data = await timeline_svc.get_incident_timeline("132438483")

    assert timeline_data["success"] is True
    assert timeline_data["storage_node"] == "Server 1 Persistent Storage"
    assert timeline_data["milestone_count"] > 0

    # Ensure token bifurcation exists for this incident
    assert timeline_data["token_summary"]["total_tokens"] > 0
    assert timeline_data["token_summary"]["prompt_tokens"] > 0

    # Check milestone stages present
    stages = [m["stage"] for m in timeline_data["milestones"]]
    assert "INGESTION" in stages or "OBSERVATION" in stages
    assert "TRIAGE" in stages

    # Check API endpoint
    api_res = await client.get(
        "/api/incidents/132438483/timeline",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert api_res.status_code == 200
    json_data = api_res.json()
    assert json_data["success"] is True
    assert json_data["storage_node"] == "Server 1 Persistent Storage"
    assert len(json_data["milestones"]) > 0


@pytest.mark.asyncio
async def test_global_telemetry_timeline_api(client: AsyncClient, admin_token: str):
    """
    Verifies that GET /api/telemetry/timeline returns HTTP 200 with Server 1 timeline ledger.
    """
    res = await client.get(
        "/api/telemetry/timeline?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Server 1" in data["storage_node"]
    assert "timeline" in data

