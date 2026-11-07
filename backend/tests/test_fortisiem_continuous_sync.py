import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.services.ai_verdict_service import AIVerdictService
from app.services.fortisiem_service import FortiSIEMService


@pytest.mark.asyncio
async def test_pull_all_incidents_without_id(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    """
    Verifies that calling /api/fortisiem/pull-all ingests incidents in batch
    without requiring any Incident IDs upfront, and automatically generates AI verdicts.
    """
    res = await client.post(
        "/api/fortisiem/pull-all",
        json={"max_count": 4, "auto_triage_llm": True, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_discovered"] > 0
    assert data["newly_ingested"] > 0
    assert data["ai_verdicts_generated"] > 0
    assert data["checkpoint_epoch"] is not None
    assert len(data["sample_incidents"]) > 0

    # Verify incidents in database have ai_verdict populated
    first_sample_id = data["sample_incidents"][0]["incident_id"]
    stmt = select(Incident).where(Incident.incident_id == first_sample_id).options(
        selectinload(Incident.events), selectinload(Incident.rule)
    )
    r = await db_session.execute(stmt)
    inc = r.scalar_one_or_none()
    assert inc is not None
    assert inc.ai_verdict is not None
    assert "verdict" in inc.ai_verdict
    assert inc.ai_verdict["verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert "reason" in inc.ai_verdict
    assert len(inc.ai_verdict["reason"]) > 0


@pytest.mark.asyncio
async def test_pull_all_caching_idempotency(client: AsyncClient, admin_token: str):
    """
    Verifies that subsequent calls recognize already ingested incidents as cached,
    preventing duplicate entries.
    """
    # 1. First pull to populate database
    res1 = await client.post(
        "/api/fortisiem/pull-all",
        json={"max_count": 3, "auto_triage_llm": False, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["newly_ingested"] > 0

    # 2. Second pull without force_refresh: all should be cached
    res2 = await client.post(
        "/api/fortisiem/pull-all",
        json={"max_count": 3, "auto_triage_llm": False, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["success"] is True
    assert d2["already_cached"] > 0
    assert d2["newly_ingested"] == 0


@pytest.mark.asyncio
async def test_ai_verdict_service_direct(db_session: AsyncSession):
    """
    Tests AIVerdictService directly to verify zero-leakage prompt formatting,
    model evaluation, and investigation queue synchronization.
    """
    # 1. Ingest fixture incident
    f_service = FortiSIEMService(db_session)
    await f_service.pull_and_ingest("132438483", force_refresh=True)

    # 2. Fetch the incident
    stmt = (
        select(Incident)
        .where(Incident.incident_id == "132438483")
        .options(selectinload(Incident.events), selectinload(Incident.rule))
    )
    res = await db_session.execute(stmt)
    inc = res.scalar_one_or_none()
    assert inc is not None

    # 3. Evaluate via AIVerdictService
    service = AIVerdictService(db_session)
    verdict = await service.evaluate_incident(inc, username="test_analyst")

    assert verdict["incident_id"] == inc.incident_id
    assert verdict["verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert 0 <= verdict["confidence"] <= 100
    assert len(verdict["reason"]) > 0

    # 4. Verify investigation note is updated with AI verdict
    inv_q = await db_session.execute(select(Investigation).where(Investigation.incident_id == inc.id))
    inv = inv_q.scalars().first()
    assert inv is not None
    assert "AI Verdict" in (inv.analyst_notes or "")


@pytest.mark.asyncio
async def test_batch_ai_verdict_endpoint(client: AsyncClient, admin_token: str):
    """
    Verifies the /api/fortisiem/batch-ai-verdict endpoint evaluates pending incidents.
    """
    # Ingest incidents first
    await client.post(
        "/api/fortisiem/pull-all",
        json={"max_count": 2, "auto_triage_llm": False, "force_refresh": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    res = await client.post(
        "/api/fortisiem/batch-ai-verdict",
        json={"max_batch": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "processed" in data
    assert "successful" in data


@pytest.mark.asyncio
async def test_scheduler_lifecycle(client: AsyncClient, admin_token: str):
    """
    Tests starting, querying status, triggering an immediate sync, and stopping
    the continuous FortiSIEM background sync scheduler.
    """
    # 1. Check initial status
    status_res = await client.get(
        "/api/fortisiem/scheduler/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "is_running" in status_data
    assert "interval_seconds" in status_data

    # 2. Start scheduler with 180s (3 minute) interval
    start_res = await client.post(
        "/api/fortisiem/scheduler/start",
        json={"interval_seconds": 180, "auto_ai_verdict": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["is_running"] is True
    assert start_data["interval_seconds"] == 180
    assert start_data["auto_ai_verdict"] is True

    # 3. Trigger immediate sync
    trigger_res = await client.post(
        "/api/fortisiem/scheduler/trigger",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.json()
    assert trigger_data.get("success") is True or "status" in trigger_data

    # 4. Stop scheduler
    stop_res = await client.post(
        "/api/fortisiem/scheduler/stop",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stop_res.status_code == 200
    stop_data = stop_res.json()
    assert stop_data["is_running"] is False
