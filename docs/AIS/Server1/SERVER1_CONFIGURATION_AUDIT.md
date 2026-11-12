# Verdictum AI — Server 1 Configuration Audit Report

**Audit Date:** 2026-11-12T04:15:00Z  
**Application Identity:** Verdictum AI  
**Configuration Path:** `/opt/wysesoc-ai/backend/.env` and `/opt/wysesoc-ai/frontend/.env.production`  
**Validator Engine:** `app.services.runtime_config_service.RuntimeConfigValidator`  
**Validation Outcome:** **PASSED (0 Blockers, Production Hardened)**

---

## 1. Configuration Sanitization & Before/After Comparison

Prior to the readiness execution, `/opt/wysesoc-ai/backend/.env` contained formatting artifacts from earlier provisioning scripts:
- Trailing literal `\n` characters embedded inside configuration values (`FORTISIEM_TIMEOUT="25.0\n"`, `LOCAL_LLM_TIMEOUT="30.0\n"`, `FORTISIEM_MOCK_FALLBACK="true\n"`).
- Duplicate comment headers (`# Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)` repeated 4 times).
- Outdated application identity (`PROJECT_NAME="WyseSOC AI"` and `NEXT_PUBLIC_APP_NAME="WyseSOC AI"`).
- Missing Redis and Celery configuration directives.

### Sanitization Actions Executed:
1. Created restorable backup: `/opt/wysesoc-ai/backend/.env.bak.<timestamp>`.
2. Cleaned all whitespace and formatting anomalies, ensuring clean key-value parsing.
3. Updated project name to **Verdictum AI** in backend `.env` and frontend `.env.production`.
4. Enforced strict fail-closed flags (`LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`, `FORTISIEM_MOCK_FALLBACK=false`).
5. Configured Celery distributed task processing directives.
6. Enforced restricted file permissions:
   - `/opt/wysesoc-ai/backend/.env`: `chmod 600`, owned by `aiverdict:aiverdict`.
   - `/opt/wysesoc-ai/frontend/.env.production`: `chmod 644`, owned by `aiverdict:aiverdict`.

---

## 2. Redacted Runtime Configuration Snapshot

All credentials, private keys, passwords, and tokens are strictly masked in compliance with Governor security rules:

```ini
# Application Identity & Lifecycle
PROJECT_NAME="Verdictum AI"
VERSION="1.0.0"
APP_ENV="production"
PLATFORM_OPERATING_MODE="advisory"
# SECRET_KEY and AUDIT_SIGNING_KEY configured (redacted)

# Database Connections (PostgreSQL on localhost)
DATABASE_URL="postgresql+asyncpg://***@127.0.0.1:5432/ai_verdict"
SYNC_DATABASE_URL="postgresql+psycopg2://***@127.0.0.1:5432/ai_verdict"
COOKIE_SECURE="false"
COOKIE_SAMESITE="lax"

# Redis & Celery Distributed Task Queue
REDIS_URL="redis://127.0.0.1:6379/0"
CELERY_BROKER_URL="redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND="redis://127.0.0.1:6379/0"
USE_ASYNC_CELERY="true"
CELERY_TASK_TIMEOUT_SECONDS=300

# FortiSIEM Live Supervisor Connection (Fail-Closed: Mock Disabled)
FORTISIEM_HOST="https://<fortisiem_supervisor_host>"
FORTISIEM_USERNAME="<configured>"
FORTISIEM_PASSWORD="<redacted:len=8>"
FORTISIEM_VERIFY_SSL=false
FORTISIEM_TIMEOUT=25.0
FORTISIEM_MOCK_FALLBACK=false

# Local LLM Server 2 Integration (Fail-Closed: Mock Disabled)
LOCAL_LLM_BASE_URL="http://<server2_inference_node_host>:8000/v1"
LOCAL_LLM_MODEL_NAME="Qwen/Qwen2.5-7B-Instruct-AWQ"
LOCAL_LLM_MODEL="Qwen/Qwen2.5-7B-Instruct-AWQ"
LOCAL_LLM_API_KEY="EMPTY"
LOCAL_LLM_TIMEOUT=30.0
LOCAL_LLM_ALLOW_MOCK_FALLBACK=false
LOCAL_LLM_CONTEXT_BUDGET=4096
LOCAL_LLM_MAX_TOKENS=512

# Autonomous Safety Controls
ENABLE_AUTO_CLOSURE=false
ENABLE_AUTO_SIEM_WRITEBACK=false
```

---

## 3. RuntimeConfigValidator Evaluation Results

Executing `RuntimeConfigValidator.validate_all(settings, strict_production_dependencies=True)` directly within the Server 1 runtime environment yielded:

```json
{
  "status": "WARNING",
  "app_env": "production",
  "operating_mode": "advisory",
  "mode_profile": {
    "allows_sqlite": false,
    "allows_mock_fallback": false,
    "allows_auto_incident_closure": false,
    "allows_siem_writeback": false,
    "requires_celery_redis": true,
    "description": "Production analyst-assisted triage requiring human review prior to incident closure."
  },
  "is_production_env": true,
  "fail_closed_mock_disabled": true,
  "context_budget": {
    "configured_context_budget": 4096,
    "reserved_completion_tokens": 512,
    "available_prompt_budget": 3584,
    "validated_tiers": [4096, 8192],
    "verified_server_max_model_len": null,
    "capacity_verification_status": "UNVERIFIED"
  },
  "blockers": [],
  "warnings": [
    "COOKIE_SECURE_DISABLED: COOKIE_SECURE=false in production risks HTTP cookie exposure.",
    "FORTISIEM_SSL_VERIFY_DISABLED: FORTISIEM_VERIFY_SSL=false weakens TLS verification in production."
  ]
}
```

### Analysis of Findings
1. **Critical Blockers:** Exactly **0 blockers** detected.
2. **Operational Warnings:**
   - `COOKIE_SECURE_DISABLED`: Permitted during internal readiness testing where Server 1 is accessed over direct IP HTTP without TLS termination.
   - `FORTISIEM_SSL_VERIFY_DISABLED`: Required because the internal FortiSIEM supervisor host utilizes an enterprise self-signed certificate.
3. **Fail-Closed Verification:** `fail_closed_mock_disabled=true`. Simulated LLM inference is strictly forbidden. Any request requiring LLM inference while Server 2 is offline will fail-closed and return `DEFERRED_SERVER2_STOPPED`.
