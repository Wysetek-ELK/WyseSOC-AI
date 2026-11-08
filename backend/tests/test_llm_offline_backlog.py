import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.incident import Incident
from app.services.ai_verdict_service import AIVerdictService, LocalLLMUnavailableError
from app.services.fortisiem_service import FortiSIEMService


@pytest.mark.asyncio
async def test_ingestion_when_llm_offline_defers_verdicts(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """
    Verifies that when Local LLM is offline, incidents are ingested cleanly into the DB
    with ai_verdict = None, and no fake or simulated verdicts are processed.
    """
    async def mock_offline(*args, **kwargs):
        return False

    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_offline)

    f_service = FortiSIEMService(db_session)
    result = await f_service.pull_all_incidents(max_count=3, auto_triage_llm=True, force_refresh=True)

    assert result["success"] is True
    assert result["newly_ingested"] > 0
    # AI verdicts must NOT be processed while Local LLM is offline
    assert result["ai_verdicts_generated"] == 0

    # Verify all ingested incidents have ai_verdict as None (pending)
    stmt = select(Incident).where(Incident.ai_verdict.is_(None))
    r = await db_session.execute(stmt)
    pending_incidents = r.scalars().all()
    assert len(pending_incidents) >= result["newly_ingested"]


@pytest.mark.asyncio
async def test_single_incident_eval_when_offline_returns_503(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """
    Verifies that requesting an AI verdict on a single incident when Local LLM is offline
    returns HTTP 503 Service Unavailable with an informative message.
    """
    async def mock_offline(*args, **kwargs):
        return False

    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_offline)

    # Ingest fixture incident
    f_service = FortiSIEMService(db_session)
    await f_service.pull_and_ingest("132438483", force_refresh=True)

    # Request AI verdict on the incident
    res = await client.post(
        "/api/incidents/132438483/ai-verdict",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert "offline" in detail.lower()


@pytest.mark.asyncio
async def test_process_pending_incidents_when_llm_comes_online(client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch):
    """
    Verifies that once Local LLM comes online, all pending incidents are evaluated
    one by one and saved to the database.
    """
    async def mock_offline(*args, **kwargs):
        return False

    async def mock_online(*args, **kwargs):
        return True

    # 1. First ingest with Local LLM offline
    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_offline)

    f_service = FortiSIEMService(db_session)
    await f_service.pull_all_incidents(max_count=3, auto_triage_llm=True, force_refresh=True)

    ai_service = AIVerdictService(db_session)
    pending_before = await ai_service.get_pending_incident_count()
    assert pending_before >= 3

    # 2. Local LLM comes online (simulate online with mock fallback for testing without real GPU)
    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", True)
    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_online)

    # Process pending incidents backlog
    res = await f_service.process_pending_incidents(max_count=50, username="test_backlog_worker")

    assert res["success"] is True
    assert res["is_llm_online"] is True
    assert res["processed"] >= pending_before
    assert res["pending_remaining"] == 0

    # Verify incidents in database now have ai_verdict populated
    pending_after = await ai_service.get_pending_incident_count()
    assert pending_after == 0

    stmt = select(Incident).where(Incident.ai_verdict.is_not(None))
    r = await db_session.execute(stmt)
    evaluated = r.scalars().all()
    assert len(evaluated) >= pending_before
    for inc in evaluated:
        assert inc.ai_verdict is not None
        assert "verdict" in inc.ai_verdict
