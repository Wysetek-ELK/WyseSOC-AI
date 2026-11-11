"""
Inference & Execution Provenance Classification Helpers (Phase 9.1).

Strictly separates:
1. Configured inference provider (OPENAI_COMPATIBLE | SIMULATED | DISABLED)
2. Actual execution provenance (LIVE_PROVIDER | HTTP_MOCK | SIMULATED | POLICY_GUARD |
   PREFLIGHT_GUARD | TOKEN_BUDGET_GUARD | OFFLINE | DEGRADED | HISTORICAL)
3. Current Server 2 health (ONLINE | OFFLINE | DEGRADED | HTTP_MOCK)
4. Historical execution provenance (preserved separately from current Server 2 status)
5. Test environment identity (e.g. MOCK_HTTP_E2E | OFFLINE_PYTEST | None)
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.config import settings

GUARD_MODEL_IDENTIFIERS = {
    "POLICY_GUARD",
    "PREFLIGHT_GUARD",
    "TOKEN_BUDGET_GUARD",
    "VALIDATION_GUARD",
}

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0", "testserver", "mock-llm"}


def get_test_environment_id() -> Optional[str]:
    val = str(getattr(settings, "TEST_ENVIRONMENT_ID", "") or "").strip()
    return val or None


def is_mock_http_endpoint(
    base_url: Optional[str] = None,
    explicit_mode: Optional[str] = None,
    app_env: Optional[str] = None,
    test_env: Optional[str] = None,
) -> bool:
    """
    Determine whether the configured OpenAI-compatible HTTP endpoint is a mock/test endpoint
    (HTTP_MOCK) rather than a physically provisioned Server 2 GPU node.
    """
    mode = str(
        explicit_mode
        if explicit_mode is not None
        else getattr(settings, "LOCAL_LLM_PROVENANCE", "AUTO")
    ).strip().upper()
    if mode == "HTTP_MOCK":
        return True
    if mode == "LIVE_PROVIDER":
        return False

    env_id = str(
        test_env if test_env is not None else (get_test_environment_id() or "")
    ).strip().upper()
    if env_id and any(tok in env_id for tok in ("MOCK", "E2E", "TEST")):
        return True

    url = str(base_url if base_url is not None else (getattr(settings, "LOCAL_LLM_BASE_URL", "") or "")).strip()
    if not url:
        return False

    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").strip().lower()
    env_name = str(app_env if app_env is not None else getattr(settings, "APP_ENV", "development")).strip().lower()
    is_prod = env_name in ("production", "prod")

    # Loopback / testserver URLs in non-production environments are classified as HTTP_MOCK
    # unless explicitly overridden with LOCAL_LLM_PROVENANCE=LIVE_PROVIDER.
    if not is_prod and (host in _LOOPBACK_HOSTS or host.endswith(".mock") or host.endswith(".test")):
        return True
    return False


def classify_endpoint_status(
    *,
    is_healthy: bool,
    raw_status: Optional[str] = None,
    base_url: Optional[str] = None,
    metrics_available: bool = False,
    configured_provider: str = "OPENAI_COMPATIBLE",
    explicit_mode: Optional[str] = None,
    app_env: Optional[str] = None,
    test_env: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify current Server 2 endpoint health without conflating HTTP mocks with Server 2 GPU."""
    env_id = str(test_env if test_env is not None else (get_test_environment_id() or "")).strip() or None
    status_up = str(raw_status or ("ONLINE" if is_healthy else "OFFLINE")).strip().upper()
    mock_ep = is_mock_http_endpoint(
        base_url=base_url,
        explicit_mode=explicit_mode,
        app_env=app_env,
        test_env=env_id,
    )

    if status_up in ("OFFLINE", "UNREACHABLE"):
        current_health = "OFFLINE"
        endpoint_provenance = "OFFLINE"
        gpu_verified = False
    elif status_up == "DEGRADED":
        current_health = "DEGRADED"
        endpoint_provenance = "DEGRADED"
        gpu_verified = False
    elif is_healthy or status_up in ("ONLINE", "HEALTHY"):
        if mock_ep:
            current_health = "HTTP_MOCK"
            endpoint_provenance = "HTTP_MOCK"
            gpu_verified = False
        else:
            current_health = "ONLINE"
            endpoint_provenance = "LIVE_PROVIDER"
            gpu_verified = bool(metrics_available)
    else:
        current_health = "OFFLINE"
        endpoint_provenance = "OFFLINE"
        gpu_verified = False

    return {
        "configured_provider": configured_provider,
        "endpoint_provenance": endpoint_provenance,
        "current_s2_health": current_health,
        "is_mock_endpoint": mock_ep,
        "gpu_telemetry_verified": gpu_verified,
        "test_environment": env_id,
    }


def classify_execution_provenance(
    *,
    is_simulated: bool = False,
    model_identifier: Optional[str] = None,
    validation_status: Optional[str] = None,
    eligibility_status: Optional[str] = None,
    source_type: Optional[str] = None,
    error_message: Optional[str] = None,
    recorded_provenance: Optional[str] = None,
    recorded_test_env: Optional[str] = None,
    base_url: Optional[str] = None,
    explicit_mode: Optional[str] = None,
    is_historical_context: bool = False,
) -> Dict[str, Any]:
    """
    Classify actual execution provenance independently of current Server 2 availability.
    Preserves persisted execution-time provenance (recorded_provenance) when available.
    """
    clean_model = str(model_identifier or "").strip()
    clean_val = str(validation_status or "").strip().upper()
    clean_elig = str(eligibility_status or "").strip().upper()
    clean_err = str(error_message or "").strip().upper()
    clean_src = str(source_type or "LIVE").strip().upper()
    rec_prov = str(recorded_provenance or "").strip().upper() or None
    test_env = recorded_test_env if recorded_test_env is not None else get_test_environment_id()

    if rec_prov in {"LIVE_PROVIDER", "HTTP_MOCK", "SIMULATED", "OFFLINE", "DEGRADED"} | GUARD_MODEL_IDENTIFIERS:
        exec_prov = rec_prov
        configured_provider = (
            "SIMULATED"
            if exec_prov == "SIMULATED"
            else ("DISABLED" if exec_prov in GUARD_MODEL_IDENTIFIERS else "OPENAI_COMPATIBLE")
        )
    elif is_simulated:
        exec_prov = "SIMULATED"
        configured_provider = "SIMULATED"
    elif clean_model in GUARD_MODEL_IDENTIFIERS:
        exec_prov = clean_model
        configured_provider = "POLICY_GUARD"
    elif clean_elig == "FAILED" or "SERVER2_OFFLINE" in clean_err or clean_val == "PROVIDER_UNAVAILABLE":
        exec_prov = "OFFLINE"
        configured_provider = "OPENAI_COMPATIBLE"
    elif clean_val in ("DEGRADED", "HTTP_ERROR", "TIMEOUT"):
        exec_prov = "DEGRADED"
        configured_provider = "OPENAI_COMPATIBLE"
    elif base_url is not None or explicit_mode is not None:
        mock_ep = is_mock_http_endpoint(base_url=base_url, explicit_mode=explicit_mode, test_env=test_env or "")
        exec_prov = "HTTP_MOCK" if mock_ep else "LIVE_PROVIDER"
        configured_provider = "OPENAI_COMPATIBLE"
    else:
        # Legacy record without explicit execution provenance stored: avoid falsely claiming
        # current live GPU verification when evaluating historical rows offline.
        mock_ep = is_mock_http_endpoint(test_env=test_env or "")
        if is_historical_context or clean_src == "HISTORICAL":
            exec_prov = "HTTP_MOCK" if mock_ep else "HISTORICAL"
        else:
            exec_prov = "HTTP_MOCK" if mock_ep else "LIVE_PROVIDER"
        configured_provider = "OPENAI_COMPATIBLE"

    return {
        "execution_provenance": exec_prov,
        "configured_provider": configured_provider,
        "historical_execution_provenance": (
            f"HISTORICAL ({exec_prov})"
            if (is_historical_context or clean_src == "HISTORICAL") and exec_prov != "HISTORICAL"
            else ("HISTORICAL" if clean_src == "HISTORICAL" else exec_prov)
        ),
        "is_mock_endpoint": exec_prov == "HTTP_MOCK",
        "test_environment": test_env,
    }

