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
        Strictly excludes secrets and API tokens.
        """
        state_file = cls._state_file_path()
        payload = {
            "base_url": settings.LOCAL_LLM_BASE_URL,
            "model_name": settings.LOCAL_LLM_MODEL_NAME,
            "timeout": float(settings.LOCAL_LLM_TIMEOUT),
            "context_budget": int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096)),
            "max_tokens": int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512)),
            "verified_max_model_len": getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None),
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

            if data.get("context_budget") is not None:
                new_ctx = int(data["context_budget"])
                if 1024 <= new_ctx <= 65536 and new_ctx != int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096)):
                    settings.LOCAL_LLM_CONTEXT_BUDGET = new_ctx
                    changed = True

            if data.get("max_tokens") is not None:
                new_max_tok = int(data["max_tokens"])
                if 64 <= new_max_tok <= 4096 and new_max_tok != int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512)):
                    settings.LOCAL_LLM_MAX_TOKENS = new_max_tok
                    changed = True

            if "verified_max_model_len" in data:
                v_len = int(data["verified_max_model_len"]) if data["verified_max_model_len"] is not None else None
                if v_len != getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None):
                    settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = v_len
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

    _ENV_SECTION_HEADER = "# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)"
    _MANAGED_ENV_KEYS = (
        "LOCAL_LLM_BASE_URL",
        "LOCAL_LLM_MODEL_NAME",
        "LOCAL_LLM_TIMEOUT",
        "LOCAL_LLM_CONTEXT_BUDGET",
        "LOCAL_LLM_MAX_TOKENS",
        "LOCAL_LLM_ALLOW_MOCK_FALLBACK",
    )

    @classmethod
    def _evaluate_context_status(cls) -> Dict[str, Any]:
        ctx_budget = int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096) or 4096)
        max_tokens = int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512) or 512)
        verified_len = getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
        verified = False
        warning: Optional[str] = None
        if verified_len is not None:
            if int(verified_len) >= ctx_budget:
                verified = True
            else:
                warning = (
                    f"Configured context_budget ({ctx_budget}) exceeds Server 2 verified "
                    f"max_model_len ({verified_len}); reduce context_budget or restart vLLM with higher --max-model-len."
                )
        elif ctx_budget > 4096:
            warning = (
                f"Configured context_budget={ctx_budget} (>4096) has not been verified against live Server 2 capacity; "
                "run Test Connection or integration diagnostics before relying on >4096 tokens."
            )
        return {
            "context_budget": ctx_budget,
            "max_tokens": max_tokens,
            "verified_max_model_len": int(verified_len) if verified_len is not None else None,
            "context_budget_verified": verified,
            "context_budget_warning": warning,
            "operating_mode": getattr(settings, "resolved_operating_mode", "development"),
        }

    @classmethod
    def _upsert_env_vars(cls, env_path: str, updates: Dict[str, str]) -> None:
        """
        Idempotently updates or inserts managed keys in `.env` in-place.
        Eliminates duplicated comment headers, preserves unrelated keys,
        and never writes secrets/credentials.
        """
        existing_lines: List[str] = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        new_lines: List[str] = []
        seen_keys: set[str] = set()
        header_seen = False

        for line in existing_lines:
            stripped = line.strip()
            if stripped == cls._ENV_SECTION_HEADER:
                if header_seen:
                    # Drop duplicate repeated section headers appended by legacy builds
                    if new_lines and not new_lines[-1].strip():
                        new_lines.pop()
                    continue
                header_seen = True
                new_lines.append(line if line.endswith("\n") else f"{line}\n")
                continue

            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if match:
                key = match.group(1)
                if key in updates:
                    if key not in seen_keys:
                        seen_keys.add(key)
                        new_lines.append(f"{key}={updates[key]}\n")
                    continue
            new_lines.append(line)

        missing_keys = [k for k in updates if k not in seen_keys]
        if missing_keys:
            if new_lines and new_lines[-1].strip():
                new_lines.append("\n")
            if not header_seen:
                new_lines.append(f"{cls._ENV_SECTION_HEADER}\n")
            for k in missing_keys:
                new_lines.append(f"{k}={updates[k]}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        if hasattr(os, "chmod"):
            try:
                os.chmod(env_path, 0o600)
            except Exception:
                pass

    @classmethod
    async def get_config(cls) -> LLMConfigResponse:
        """
        Returns the active LLM Server 2 configuration.
        """
        cls.sync_runtime_settings()
        parsed = cls.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
        server1_ip = await cls.get_server1_outbound_ip()
        ctx_info = cls._evaluate_context_status()

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
            context_budget=ctx_info["context_budget"],
            max_tokens=ctx_info["max_tokens"],
            verified_max_model_len=ctx_info["verified_max_model_len"],
            context_budget_verified=ctx_info["context_budget_verified"],
            context_budget_warning=ctx_info["context_budget_warning"],
            operating_mode=ctx_info["operating_mode"],
            allow_mock_fallback=settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
            is_online=is_online,
            server1_outbound_ip=server1_ip,
        )

    @classmethod
    def update_config(cls, data: LLMConfigUpdate) -> LLMConfigResponse:
        """
        Updates LLM Server IP, port, context budget, and inference settings dynamically in memory
        and persists non-secret configuration idempotently to `.env` in non-production environments.
        """
        parsed = cls.parse_llm_url(
            raw_input=data.host,
            default_port=data.port or 8000,
            default_proto=data.protocol or "http",
        )

        # 1. Update in-memory settings
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        previous_base_url = settings.LOCAL_LLM_BASE_URL
        settings.LOCAL_LLM_BASE_URL = parsed["base_url"]
        if parsed["base_url"] != previous_base_url:
            settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = None

        if data.model_name and data.model_name.strip():
            new_model = data.model_name.strip()
            if new_model != settings.LOCAL_LLM_MODEL_NAME:
                settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = None
            settings.LOCAL_LLM_MODEL_NAME = new_model

        if data.timeout is not None:
            settings.LOCAL_LLM_TIMEOUT = float(data.timeout)

        new_ctx = int(data.context_budget) if data.context_budget is not None else int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096))
        new_max_tok = int(data.max_tokens) if data.max_tokens is not None else int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512))
        if (new_ctx - new_max_tok) < 512:
            raise ValueError(
                f"Invalid context budget ({new_ctx}) and max_tokens ({new_max_tok}): must leave at least 512 prompt tokens."
            )
        settings.LOCAL_LLM_CONTEXT_BUDGET = new_ctx
        settings.LOCAL_LLM_MAX_TOKENS = new_max_tok

        if data.allow_mock_fallback is not None:
            # In production, mock fallback is strictly disabled (REQ-02 / AV-004 / AIS-F12)
            settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK = False if is_prod else bool(data.allow_mock_fallback)

        # Reset online status so next evaluation/monitoring triggers a fresh probe
        from app.services.ai_verdict_service import AIVerdictService
        AIVerdictService._is_local_llm_online = None
        AIVerdictService._last_probe_time = 0.0

        # Persist shared runtime state so all Uvicorn & Celery workers pick up changes immediately
        cls._persist_runtime_state()

        # 2. Persist non-secret settings idempotently to backend .env file (dev/staging only)
        if not is_prod:
            env_path = os.path.join(BASE_DIR, ".env")
            env_updates = {
                "LOCAL_LLM_BASE_URL": f'"{settings.LOCAL_LLM_BASE_URL}"',
                "LOCAL_LLM_MODEL_NAME": f'"{settings.LOCAL_LLM_MODEL_NAME}"',
                "LOCAL_LLM_TIMEOUT": str(settings.LOCAL_LLM_TIMEOUT),
                "LOCAL_LLM_CONTEXT_BUDGET": str(settings.LOCAL_LLM_CONTEXT_BUDGET),
                "LOCAL_LLM_MAX_TOKENS": str(settings.LOCAL_LLM_MAX_TOKENS),
                "LOCAL_LLM_ALLOW_MOCK_FALLBACK": "true" if settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK else "false",
            }
            try:
                cls._upsert_env_vars(env_path, env_updates)
            except Exception as e:
                logger.warning(f"Could not persist LLM settings to {env_path}: {e}")

        logger.info("Updated LOCAL_LLM configuration in runtime state (credentials omitted).")
        ctx_info = cls._evaluate_context_status()

        return LLMConfigResponse(
            host=parsed["host"],
            port=parsed["port"],
            protocol=parsed["protocol"],
            base_url=settings.LOCAL_LLM_BASE_URL,
            model_name=settings.LOCAL_LLM_MODEL_NAME,
            timeout=settings.LOCAL_LLM_TIMEOUT,
            context_budget=ctx_info["context_budget"],
            max_tokens=ctx_info["max_tokens"],
            verified_max_model_len=ctx_info["verified_max_model_len"],
            context_budget_verified=ctx_info["context_budget_verified"],
            context_budget_warning=ctx_info["context_budget_warning"],
            operating_mode=ctx_info["operating_mode"],
            allow_mock_fallback=settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
            is_online=False,
            server1_outbound_ip=cls._cached_server1_ip,
        )

    @staticmethod
    def _extract_max_model_len(models_payload: Dict[str, Any], preferred_model: Optional[str] = None) -> Optional[int]:
        entries = models_payload.get("data") or []
        if not isinstance(entries, list):
            return None
        preferred_match: Optional[int] = None
        fallback_len: Optional[int] = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw_len = entry.get("max_model_len") or entry.get("context_length")
            if raw_len is None:
                continue
            try:
                parsed_len = int(raw_len)
            except (TypeError, ValueError):
                continue
            if parsed_len <= 0:
                continue
            if preferred_model and str(entry.get("id", "")).strip() == preferred_model.strip():
                preferred_match = parsed_len
            elif fallback_len is None:
                fallback_len = parsed_len
        return preferred_match if preferred_match is not None else fallback_len

    @classmethod
    async def test_connection(cls, req: LLMTestConnectionRequest) -> LLMTestConnectionResponse:
        """
        Probes the specified LLM server endpoint to verify reachability, model list,
        and exposed `max_model_len` capacity without assuming support beyond Server 2 telemetry.
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
                    models = [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]
                    model_str = ", ".join(models) if models else settings.LOCAL_LLM_MODEL_NAME
                    server_max_len = cls._extract_max_model_len(data, settings.LOCAL_LLM_MODEL_NAME)
                    configured_budget = int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096) or 4096)
                    supported: Optional[bool] = (
                        (server_max_len >= configured_budget) if server_max_len is not None else None
                    )

                    from app.services.ai_verdict_service import AIVerdictService
                    active_parsed = cls.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
                    if base_url == active_parsed["base_url"]:
                        AIVerdictService._is_local_llm_online = True
                        AIVerdictService._last_probe_time = time.time()
                        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = server_max_len
                        cls._persist_runtime_state()

                    capacity_note = (
                        f" | max_model_len={server_max_len} ({'supports' if supported else 'BELOW'} configured {configured_budget})"
                        if server_max_len is not None
                        else " | max_model_len not exposed by server (capacity unverified)"
                    )

                    return LLMTestConnectionResponse(
                        success=True,
                        status_code=200,
                        latency_ms=latency_ms,
                        message=f"Connection successful! Models loaded on Server 2: {model_str}{capacity_note}",
                        models=models,
                        tested_url=models_url,
                        server_max_model_len=server_max_len,
                        context_budget_supported=supported,
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
