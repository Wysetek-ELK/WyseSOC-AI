import os
import re
import sys
import json
import time
import socket
import logging
import tempfile
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
import httpx

from app.config import settings, BASE_DIR
from app.schemas.llm_config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMTestConnectionRequest,
    LLMTestConnectionResponse,
)

logger = logging.getLogger(__name__)


class LLMConfigService:
    """
    Manages dynamic runtime configuration and persistence of the Local LLM Server 2
    IP address, port, and inference parameters.
    """
    _cached_server1_ip: Optional[str] = None
    _cached_ip_timestamp: float = 0.0
    _process_start_time: float = time.time()
    _last_synced_state_mtime_ns: int = 0

    @classmethod
    def _state_file_path(cls) -> str:
        is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        filename = "test_llm_config_state.json" if is_pytest else "llm_config_state.json"
        return os.path.join(BASE_DIR, filename)

    @classmethod
    def _persist_runtime_state(cls) -> None:
        """
        Atomically writes active Server 2 configuration to a shared runtime state file
        so all Uvicorn API workers and background workers stay synchronized even in production.
        """
        state_file = cls._state_file_path()
        payload = {
            "base_url": settings.LOCAL_LLM_BASE_URL,
            "model_name": settings.LOCAL_LLM_MODEL_NAME,
            "timeout": float(settings.LOCAL_LLM_TIMEOUT),
            "allow_mock_fallback": bool(settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK),
            "updated_at": time.time(),
        }
        tmp_path: Optional[str] = None
        try:
            parent_dir = os.path.dirname(os.path.abspath(state_file))
            os.makedirs(parent_dir, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(prefix=".llm_cfg_", suffix=".tmp", dir=parent_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, state_file)
            cls._last_synced_state_mtime_ns = os.stat(state_file).st_mtime_ns
        except Exception as exc:
            logger.warning(f"Failed to persist shared LLM runtime state: {exc}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @classmethod
    def sync_runtime_settings(cls) -> bool:
        """
        Synchronizes in-memory LOCAL_LLM_* settings from the shared runtime state file
        when another worker process updates Server 2 config.
        Returns True if settings changed in the current worker process.
        """
        state_file = cls._state_file_path()
        if not os.path.exists(state_file):
            return False

        is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        try:
            st = os.stat(state_file)
            if is_pytest and (st.st_mtime_ns / 1e9) < cls._process_start_time:
                return False
            if st.st_mtime_ns <= cls._last_synced_state_mtime_ns:
                return False

            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return False

            changed = False
            new_url = str(data.get("base_url") or "").strip()
            if new_url and new_url != settings.LOCAL_LLM_BASE_URL:
                settings.LOCAL_LLM_BASE_URL = new_url
                changed = True

            new_model = str(data.get("model_name") or "").strip()
            if new_model and new_model != settings.LOCAL_LLM_MODEL_NAME:
                settings.LOCAL_LLM_MODEL_NAME = new_model
                changed = True

            if data.get("timeout") is not None:
                new_timeout = float(data["timeout"])
                if new_timeout != float(settings.LOCAL_LLM_TIMEOUT):
                    settings.LOCAL_LLM_TIMEOUT = new_timeout
                    changed = True

            if data.get("allow_mock_fallback") is not None:
                is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
                new_mock = False if is_prod else bool(data["allow_mock_fallback"])
                if new_mock != bool(settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK):
                    settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK = new_mock
                    changed = True

            cls._last_synced_state_mtime_ns = st.st_mtime_ns
            if changed:
                from app.services.ai_verdict_service import AIVerdictService
                AIVerdictService._is_local_llm_online = None
                AIVerdictService._last_probe_time = 0.0
                logger.info(
                    f"Synced shared LLM runtime config in PID {os.getpid()}: "
                    f"base_url={settings.LOCAL_LLM_BASE_URL}, model={settings.LOCAL_LLM_MODEL_NAME}"
                )
            return changed
        except Exception as exc:
            logger.debug(f"Could not sync shared LLM runtime state: {exc}")
            return False

    @staticmethod
    def parse_llm_url(
        raw_input: str,
        default_port: int = 8000,
        default_proto: str = "http",
    ) -> Dict[str, Any]:
        """
        Parses user-entered IP, hostname, or full URL into normalized components:
        (host, port, protocol, base_url).
        """
        raw = raw_input.strip()

        # Check if full URL provided
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            proto = parsed.scheme.lower()
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or (443 if proto == "https" else default_port)
            path = parsed.path.rstrip("/")
            if not path or not path.endswith("/v1"):
                path = f"{path}/v1" if path else "/v1"
            base_url = f"{proto}://{host}:{port}{path}" if parsed.port or (proto == "http" and port != 80) or (proto == "https" and port != 443) else f"{proto}://{host}{path}"
            return {
                "host": host,
                "port": port,
                "protocol": proto,
                "base_url": base_url,
            }

        # Handle host:port format
        if ":" in raw and not raw.startswith("["):
            parts = raw.split(":", 1)
            host = parts[0].strip()
            try:
                port = int(parts[1].split("/")[0].strip())
            except ValueError:
                port = default_port
        else:
            host = raw
            port = default_port

        proto = default_proto.lower()
        base_url = f"{proto}://{host}:{port}/v1"
        return {
            "host": host,
            "port": port,
            "protocol": proto,
            "base_url": base_url,
        }

    @classmethod
    async def get_server1_outbound_ip(cls) -> Optional[str]:
        """
        Resolves Server 1's network address / outbound IP without contacting external
        third-party discovery services (REQ-07 / AV-011).
        Checks settings.SERVER1_OUTBOUND_IP, then settings.SERVER1_HOST, then local hostname socket.
        """
        now = time.time()
        if cls._cached_server1_ip and (now - cls._cached_ip_timestamp < 3600):
            return cls._cached_server1_ip

        # 1. Check explicitly configured outbound IP
        configured_ip = getattr(settings, "SERVER1_OUTBOUND_IP", None)
        if configured_ip and configured_ip.strip():
            cls._cached_server1_ip = configured_ip.strip()
            cls._cached_ip_timestamp = now
            return cls._cached_server1_ip

        # 2. Check configured host if not loopback or catch-all
        configured_host = getattr(settings, "SERVER1_HOST", None)
        if configured_host and configured_host.strip() and configured_host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            cls._cached_server1_ip = configured_host.strip()
            cls._cached_ip_timestamp = now
            return cls._cached_server1_ip

        # 3. Resolve local interface IP via socket
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            if local_ip and local_ip != "127.0.0.1":
                cls._cached_server1_ip = local_ip
                cls._cached_ip_timestamp = now
                return cls._cached_server1_ip
        except Exception:
            pass

        return None

    @classmethod
    async def get_config(cls) -> LLMConfigResponse:
        """
        Returns the active LLM Server 2 configuration.
        """
        cls.sync_runtime_settings()
        parsed = cls.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
        server1_ip = await cls.get_server1_outbound_ip()

        # Check live online status from AIVerdictService (utilizes 15s cache)
        from app.services.ai_verdict_service import AIVerdictService
        try:
            is_online = await AIVerdictService.is_local_llm_available()
        except Exception:
            is_online = bool(getattr(AIVerdictService, "_is_local_llm_online", False))

        return LLMConfigResponse(
            host=parsed["host"],
            port=parsed["port"],
            protocol=parsed["protocol"],
            base_url=settings.LOCAL_LLM_BASE_URL,
            model_name=settings.LOCAL_LLM_MODEL_NAME,
            timeout=settings.LOCAL_LLM_TIMEOUT,
            allow_mock_fallback=settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
            is_online=is_online,
            server1_outbound_ip=server1_ip,
        )

    @classmethod
    def update_config(cls, data: LLMConfigUpdate) -> LLMConfigResponse:
        """
        Updates LLM Server IP, port, and inference settings dynamically in memory
        and persists them securely to the .env file.
        """
        parsed = cls.parse_llm_url(
            raw_input=data.host,
            default_port=data.port or 8000,
            default_proto=data.protocol or "http",
        )

        # 1. Update in-memory settings
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        settings.LOCAL_LLM_BASE_URL = parsed["base_url"]

        if data.model_name and data.model_name.strip():
            settings.LOCAL_LLM_MODEL_NAME = data.model_name.strip()

        if data.timeout is not None:
            settings.LOCAL_LLM_TIMEOUT = float(data.timeout)

        if data.allow_mock_fallback is not None:
            # In production, mock fallback is strictly disabled (REQ-02 / AV-004)
            settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK = False if is_prod else bool(data.allow_mock_fallback)

        # Reset online status so next evaluation/monitoring triggers a fresh probe
        from app.services.ai_verdict_service import AIVerdictService
        AIVerdictService._is_local_llm_online = None
        AIVerdictService._last_probe_time = 0.0

        # Persist shared runtime state so all Uvicorn & Celery workers pick up changes immediately
        cls._persist_runtime_state()

        # 2. Persist to backend .env file (development / staging only - avoided in production)
        if not is_prod:
            env_path = os.path.join(BASE_DIR, ".env")
            env_lines = []

            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
                        if match:
                            key = match.group(1)
                            if key in (
                                "LOCAL_LLM_BASE_URL",
                                "LOCAL_LLM_MODEL_NAME",
                                "LOCAL_LLM_TIMEOUT",
                                "LOCAL_LLM_ALLOW_MOCK_FALLBACK",
                            ):
                                continue
                        env_lines.append(line)

            # Append updated LLM variables
            env_updates = [
                f'\n# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)\n',
                f'LOCAL_LLM_BASE_URL="{settings.LOCAL_LLM_BASE_URL}"\n',
                f'LOCAL_LLM_MODEL_NAME="{settings.LOCAL_LLM_MODEL_NAME}"\n',
                f'LOCAL_LLM_TIMEOUT={settings.LOCAL_LLM_TIMEOUT}\n',
                f'LOCAL_LLM_ALLOW_MOCK_FALLBACK={"true" if settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK else "false"}\n',
            ]
            env_lines.extend(env_updates)

            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(env_lines)
                if hasattr(os, "chmod"):
                    try:
                        os.chmod(env_path, 0o600)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not persist LLM settings to {env_path}: {e}")

        logger.info(f"Updated LOCAL_LLM_BASE_URL to {settings.LOCAL_LLM_BASE_URL}")

        return LLMConfigResponse(
            host=parsed["host"],
            port=parsed["port"],
            protocol=parsed["protocol"],
            base_url=settings.LOCAL_LLM_BASE_URL,
            model_name=settings.LOCAL_LLM_MODEL_NAME,
            timeout=settings.LOCAL_LLM_TIMEOUT,
            allow_mock_fallback=settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
            is_online=False,
            server1_outbound_ip=cls._cached_server1_ip,
        )

    @classmethod
    async def test_connection(cls, req: LLMTestConnectionRequest) -> LLMTestConnectionResponse:
        """
        Probes the specified LLM server endpoint to verify reachability and model list.
        """
        parsed = cls.parse_llm_url(
            raw_input=req.host,
            default_port=req.port or 8000,
            default_proto=req.protocol or "http",
        )
        base_url = parsed["base_url"]
        models_url = f"{base_url}/models"
        timeout_sec = min(max(req.timeout or 10.0, 1.0), 30.0)

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                res = await client.get(
                    models_url,
                    headers={"Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}"},
                )
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    model_str = ", ".join(models) if models else settings.LOCAL_LLM_MODEL_NAME

                    # Mark local LLM online if testing the currently configured endpoint
                    from app.services.ai_verdict_service import AIVerdictService
                    active_parsed = cls.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
                    if base_url == active_parsed["base_url"]:
                        AIVerdictService._is_local_llm_online = True
                        AIVerdictService._last_probe_time = time.time()

                    return LLMTestConnectionResponse(
                        success=True,
                        status_code=200,
                        latency_ms=latency_ms,
                        message=f"Connection successful! Models loaded on Server 2: {model_str}",
                        models=models,
                        tested_url=models_url,
                    )
                else:
                    return LLMTestConnectionResponse(
                        success=False,
                        status_code=res.status_code,
                        latency_ms=latency_ms,
                        message=f"Server returned HTTP {res.status_code}: {res.text[:200]}",
                        models=[],
                        tested_url=models_url,
                    )
        except httpx.ConnectTimeout:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return LLMTestConnectionResponse(
                success=False,
                latency_ms=latency_ms,
                message=f"Connection timed out after {timeout_sec}s. Verify that port {parsed['port']} is open in Server 2 firewall/AWS Security Group and that Server 1's IP is whitelisted.",
                tested_url=models_url,
            )
        except httpx.ConnectError as ce:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return LLMTestConnectionResponse(
                success=False,
                latency_ms=latency_ms,
                message=f"Connection refused ({ce}). Verify that the vLLM / model server is running on Server 2 and listening on 0.0.0.0:{parsed['port']}.",
                tested_url=models_url,
            )
        except Exception as e:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return LLMTestConnectionResponse(
                success=False,
                latency_ms=latency_ms,
                message=f"Error connecting to LLM server: {str(e)}",
                tested_url=models_url,
            )
