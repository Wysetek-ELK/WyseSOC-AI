import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.services.incident_service import IncidentService
from app.services.ingestion_service import IngestionService
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

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
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
            "https://192.0.2.10/phoenix/rest/incident/incidentDetail"
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


@pytest.mark.asyncio
async def test_fortisiem_pull_live_404_falls_back_to_fixtures(client: AsyncClient, admin_token: str, monkeypatch):
    """
    Test when live FortiSIEM returns 404 (or endpoint not found), the platform gracefully
    falls back to the offline fixture archive when mock_fallback is enabled.
    """
    import respx
    import httpx

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "super/test")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "testpass")
    monkeypatch.setattr(settings, "FORTISIEM_MOCK_FALLBACK", True)

    with respx.mock(assert_all_called=False) as respx_mock:
        # All live endpoints return 404
        respx_mock.route().mock(return_value=httpx.Response(404, text="Not Found"))

        res = await client.post(
            "/api/fortisiem/fetch",
            json={"incident_id": "132438483", "force_refresh": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["incident_id"] == "132438483"
        assert data["source"] == "FIXTURE_FALLBACK"
        assert "fixture archive" in data["message"].lower()


@pytest.mark.asyncio
async def test_fortisiem_config_and_rbac(client: AsyncClient, admin_token: str, analyst_token: str):
    """Test getting and updating FortiSIEM configuration from the UI with RBAC enforcement."""
    # 1. Non-admin forbidden
    res = await client.get("/api/fortisiem/config", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 403

    # 2. Admin can get config
    res = await client.get("/api/fortisiem/config", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    cfg = res.json()
    assert "host" in cfg
    assert "username" in cfg
    assert "is_password_set" in cfg
    assert "verify_ssl" in cfg

    # 3. Admin can update config
    update_payload = {
        "host": "https://siem-supervisor.internal",
        "username": "svc_soc_ai",
        "password": "SecretSuperPassword123!",
        "verify_ssl": False,
        "timeout": 30.0,
        "mock_fallback": True,
    }
    update_res = await client.post(
        "/api/fortisiem/config",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_res.status_code == 200
    updated_cfg = update_res.json()
    assert updated_cfg["host"] == "https://siem-supervisor.internal"
    assert updated_cfg["username"] == "svc_soc_ai"
    assert updated_cfg["is_password_set"] is True
    assert updated_cfg["timeout"] == 30.0
    # Guarantee password is never leaked in response
    assert "password" not in updated_cfg


@pytest.mark.asyncio
async def test_fortisiem_test_connection(client: AsyncClient, admin_token: str, analyst_token: str):
    """Test testing FortiSIEM connectivity from the UI."""
    import respx
    import httpx

    # Non-admin forbidden
    res_deny = await client.post(
        "/api/fortisiem/test-connection",
        json={"host": "https://fortisiem.probe.net", "username": "admin", "password": "abc"},
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res_deny.status_code == 403

    # Admin tests successful connection
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.get(
            "https://fortisiem.probe.net/phoenix/rest/incident/incidentDetail"
        ).mock(return_value=httpx.Response(404, text="Incident 0 not found"))

        res_ok = await client.post(
            "/api/fortisiem/test-connection",
            json={"host": "https://fortisiem.probe.net", "username": "admin", "password": "abc"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_ok.status_code == 200
        ok_data = res_ok.json()
        assert ok_data["success"] is True
        assert ok_data["latency_ms"] is not None
        assert route.called


@pytest.mark.asyncio
async def test_fortisiem_sync_rules(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """Test bulk synchronization of detection rules from FortiSIEM/fixtures into local database."""
    from app.models.rule import Rule

    res = await client.post(
        "/api/fortisiem/sync-rules",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_local_rules"] >= 2
    assert "Successfully synchronized" in data["message"]

    # Verify rules are present in database
    r_res = await db_session.execute(select(Rule))
    rules = r_res.scalars().all()
    assert len(rules) >= 2


@pytest.mark.asyncio
async def test_fortisiem_cache_miss_auto_registers_rule(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """Test that ingesting an incident with an unseen rule dynamically creates and links the Rule locally."""
    from app.models.rule import Rule
    from app.services.ingestion_service import IngestionService

    ingestion = IngestionService(db_session)
    unseen_event_type = "PH_RULE_TEST_CACHE_MISS_DYNAMIC_DISCOVERY"
    payload = {
        "incidentId": "99999901",
        "title": "Dynamic Cache Miss Security Alert",
        "eventName": "Dynamic Cache Miss Security Alert",
        "eventType": unseen_event_type,
        "eventSeverity": "HIGH",
        "eventSeverityCat": "HIGH",
        "phIncidentCategory": "Security",
        "phSubIncidentCategory": "Policy Violation",
        "incidentDetail": "{\"testPolicy\": true}",
    }

    job, result, msg = await ingestion.ingest_single_json(
        raw_data=payload,
        filename="test_cache_miss.json",
        username="admin"
    )
    assert result == "imported"

    # Verify rule was dynamically created in local DB
    rule_q = await db_session.execute(select(Rule).where(Rule.event_type == unseen_event_type))
    created_rule = rule_q.scalar_one_or_none()
    assert created_rule is not None
    assert created_rule.rule_id == unseen_event_type
    assert created_rule.severity == "HIGH"
    assert created_rule.name == "Dynamic Cache Miss Security Alert"

    # Verify incident is properly linked to the new rule
    inc_q = await db_session.execute(select(Incident).where(Incident.incident_id == "99999901"))
    inc = inc_q.scalar_one_or_none()
    assert inc is not None
    assert inc.rule_id == created_rule.id


@pytest.mark.asyncio
async def test_fortisiem_pull_rule_endpoint(client: AsyncClient, admin_token: str, monkeypatch):
    """Test pulling a dedicated rule from FortiSIEM live endpoint."""
    import respx
    from app.models.rule import Rule

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "api_user")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "api_pass")

    mock_rule = {
        "ruleId": "PH_RULE_LIVE_PULL_CUSTOM_TEST",
        "name": "Live Pulled FortiSIEM Detection Rule",
        "description": "Detection rule pulled directly from FortiSIEM Supervisor rule API.",
        "severity": "CRITICAL",
        "category": "Security",
        "subCategory": "Malware Outbreak",
        "dataSource": "FortiGate",
        "pattern": "srcIp != dstIp AND dstPort == 445",
        "attackTechnique": "T1021.002",
        "attackTactic": "Lateral Movement",
    }

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get("https://192.0.2.10/phoenix/rest/pub/rule/PH_RULE_LIVE_PULL_CUSTOM_TEST").respond(
            status_code=200,
            json=mock_rule,
        )

        res = await client.post(
            "/api/fortisiem/pull-rule",
            json={"rule_id": "PH_RULE_LIVE_PULL_CUSTOM_TEST", "force_refresh": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["rule_id"] == "PH_RULE_LIVE_PULL_CUSTOM_TEST"
        assert data["severity"] == "CRITICAL"
        assert "Live Pulled FortiSIEM Detection Rule" in data["name"]


@pytest.mark.asyncio
async def test_fortisiem_live_rule_enrichment_on_incident_cache_miss(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """Verify that when an incident is ingested with an unseen rule, the rule is pulled live from FortiSIEM."""
    import respx
    from app.models.rule import Rule
    from app.services.ingestion_service import IngestionService

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "api_user")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "api_pass")

    unseen_event_type = "PH_RULE_LIVE_DISCOVERED_PRIV_ESC"
    mock_siem_rule = {
        "ruleId": unseen_event_type,
        "name": "Live Priv Escalation Rule",
        "description": "Rich description pulled directly from FortiSIEM rule API.",
        "severity": "HIGH",
        "category": "Privilege Escalation",
        "subCategory": "Credential Access",
        "dataSource": "Windows Security Event",
        "pattern": "eventId == 4672",
        "attackTechnique": "T1078",
        "attackTactic": "Privilege Escalation",
    }

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get("https://192.0.2.10/phoenix/rest/pub/rule").respond(
            status_code=200,
            json=mock_siem_rule,
        )

        ingestion = IngestionService(db_session)
        payload = {
            "incidentId": "99999902",
            "title": "Privilege Escalation Incident",
            "eventName": "Live Priv Escalation Rule",
            "eventType": unseen_event_type,
            "eventSeverity": "HIGH",
        }

        job, result, msg = await ingestion.ingest_single_json(
            raw_data=payload,
            filename="test_live_rule_cache_miss.json",
            username="admin",
        )
        assert result == "imported"

        # Verify rule was enriched from FortiSIEM rule API
        rule_q = await db_session.execute(select(Rule).where(Rule.event_type == unseen_event_type))
        created_rule = rule_q.scalar_one_or_none()
        assert created_rule is not None
        assert created_rule.rule_id == unseen_event_type
        assert created_rule.parsed_metadata.get("source") == "FORTISIEM_LIVE_RULE_API"
        assert created_rule.parsed_metadata.get("attackTechnique") == "T1078"


@pytest.mark.asyncio
async def test_fortisiem_pull_manually_cleared_resolution(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """
    Verify pulling an incident with FortiSIEM closure fields:
    - Incident Status: Manually Cleared
    - Cleared Reason: TEst
    - Cleared User: rohitp
    - Resolution: False Positive
    - Cleared Time: 1793783492775
    Correctly populates HistoricalGroundTruth and Incident status.
    """
    import respx
    import httpx

    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "api_user")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "api_pass")
    monkeypatch.setattr(settings, "FORTISIEM_MOCK_FALLBACK", False)

    mock_incident = {
        "incidentId": "888999111",
        "eventType": "PH_RULE_TEST_CLEARED",
        "eventName": "Live Cleared Test Alert",
        "severity": "MEDIUM",
        "incidentStatus": "Manually Cleared",
        "clearedReason": "TEst",
        "clearedUser": "rohitp",
        "resolution": "False Positive",
        "clearedTime": 1793783492775,
        "comments": "Analyst reviewed and cleared as FP",
        "rawEvents": [
            {
                "eventId": "evt_cl_1",
                "eventType": "TEST_LOG",
                "attribute": {"procName": "safe_app.exe"}
            }
        ]
    }

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(
            "https://192.0.2.10/phoenix/rest/incident/incidentDetail"
        ).mock(return_value=httpx.Response(200, json=mock_incident))

        res = await client.post(
            "/api/fortisiem/fetch",
            json={"incident_id": "888999111", "force_refresh": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["status_name"] == "Manually Cleared"
        assert data["resolution"] == "False Positive"
        assert data["cleared_reason"] == "TEst"
        assert data["cleared_user"] == "rohitp"

        # Verify DB records
        q = await db_session.execute(
            select(Incident, HistoricalGroundTruth)
            .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
            .where(Incident.incident_id == "888999111")
        )
        row = q.first()
        assert row is not None
        inc, gt = row
        assert inc.status_code == 2
        assert inc.status_name == "Manually Cleared"
        assert gt is not None
        assert gt.resolution == "False Positive"
        assert gt.cleared_reason == "TEst"
        assert gt.cleared_user == "rohitp"
        assert gt.cleared_time_epoch == 1793783492775


@pytest.mark.asyncio
async def test_fortisiem_sync_ground_truth_for_existing_open_incident(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """
    Verify that when an existing incident was ingested while Open,
    re-pulling or syncing from FortiSIEM updates its ground truth and marks it Manually Cleared.
    """
    import respx
    import httpx

    # 1. Ingest incident as Open
    ingestion = IngestionService(db_session)
    open_payload = {
        "incidentId": "888999222",
        "title": "Initially Open Incident",
        "eventName": "Initially Open Alert",
        "eventType": "PH_RULE_OPEN_TEST",
        "severity": "HIGH",
        "status": 1,
        "incidentStatus": "0",
    }
    await ingestion.ingest_single_json(open_payload, filename="open.json", username="test")

    # Verify initially open
    q1 = await db_session.execute(select(Incident).where(Incident.incident_id == "888999222"))
    inc1 = q1.scalar_one_or_none()
    assert inc1 is not None
    assert inc1.status_code == 1
    assert inc1.status_name == "Open"

    # 2. Setup mock for updated FortiSIEM resolution
    monkeypatch.setattr(settings, "FORTISIEM_HOST", "https://192.0.2.10")
    monkeypatch.setattr(settings, "FORTISIEM_USERNAME", "api_user")
    monkeypatch.setattr(settings, "FORTISIEM_PASSWORD", "api_pass")
    monkeypatch.setattr(settings, "FORTISIEM_MOCK_FALLBACK", False)

    resolved_payload = {
        "incidentId": "888999222",
        "eventType": "PH_RULE_OPEN_TEST",
        "title": "Initially Open Incident",
        "incidentStatus": "Manually Cleared",
        "incidentReso": "True Positive",
        "clearReason": "Malware confirmed on host",
        "caseUser": "analyst1",
        "incidentClearedTime": 1793799999000,
    }

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            "https://192.0.2.10/phoenix/rest/incident/incidentDetail"
        ).mock(return_value=httpx.Response(200, json=resolved_payload))

        # Call single incident sync endpoint
        res = await client.post(
            "/api/fortisiem/incident/888999222/sync-resolution",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["status_name"] == "Manually Cleared"
        assert data["resolution"] == "True Positive"
        assert data["cleared_reason"] == "Malware confirmed on host"
        assert data["cleared_user"] == "analyst1"

        # Verify DB is updated
        q2 = await db_session.execute(
            select(Incident, HistoricalGroundTruth)
            .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
            .where(Incident.incident_id == "888999222")
        )
        inc2, gt2 = q2.first()
        assert inc2.status_code == 2
        assert inc2.status_name == "Manually Cleared"
        assert gt2.resolution == "True Positive"
        assert gt2.cleared_reason == "Malware confirmed on host"
        assert gt2.cleared_user == "analyst1"


@pytest.mark.asyncio
async def test_fortisiem_sync_all_resolutions_endpoint(client: AsyncClient, admin_token: str):
    """Verify the /api/fortisiem/sync-resolutions endpoint runs cleanly."""
    res = await client.post(
        "/api/fortisiem/sync-resolutions",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "total_incidents_checked" in data
    assert "resolutions_updated" in data




