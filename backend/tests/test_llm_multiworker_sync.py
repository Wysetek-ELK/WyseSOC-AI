import os
import pytest
import respx
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.schemas.llm_config import LLMConfigUpdate
from app.services.llm_config_service import LLMConfigService
from app.services.system_monitor_service import SystemMonitorService
from app.services.ai_verdict_service import AIVerdictService
from app.services.model_provider.factory import get_model_provider
from app.services.fortisiem_scheduler import SentinelIngestWorker


@pytest.mark.asyncio
async def test_multiworker_llm_config_sync_in_production_mode(monkeypatch, tmp_path):
    """
    Simulates Worker 1 updating LLM config in APP_ENV=production and Worker 2
    picking up the exact Server 2 URL, model, and cache invalidation automatically.
    """
    state_file = str(tmp_path / "llm_config_state.json")
    monkeypatch.setattr(LLMConfigService, "_state_file_path", classmethod(lambda cls: state_file))
    monkeypatch.setattr(settings, "APP_ENV", "production")

    orig_url = settings.LOCAL_LLM_BASE_URL
    orig_model = settings.LOCAL_LLM_MODEL_NAME
    orig_timeout = settings.LOCAL_LLM_TIMEOUT
    orig_sync_mtime = LLMConfigService._last_synced_state_mtime_ns
    orig_online = AIVerdictService._is_local_llm_online
    orig_probe = AIVerdictService._last_probe_time

    try:
        updated = LLMConfigService.update_config(
            LLMConfigUpdate(
                host="192.0.2.42",
                port=8000,
                protocol="http",
                model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
                timeout=90.0,
            )
        )
        assert updated.base_url == "http://192.0.2.42:8000/v1"
        assert os.path.exists(state_file)

        # Simulate another worker process having stale settings and a stale offline probe cache
        settings.LOCAL_LLM_BASE_URL = "http://127.0.0.1:8000/v1"
        settings.LOCAL_LLM_MODEL_NAME = "old-model"
        LLMConfigService._last_synced_state_mtime_ns = 0
        AIVerdictService._is_local_llm_online = False
        AIVerdictService._last_probe_time = 9999999999.0

        provider = get_model_provider("OPENAI_COMPATIBLE")
        assert provider.base_url == "http://192.0.2.42:8000/v1"
        assert settings.LOCAL_LLM_BASE_URL == "http://192.0.2.42:8000/v1"
        assert settings.LOCAL_LLM_MODEL_NAME == "Qwen/Qwen2.5-7B-Instruct-AWQ"
        assert AIVerdictService._is_local_llm_online is None
        assert AIVerdictService._last_probe_time == 0.0
    finally:
        settings.LOCAL_LLM_BASE_URL = orig_url
        settings.LOCAL_LLM_MODEL_NAME = orig_model
        settings.LOCAL_LLM_TIMEOUT = orig_timeout
        LLMConfigService._last_synced_state_mtime_ns = orig_sync_mtime
        AIVerdictService._is_local_llm_online = orig_online
        AIVerdictService._last_probe_time = orig_probe


@pytest.mark.asyncio
@respx.mock
async def test_server_2_monitor_auth_and_health_fallback(monkeypatch, tmp_path):
    """
    Verifies SystemMonitorService._sample_server_2 sends Authorization Bearer headers
    and falls back to /health when /v1/models returns 404, preventing Sidebar vs Dashboard mismatch.
    """
    state_file = str(tmp_path / "missing_llm_state.json")
    monkeypatch.setattr(LLMConfigService, "_state_file_path", classmethod(lambda cls: state_file))
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://192.0.2.77:8000/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_API_KEY", "test-secret-token")

    models_route = respx.get("http://192.0.2.77:8000/v1/models").respond(status_code=404)
    health_route = respx.get("http://192.0.2.77:8000/health").respond(status_code=200)
    respx.get("http://192.0.2.77:8000/metrics").respond(status_code=404)

    svc = SystemMonitorService(db=None)  # type: ignore[arg-type]
    s2 = await svc._sample_server_2()

    assert models_route.called
    assert health_route.called
    assert models_route.calls[0].request.headers.get("Authorization") == "Bearer test-secret-token"
    assert s2["status"] == "ONLINE"


@pytest.mark.asyncio
async def test_sentinel_worker_backlog_drain_without_25s_timeout(tmp_path, monkeypatch):
    """
    Verifies SentinelIngestWorker.run_pending_reconciliation_until_drained processes
    multiple sequential batches until pending_remaining reaches zero.
    """
    worker = SentinelIngestWorker()
    monkeypatch.setattr(worker, "_state_file", str(tmp_path / "scheduler_state.json"))

    batch_calls = [
        {"success": True, "is_llm_online": True, "processed": 25, "failed": 0, "pending_remaining": 10},
        {"success": True, "is_llm_online": True, "processed": 10, "failed": 0, "pending_remaining": 0},
    ]

    async def fake_process(self, max_count=100, username="scheduler"):
        return batch_calls.pop(0)

    with patch("app.services.fortisiem_service.FortiSIEMService.process_pending_incidents", new=fake_process):
        result = await worker.run_pending_reconciliation_until_drained(max_batch=25, max_batches=5)

    assert result["success"] is True
    assert result["processed"] == 35
    assert result["pending_remaining"] == 0
    assert worker.total_ai_verdicts_count == 35


@pytest.mark.asyncio
async def test_process_pending_verdicts_background_endpoint(client: AsyncClient, admin_token: str, monkeypatch):
    """
    Verifies POST /api/fortisiem/process-pending-verdicts?background=true starts cleanly
    without waiting for full LLM batch completion.
    """
    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", classmethod(lambda cls, force_refresh=False: _async_true()))
    monkeypatch.setattr(AIVerdictService, "get_pending_incident_count", AsyncMock(return_value=14))

    with patch("app.services.fortisiem_scheduler.fortisiem_scheduler.trigger_pending_reconciliation", return_value=True) as mock_trigger:
        res = await client.post(
            "/api/fortisiem/process-pending-verdicts?background=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["started"] is True
    assert data["pending_remaining"] == 14
    mock_trigger.assert_called_once()


async def _async_true() -> bool:
    return True

