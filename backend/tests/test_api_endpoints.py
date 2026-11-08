import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion_service import IngestionService

FIXTURE_ZIP_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip")
)


@pytest.mark.asyncio
async def test_dashboard_metrics_empty(client: AsyncClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    resp = await client.get("/api/dashboard/metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_incidents"] == 0
    assert data["is_empty"] is True


@pytest.mark.asyncio
async def test_api_full_workflow(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Ingest via IngestionService to populate DB
    with open(FIXTURE_ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    service = IngestionService(db_session)
    await service.ingest_zip(file_bytes, "Incident json.zip", "admin_test")

    # 2. Check Dashboard Metrics
    dash_resp = await client.get("/api/dashboard/metrics", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total_incidents"] == 20
    assert dash_data["total_rules"] == 2
    assert dash_data["historical_true_positives"] == 10
    assert dash_data["historical_false_positives"] == 10
    assert dash_data["is_empty"] is False
    assert len(dash_data["severity_breakdown"]) > 0
    assert len(dash_data["source_breakdown"]) == 2

    # 3. Check Incidents Listing
    inc_resp = await client.get("/api/incidents?page=1&page_size=10", headers=headers)
    assert inc_resp.status_code == 200
    inc_data = inc_resp.json()
    assert inc_data["total"] == 20
    assert len(inc_data["items"]) == 10
    sample_inc_id = inc_data["items"][0]["incident_id"]

    # 4. Check Incident Detail - Standard Mode (Shows ground truth)
    det_resp = await client.get(f"/api/incidents/{sample_inc_id}?blind_review=false", headers=headers)
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["incident_id"] == sample_inc_id
    assert det_data["ground_truth"] is not None
    assert det_data["ground_truth"]["resolution"] in ["True Positive", "False Positive"]
    assert len(det_data["events"]) > 0

    # 5. Check Incident Detail - Blind Review Mode (Ground truth must be None)
    blind_resp = await client.get(f"/api/incidents/{sample_inc_id}?blind_review=true", headers=headers)
    assert blind_resp.status_code == 200
    blind_data = blind_resp.json()
    assert blind_data["ground_truth"] is None, "Security Violation: Ground truth leaked in Blind Review Mode!"

    # 6. Check Model-Facing Payload Endpoint (Strict Allowlist)
    model_resp = await client.get(f"/api/incidents/{sample_inc_id}/model-payload", headers=headers)
    assert model_resp.status_code == 200
    model_payload = model_resp.json()
    assert "resolution" not in model_payload
    assert "cleared_reason" not in model_payload
    assert "clearedReason" not in model_payload
    assert "comments" not in model_payload
    assert "clearedUser" not in model_payload
    assert "incident_id" in model_payload
    assert "event_type" in model_payload
    assert len(model_payload["events"]) > 0

    # 7. Check Rules Listing
    rules_resp = await client.get("/api/rules", headers=headers)
    assert rules_resp.status_code == 200
    rules_data = rules_resp.json()
    assert rules_data["total"] == 2
    # Verify incident counts are aggregated on rules
    for r in rules_data["items"]:
        assert r["incident_count"] == 10

    # 7b. Check Rules Stats Metrics
    stats_resp = await client.get("/api/rules/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["total_rules"] == 2
    assert stats_data["active_rules"] + stats_data["inactive_rules"] == 2
    assert stats_data["rules_with_incidents"] == 2
    assert stats_data["total_linked_incidents"] == 20

    # 8. Check Audit Logs
    audit_resp = await client.get("/api/audit", headers=headers)
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["total"] > 0

