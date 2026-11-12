"""
Runtime Configuration Hardening & Readiness Validator (AIS 2.3 / AIS-F12).

Centralizes configuration validation for PostgreSQL, Redis/Celery, FortiSIEM,
Server 2 local LLM, context budgets, and separated operating modes
(`development`, `integration`, `shadow`, `advisory`, `autonomous`) while strictly
redacting all credentials, passwords, keys, and tokens from exported diagnostics.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import (
    KNOWN_INSECURE_SECRETS,
    PRODUCTION_SAFE_MODES,
    SUPPORTED_OPERATING_MODES,
    VALIDATED_CONTEXT_BUDGET_TIERS,
    Settings,
    settings as default_settings,
)

logger = logging.getLogger("ai_verdict.runtime_config")

_PLACEHOLDER_MARKERS = (
    "replace_with",
    "changeme",
    "placeholder",
    "example_password",
    "<password>",
)

_OPERATING_MODE_PROFILES: Dict[str, Dict[str, Any]] = {
    "development": {
        "allows_sqlite": True,
        "allows_mock_fallback": True,
        "allows_auto_incident_closure": False,
        "allows_siem_writeback": False,
        "requires_celery_redis": False,
        "description": "Local developer/CI mode supporting SQLite and explicit lab simulation.",
    },
    "integration": {
        "allows_sqlite": True,
        "allows_mock_fallback": False,
        "allows_auto_incident_closure": False,
        "allows_siem_writeback": False,
        "requires_celery_redis": False,
        "description": "Server 1 + Server 2 pre-production integration verification; real LLM expected, no automatic SIEM actions.",
    },
    "shadow": {
        "allows_sqlite": False,
        "allows_mock_fallback": False,
        "allows_auto_incident_closure": False,
        "allows_siem_writeback": False,
        "requires_celery_redis": True,
        "description": "Read-only shadow inference in production; predictions recorded for audit only.",
    },
    "advisory": {
        "allows_sqlite": False,
        "allows_mock_fallback": False,
        "allows_auto_incident_closure": False,
        "allows_siem_writeback": False,
        "requires_celery_redis": True,
        "description": "Production analyst-assisted triage requiring human review prior to incident closure.",
    },
    "autonomous": {
        "allows_sqlite": False,
        "allows_mock_fallback": False,
        "allows_auto_incident_closure": True,
        "allows_siem_writeback": True,
        "requires_celery_redis": True,
        "description": "Restricted production mode permitting autonomous closure ONLY for G1-G8 empirically certified policies.",
    },
}


def mask_secret(value: Optional[str]) -> str:
    """Never reveal raw keys/tokens in logs or diagnostic output."""
    if not value or not str(value).strip():
        return "<unset>"
    s = str(value).strip()
    if s.upper() == "EMPTY":
        return "EMPTY"
    return f"<redacted:len={len(s)}>"


def redact_url_credentials(raw_url: Optional[str]) -> str:
    """Masks user:password credentials and optional sensitive query tokens inside URLs."""
    if not raw_url or not str(raw_url).strip():
        return ""
    s = str(raw_url).strip()
    redacted = re.sub(r"://([^:/@\s]+):([^@/\s]+)@", r"://\1:***@", s)
    redacted = re.sub(r"://([^@/\s]+)@", r"://***@", redacted)
    return redacted


def _contains_placeholder(value: Optional[str]) -> bool:
    if not value:
        return False
    low = str(value).lower()
    return any(marker in low for marker in _PLACEHOLDER_MARKERS)


class RuntimeConfigValidator:
    """Validates Server 1 & Server 2 configuration health and mode compliance."""

    @classmethod
    def get_mode_profile(cls, mode: str) -> Dict[str, Any]:
        return dict(_OPERATING_MODE_PROFILES.get(mode.lower().strip(), _OPERATING_MODE_PROFILES["advisory"]))

    @classmethod
    def validate_all(
        cls,
        cfg: Optional[Settings] = None,
        *,
        strict_production_dependencies: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates configuration completeness, fail-closed safety guards, context capacity
        assumptions, and mode boundaries without mutating state or leaking secrets.
        """
        s = cfg or default_settings
        app_env = str(getattr(s, "APP_ENV", "development") or "development").lower().strip()
        is_prod = app_env in ("production", "prod")
        mode = (
            getattr(s, "resolved_operating_mode", None)
            or (getattr(s, "PLATFORM_OPERATING_MODE", "") or ("advisory" if is_prod else "development"))
        )
        mode = str(mode).lower().strip()
        profile = cls.get_mode_profile(mode)

        blockers: List[str] = []
        warnings: List[str] = []

        if mode not in SUPPORTED_OPERATING_MODES:
            blockers.append(
                f"INVALID_OPERATING_MODE: '{mode}' is not one of {sorted(SUPPORTED_OPERATING_MODES)}."
            )

        if is_prod and mode not in PRODUCTION_SAFE_MODES and mode != "integration":
            blockers.append(
                f"UNSAFE_PRODUCTION_MODE: APP_ENV='{app_env}' cannot run in '{mode}' mode."
            )

        # 1. Security & Cryptographic Secrets
        secret_key = str(getattr(s, "SECRET_KEY", "") or "")
        audit_key = str(getattr(s, "AUDIT_SIGNING_KEY", "") or "")
        if is_prod:
            if not secret_key or secret_key in KNOWN_INSECURE_SECRETS or len(secret_key) < 32 or _contains_placeholder(secret_key):
                blockers.append("PRODUCTION_SECRET_KEY_INVALID: Strong 32+ char SECRET_KEY is required.")
            if not audit_key or audit_key in KNOWN_INSECURE_SECRETS or len(audit_key) < 32 or _contains_placeholder(audit_key):
                blockers.append("PRODUCTION_AUDIT_SIGNING_KEY_MISSING: Strong AUDIT_SIGNING_KEY recommended/required in production.")
            if not bool(getattr(s, "COOKIE_SECURE", False)):
                warnings.append("COOKIE_SECURE_DISABLED: COOKIE_SECURE=false in production risks HTTP cookie exposure.")

        # 2. Database (PostgreSQL vs SQLite)
        db_url = str(getattr(s, "DATABASE_URL", "") or "")
        sync_db_url = str(getattr(s, "SYNC_DATABASE_URL", "") or "")
        is_postgres_async = "postgres" in db_url.lower()
        is_postgres_sync = "postgres" in sync_db_url.lower()

        if _contains_placeholder(db_url) or _contains_placeholder(sync_db_url):
            blockers.append("DATABASE_URL_PLACEHOLDER: Replace template DB password before deployment.")
        if not profile["allows_sqlite"] and not is_postgres_async:
            msg = f"NON_POSTGRES_DB_FOR_MODE: Mode '{mode}' requires PostgreSQL, got '{redact_url_credentials(db_url)}'."
            if is_prod or strict_production_dependencies:
                blockers.append(msg)
            else:
                warnings.append(msg)
        if is_postgres_async != is_postgres_sync:
            warnings.append("DB_URL_DRIVER_MISMATCH: DATABASE_URL and SYNC_DATABASE_URL point to different database backends.")

        # 3. Redis / Celery
        redis_url = str(getattr(s, "REDIS_URL", "") or "")
        broker_url = str(getattr(s, "CELERY_BROKER_URL", "") or "")
        backend_url = str(getattr(s, "CELERY_RESULT_BACKEND", "") or "")
        use_celery = bool(getattr(s, "USE_ASYNC_CELERY", False))

        if profile["requires_celery_redis"] and not use_celery:
            msg = f"CELERY_DISABLED_IN_MODE: Mode '{mode}' should run with USE_ASYNC_CELERY=true."
            if is_prod and strict_production_dependencies:
                blockers.append(msg)
            else:
                warnings.append(msg)
        if use_celery and not (redis_url and broker_url and backend_url):
            blockers.append("REDIS_CELERY_URLS_INCOMPLETE: REDIS_URL, CELERY_BROKER_URL, and CELERY_RESULT_BACKEND must be configured.")
        if _contains_placeholder(redis_url) or _contains_placeholder(broker_url):
            blockers.append("REDIS_URL_PLACEHOLDER: Replace template Redis URL.")

        # 4. Local LLM (Server 2) & Mock Fallback Fail-Closed
        llm_base = str(getattr(s, "LOCAL_LLM_BASE_URL", "") or "")
        llm_model = str(getattr(s, "LOCAL_LLM_MODEL_NAME", "") or "")
        llm_mock = bool(getattr(s, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False))
        ctx_budget = int(getattr(s, "LOCAL_LLM_CONTEXT_BUDGET", 16384) or 16384)
        max_tokens = int(getattr(s, "LOCAL_LLM_MAX_TOKENS", 1024) or 1024)
        target_input = int(getattr(s, "LOCAL_LLM_TARGET_INPUT_BUDGET", 8192) or 8192)
        verified_max_model_len = getattr(s, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)

        if not llm_base:
            blockers.append("LOCAL_LLM_BASE_URL_MISSING: Server 2 LLM endpoint URL is required.")
        elif _contains_placeholder(llm_base):
            blockers.append("LOCAL_LLM_BASE_URL_PLACEHOLDER: Replace template Server 2 host before integration/production.")

        parsed_llm = urlparse(llm_base)
        if parsed_llm.scheme not in ("http", "https"):
            blockers.append(f"LOCAL_LLM_INVALID_SCHEME: Expected http/https scheme for '{redact_url_credentials(llm_base)}'.")
        if mode in ("integration", "shadow", "advisory", "autonomous") and (parsed_llm.hostname in ("127.0.0.1", "localhost")):
            warnings.append("LOCAL_LLM_LOOPBACK_HOST: LOCAL_LLM_BASE_URL points to localhost; Server 2 remote GPU host is expected.")

        if llm_mock and not profile["allows_mock_fallback"]:
            blockers.append(
                f"LLM_MOCK_FALLBACK_FORBIDDEN: LOCAL_LLM_ALLOW_MOCK_FALLBACK=true is prohibited in mode '{mode}' / APP_ENV='{app_env}'."
            )

        if not llm_model.strip():
            blockers.append("LOCAL_LLM_MODEL_NAME_MISSING: Active model identifier cannot be blank.")

        if ctx_budget < 1024 or ctx_budget > 131072:
            blockers.append(f"INVALID_CONTEXT_BUDGET: LOCAL_LLM_CONTEXT_BUDGET={ctx_budget} out of supported range 1024..131072.")
        elif (ctx_budget - max_tokens) < 512:
            blockers.append(
                f"INSUFFICIENT_PROMPT_HEADROOM: LOCAL_LLM_CONTEXT_BUDGET ({ctx_budget}) - LOCAL_LLM_MAX_TOKENS ({max_tokens}) < 512."
            )

        context_capacity_status = "UNVERIFIED"
        if verified_max_model_len is not None:
            if int(verified_max_model_len) < ctx_budget:
                blockers.append(
                    f"CONTEXT_BUDGET_EXCEEDS_SERVER_CAPACITY: Configured LOCAL_LLM_CONTEXT_BUDGET={ctx_budget} exceeds "
                    f"Server 2 verified max_model_len={verified_max_model_len}."
                )
                context_capacity_status = "EXCEEDS_VERIFIED_LIMIT"
            else:
                context_capacity_status = "VERIFIED"
        elif ctx_budget > 16384:
            warnings.append(
                f"UNVERIFIED_EXTENDED_CONTEXT_BUDGET: LOCAL_LLM_CONTEXT_BUDGET={ctx_budget} (>16384) configured without live "
                "Server 2 max_model_len confirmation; do not assume Server 2 supports this context length until probed."
            )

        # 5. FortiSIEM Integration
        siem_host = str(getattr(s, "FORTISIEM_HOST", "") or "").strip()
        siem_mock = bool(getattr(s, "FORTISIEM_MOCK_FALLBACK", False))
        siem_verify_ssl = bool(getattr(s, "FORTISIEM_VERIFY_SSL", False))
        siem_auto_poll = bool(getattr(s, "FORTISIEM_AUTO_POLL_ENABLED", False))

        if siem_mock and not profile["allows_mock_fallback"]:
            blockers.append(
                f"FORTISIEM_MOCK_FALLBACK_FORBIDDEN: FORTISIEM_MOCK_FALLBACK=true is prohibited in mode '{mode}' / APP_ENV='{app_env}'."
            )
        if siem_host:
            parsed_siem = urlparse(siem_host)
            if parsed_siem.scheme != "https":
                warnings.append("FORTISIEM_NON_HTTPS: FortiSIEM integration should use HTTPS.")
            if is_prod and not siem_verify_ssl:
                warnings.append("FORTISIEM_SSL_VERIFY_DISABLED: FORTISIEM_VERIFY_SSL=false weakens TLS verification in production.")
        elif siem_auto_poll:
            blockers.append("FORTISIEM_AUTO_POLL_NO_HOST: FORTISIEM_AUTO_POLL_ENABLED=true without FORTISIEM_HOST.")

        status = "BLOCKED" if blockers else ("WARNING" if warnings else "READY")
        return {
            "status": status,
            "app_env": app_env,
            "operating_mode": mode,
            "mode_profile": profile,
            "is_production_env": is_prod,
            "fail_closed_mock_disabled": (not llm_mock) and (not siem_mock),
            "context_budget": {
                "configured_context_budget": ctx_budget,
                "reserved_completion_tokens": max_tokens,
                "target_input_budget": target_input,
                "available_prompt_budget": max(512, ctx_budget - max_tokens),
                "validated_tiers": list(VALIDATED_CONTEXT_BUDGET_TIERS),
                "verified_server_max_model_len": verified_max_model_len,
                "capacity_verification_status": context_capacity_status,
            },
            "redacted_snapshot": cls.export_redacted_snapshot(s),
            "blockers": blockers,
            "warnings": warnings,
        }

    @classmethod
    def enforce_fail_closed(cls, cfg: Optional[Settings] = None) -> Dict[str, Any]:
        """Raises RuntimeError if critical blockers exist in strict production or protected operating modes."""
        report = cls.validate_all(cfg, strict_production_dependencies=True)
        if report["blockers"] and (
            report["is_production_env"] or report["operating_mode"] in PRODUCTION_SAFE_MODES
        ):
            raise RuntimeError(
                "Fail-Closed Configuration Blocker(s) detected: " + " | ".join(report["blockers"])
            )
        return report

    @classmethod
    def export_redacted_snapshot(cls, cfg: Optional[Settings] = None) -> Dict[str, Any]:
        """Exports complete configuration state with all secrets, credentials, and keys redacted."""
        s = cfg or default_settings
        return {
            "app_env": getattr(s, "APP_ENV", "development"),
            "operating_mode": getattr(
                s,
                "resolved_operating_mode",
                getattr(s, "PLATFORM_OPERATING_MODE", "development"),
            ),
            "secret_key": mask_secret(getattr(s, "SECRET_KEY", "")),
            "audit_signing_key": mask_secret(getattr(s, "AUDIT_SIGNING_KEY", "")),
            "database_url": redact_url_credentials(getattr(s, "DATABASE_URL", "")),
            "sync_database_url": redact_url_credentials(getattr(s, "SYNC_DATABASE_URL", "")),
            "redis_url": redact_url_credentials(getattr(s, "REDIS_URL", "")),
            "celery_broker_url": redact_url_credentials(getattr(s, "CELERY_BROKER_URL", "")),
            "celery_result_backend": redact_url_credentials(getattr(s, "CELERY_RESULT_BACKEND", "")),
            "use_async_celery": bool(getattr(s, "USE_ASYNC_CELERY", False)),
            "local_llm_base_url": redact_url_credentials(getattr(s, "LOCAL_LLM_BASE_URL", "")),
            "local_llm_model_name": getattr(s, "LOCAL_LLM_MODEL_NAME", ""),
            "local_llm_api_key": mask_secret(getattr(s, "LOCAL_LLM_API_KEY", "")),
            "local_llm_timeout": float(getattr(s, "LOCAL_LLM_TIMEOUT", 60.0)),
            "local_llm_context_budget": int(getattr(s, "LOCAL_LLM_CONTEXT_BUDGET", 16384)),
            "local_llm_max_tokens": int(getattr(s, "LOCAL_LLM_MAX_TOKENS", 1024)),
            "local_llm_target_input_budget": int(getattr(s, "LOCAL_LLM_TARGET_INPUT_BUDGET", 8192)),
            "local_llm_verified_max_model_len": getattr(s, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None),
            "local_llm_allow_mock_fallback": bool(getattr(s, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)),
            "fortisiem_host": redact_url_credentials(getattr(s, "FORTISIEM_HOST", "")),
            "fortisiem_username": "<configured>" if getattr(s, "FORTISIEM_USERNAME", "") else "<unset>",
            "fortisiem_password": mask_secret(getattr(s, "FORTISIEM_PASSWORD", "")),
            "fortisiem_verify_ssl": bool(getattr(s, "FORTISIEM_VERIFY_SSL", False)),
            "fortisiem_mock_fallback": bool(getattr(s, "FORTISIEM_MOCK_FALLBACK", False)),
            "fortisiem_auto_poll_enabled": bool(getattr(s, "FORTISIEM_AUTO_POLL_ENABLED", False)),
            "fortisiem_auto_ai_verdict": bool(getattr(s, "FORTISIEM_AUTO_AI_VERDICT", True)),
        }

