# AIS 2.3 Configuration Hardening & Operating Mode Readiness (`AIS-F12`)

## 1. `.env` Persistence Remediation (`LLMConfigService`)

- **Defect (`AIS-F12`):** `LLMConfigService.update_config()` previously stripped `LOCAL_LLM_*` key lines while leaving prior `# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)` header comments intact and appending a duplicate block on every update.
- **Fix (`backend/app/services/llm_config_service.py`):**
  - Replaced append logic with `_upsert_env_vars()` performing deterministic in-place key replacement (`LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL_NAME`, `LOCAL_LLM_TIMEOUT`, `LOCAL_LLM_CONTEXT_BUDGET`, `LOCAL_LLM_MAX_TOKENS`, `LOCAL_LLM_ALLOW_MOCK_FALLBACK`), deduplicating repeated header comments, preserving unrelated keys, and never writing secrets/API tokens (`LOCAL_LLM_API_KEY`, `SECRET_KEY`, `FORTISIEM_PASSWORD`).
  - Extended atomic JSON worker-sync state (`llm_config_state.json`) to synchronize `context_budget`, `max_tokens`, and runtime `verified_max_model_len` across Uvicorn and Celery workers.
  - Hardened `FortiSIEMService.update_config()` (`backend/app/services/fortisiem_service.py`) so `FORTISIEM_MOCK_FALLBACK` is forced `False` when `APP_ENV` is `production`.

## 2. Separated Operating Modes (`PLATFORM_OPERATING_MODE`)

| Mode | SQLite Permitted | Mock Fallback Permitted | Async Celery Expected | Auto Closure / SIEM Writeback | Intended Phase |
| --- | --- | --- | --- | --- | --- |
| `development` | Yes | Opt-in only | Optional | Never | Local unit/dev testing (forbidden in `APP_ENV=production`) |
| `integration` | Yes | Never (`LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`) | Recommended | Never | Server 1 + Server 2 pre-prod live LLM verification |
| `shadow` | No (PostgreSQL required) | Never | Required | Never | Read-only live inference telemetry shadow validation |
| `advisory` | No (PostgreSQL required) | Never | Required | Never (human analyst review required) | Production analyst-assisted triage (default in `APP_ENV=production`) |
| `autonomous` | No (PostgreSQL required) | Never | Required | Gated strictly by G1-G8 empirical non-simulated certification | Strictly controlled rule-level automation |

## 3. Fail-Closed Production Validation & Secret Redaction (`RuntimeConfigValidator`)

- Implemented `RuntimeConfigValidator` (`backend/app/services/runtime_config_service.py`):
  - **`validate_all(cfg, strict_production_dependencies=...)`:** Validates `APP_ENV`, `PLATFORM_OPERATING_MODE`, `SECRET_KEY`, `AUDIT_SIGNING_KEY`, PostgreSQL `DATABASE_URL` / `SYNC_DATABASE_URL`, Redis/Celery URLs, Server 2 `LOCAL_LLM_*` endpoint and context capacity assumptions, and FortiSIEM TLS/host/mock flags.
  - **`enforce_fail_closed(cfg)`:** Raises `RuntimeError` if critical blockers exist in `production` or protected operating modes (`shadow`, `advisory`, `autonomous`) — preventing silent fallback to SQLite, placeholder credentials, or mock inference.
  - **`export_redacted_snapshot(cfg)` / `mask_secret()` / `redact_url_credentials()`:** Guarantees zero plaintext secrets, passwords, API keys, JWT keys, or HMAC signing keys appear in diagnostic exports or logs.
- Updated `deployment/env.production.example` to document `PLATFORM_OPERATING_MODE="advisory"` and validated `LOCAL_LLM_CONTEXT_BUDGET` (`4096` / `8192`) requirements.

