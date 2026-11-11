# Phase 9 — Integration & Validation Runbook

Phase 9 provides a dedicated staged integration runner (`scripts/run_integration_suite.py`) that enforces honest separation between offline contracts and live infrastructure readiness.

---

## 1. Execution Modes

| Mode Flag | Scope | Unreachable Infrastructure Behavior |
|---|---|---|
| `--mode OFFLINE_CONTRACT_TESTS` | Runs local pytest contract suites covering Server 1 <-> Server 2 OpenAI wire schema, PostgreSQL SQLAlchemy/Alembic + locks, Redis/Celery queue routing, and FortiSIEM parser/pull contracts. | Self-contained (`exit 0` on green). |
| `--mode STAGING_INTEGRATION_TESTS` | Probes live TCP/service endpoints for Server 2 (`/v1`), PostgreSQL (`postgresql://`), Redis (`6379`), and FortiSIEM HTTPS API. | Reports `"status": "BLOCKED"`, `"classification": "NOT_TESTED"`, exits code `2`. Never substitutes mocks. |
| `--mode LIVE_MODEL_VALIDATION` | Executes `smoke_test_server2.py` against `settings.LOCAL_LLM_BASE_URL` for live chat completion, structured SOC JSON, error handling, and `/metrics`. | Reports `"BLOCKED"` / `"NOT_EXECUTED"`, exits code `2`. |

---

## 2. Commands Executed During Phase 9 Verification

```powershell
# 1. Offline wire & integration contracts (PASSED, exit 0)
python scripts/run_integration_suite.py --mode OFFLINE_CONTRACT_TESTS `
  --output docs/phase9/evidence/deployment/offline_contract_tests.json

# 2. Live staging probe check in offline dev workstation (BLOCKED, exit 2)
python scripts/run_integration_suite.py --mode STAGING_INTEGRATION_TESTS `
  --output docs/phase9/evidence/deployment/staging_integration_probes.json
```

### Observed Results Summary

- **`OFFLINE_CONTRACT_TESTS` (`docs/phase9/evidence/deployment/offline_contract_tests.json`):** `overall_status: "PASSED"`
  - `server1_server2_contract`: `PASSED` (6 passed, 5 deselected)
  - `app_postgresql_contract`: `PASSED` (6 passed)
  - `app_redis_celery_contract`: `PASSED` (2 passed)
  - `app_fortisiem_contract`: `PASSED` (18 passed)
- **`STAGING_INTEGRATION_TESTS` (`docs/phase9/evidence/deployment/staging_integration_probes.json`):** `overall_status: "BLOCKED"` (exit `2`)
  - `server1_to_server2`: `BLOCKED` (`NOT_TESTED` — TimeoutError)
  - `app_to_postgresql`: `BLOCKED` (`NOT_TESTED` — SQLite active in local dev)
  - `app_to_redis_celery`: `BLOCKED` (`NOT_TESTED` — TimeoutError)
  - `app_to_fortisiem`: `BLOCKED` (`NOT_TESTED` — `gaierror`)

