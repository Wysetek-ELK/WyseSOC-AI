import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.services.incident_service import IncidentService
from app.config import settings


@pytest.mark.asyncio
async def test_fortisiem_status(client: AsyncClient, admin_token: str):
    """Verify FortiSIEM status endpoint returns configuration and available fixture IDs."""
    res = await client.get(
        "/api/fortisiem/status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "is_configured" in data
    assert "mode" in data
    assert "sample_incident_ids" in data
    assert isinstance(data["sample_incident_ids"], list)
    assert len(data["sample_incident_ids"]) > 0
    assert "132438483" in data["sample_incident_ids"]


@pytest.mark.asyncio
async def test_fortisiem_pull_valid_incident(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """Test pulling a valid incident by ID (using fixture fallback mode)."""
    incident_id = "132438483"
    res = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": incident_id, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["incident_id"] == incident_id
    assert data["db_id"] is not None
    assert data["event_count"] > 0
    assert "Crowdstrike" in data["title"]

    # Verify database record with eager loaded relationships
    stmt = (
        select(Incident)
        .where(Incident.incident_id == incident_id)
        .options(selectinload(Incident.events), selectinload(Incident.rule))
    )
    r = await db_session.execute(stmt)
    inc = r.scalar_one_or_none()
    assert inc is not None
    assert inc.event_type == "PH_RULE_CS_SUSPICIOUS_ACTIVITY"

    # Verify investigation record was automatically created in the queue
    inv_stmt = select(Investigation).where(Investigation.incident_id == inc.id)
    inv_res = await db_session.execute(inv_stmt)
    inv = inv_res.scalar_one_or_none()
    assert inv is not None
    assert inv.status == "PENDING_REVIEW"

    # Verify Ground Truth Isolation: historical closure data is in ground_truth table, NOT leaked
    inc_service = IncidentService(db_session)
    payload = inc_service.get_model_facing_payload(inc)
    assert "resolution" not in payload
    assert "cleared_reason" not in payload
    assert "clearedReason" not in payload
    assert "comments" not in payload


@pytest.mark.asyncio
async def test_fortisiem_pull_cache_and_force_refresh(client: AsyncClient, admin_token: str):
    """Verify that pulling an existing incident returns cached copy unless force_refresh is requested."""
    incident_id = "132438483"
    # First pull
    res1 = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": incident_id, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res1.status_code == 200

    # Second pull without force_refresh (should hit cache)
    res2 = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": incident_id, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 200
    assert res2.json()["source"] == "DATABASE_CACHE"

    # Third pull with force_refresh
    res3 = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": incident_id, "force_refresh": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res3.status_code == 200
    assert res3.json()["source"] in ("LIVE", "FIXTURE_FALLBACK")


@pytest.mark.asyncio
async def test_fortisiem_pull_nonexistent_incident(client: AsyncClient, admin_token: str):
    """Verify pulling an unknown incident returns 404 with helpful error."""
    res = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": "999999999", "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404
    detail = res.json()["detail"]
    assert "999999999" in detail


@pytest.mark.asyncio
async def test_fortisiem_pull_rbac(client: AsyncClient, viewer_token: str):
    """Verify that read-only viewers cannot trigger incident pulls (requires Admin or SOC Analyst)."""
    res = await client.post(
        "/api/fortisiem/fetch",
        json={"incident_id": "132438483", "force_refresh": False},
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_fortisiem_pull_live_mocked(client: AsyncClient, admin_token: str, monkeypatch):
    """Test pulling from simulated live FortiSIEM HTTP endpoint."""
    import respx
    import httpx

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://fortisiem.example.corp")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "api_user")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "api_pass")
    monkeypatch.setattr(settings, "FORTISIEM_MOCK_FALLBACK", False)

    mock_incident = {
        "incidentId": "888123456",
        "eventType": "PH_RULE_TEST_ALERT",
        "eventName": "Live FortiSIEM Test Alert",
        "category": "Malware",
        "severity": "High",
        "status": 1,
        "detail": "Live API pulled detail",
        "rawEvents": [
            {
                "eventId": "evt_live_1",
                "eventType": "TEST_LOG",
                "attribute": {"procName": "malware.exe"}
            }
        ]
    }

    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.get(
            "https://fortisiem.example.corp/phoenix/rest/incident/incidentDetail"
        ).mock(return_value=httpx.Response(200, json=mock_incident))

        res = await client.post(
            "/api/fortisiem/fetch",
            json={"incident_id": "888123456", "force_refresh": False},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["incident_id"] == "888123456"
        assert data["source"] == "LIVE"
        assert data["event_count"] == 1
        assert route.called

