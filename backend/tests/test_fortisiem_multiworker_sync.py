import os
import pytest
from app.config import settings
from app.schemas.fortisiem import FortiSIEMConfigUpdate
from app.services.fortisiem_service import FortiSIEMService


@pytest.mark.asyncio
async def test_multiworker_fortisiem_config_sync_in_production_mode(monkeypatch, tmp_path):
    """
    Verifies that when Worker 1 updates the FortiSIEM host in production mode (APP_ENV=production):
    1. The new host is persisted to the shared runtime state file.
    2. The non-secret config is persisted to .env on disk across all environments.
    3. The password is strictly NOT saved in plaintext in .env.
    4. Worker 2 (starting with stale in-memory settings) automatically detects the state update
       and returns the new host on get_config() / page refresh.
    """
    state_file = str(tmp_path / "fortisiem_config_state.json")
    fake_env = tmp_path / ".env"
    fake_env.write_text("FORTISIEM_HOST=\"https://172.27.27.31\"\nFORTISIEM_USERNAME=\"super/old\"\n", encoding="utf-8")

    monkeypatch.setattr(FortiSIEMService, "_state_file_path", classmethod(lambda cls: state_file))
    from app.services import fortisiem_service
    monkeypatch.setattr(fortisiem_service, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "APP_ENV", "production")

    orig_host = settings.FORTISIEM_HOST
    orig_user = settings.FORTISIEM_USERNAME
    orig_sync_mtime = FortiSIEMService._last_synced_state_mtime_ns

    try:
        # Worker 1 updates config to 172.26.26.31
        updated = FortiSIEMService.update_config(
            FortiSIEMConfigUpdate(
                host="https://172.26.26.31",
                username="super/test",
                password="TestPassword123!",
                timeout=25.0,
                verify_ssl=False,
                mock_fallback=False,
            )
        )
        assert updated["host"] == "https://172.26.26.31"
        assert updated["username"] == "super/test"
        assert os.path.exists(state_file)

        # Verify .env was persisted with new host and NO plaintext password
        env_content = fake_env.read_text(encoding="utf-8")
        assert "172.26.26.31" in env_content
        assert "super/test" in env_content
        assert "TestPassword123!" not in env_content
        assert "FORTISIEM_PASSWORD" not in env_content

        # Simulate Worker 2 having stale in-memory settings (172.27.27.31)
        settings.FORTISIEM_HOST = "https://172.27.27.31"
        settings.FORTISIEM_USERNAME = "super/old"
        FortiSIEMService._last_synced_state_mtime_ns = 0

        # Worker 2 calls get_config() (e.g. on page refresh)
        cfg2 = FortiSIEMService.get_config()
        assert cfg2["host"] == "https://172.26.26.31"
        assert cfg2["username"] == "super/test"
        assert settings.FORTISIEM_HOST == "https://172.26.26.31"
        assert settings.FORTISIEM_USERNAME == "super/test"
    finally:
        settings.FORTISIEM_HOST = orig_host
        settings.FORTISIEM_USERNAME = orig_user
        FortiSIEMService._last_synced_state_mtime_ns = orig_sync_mtime
