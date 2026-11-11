# Phase 8.2 — Stage B Staging Readiness, Probes & Activation Runbook

**Evidence Source:** `docs/phase8.2/evidence/staging/stage_b_staging_readiness_and_probes.json`  
**Staging Status:** `BLOCKED`

## 1. Live Socket Probes (Executed in Phase 8.2)

| Dependency | Configured Target | Port | Reachable | Failure Reason | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| PostgreSQL | `127.0.0.1` | `5432` | `false` | `TimeoutError` | `UNAVAILABLE` |
| Redis | `127.0.0.1` | `6379` | `false` | `TimeoutError` | `UNAVAILABLE` |
| Server 2 Local LLM | `<CONFIGURED_HOST>` (`192.0.2.50`) | `8000` | `false` | `TimeoutError` | `UNAVAILABLE` / Placeholder |
| FortiSIEM Supervisor | `<CONFIGURED_HOST>` (`.env` supervisor host) | `443` | `false` | `gaierror` | `UNAVAILABLE` / Unresolvable |

## 2. Staging Isolation Decision

- RepoDeploy Governor target list contains only `"remote-server (production)"`.
- Per Stage B Staging Isolation Rules, **zero deployments or modifications** were executed against production (`production_deployment_executed = false`) and **no Docker environment** was introduced (`docker_introduced = false`).

## 3. Staging Activation Runbook (When Hardware Becomes Available)

1. Provision an authorized non-production staging target (PostgreSQL, Redis, Server 2 vLLM OpenAI-compatible GPU node, and staging FortiSIEM or recorded replay feed).
2. Set `APP_ENV=staging`, `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`, `FORTISIEM_MOCK_FALLBACK=false`, and `FORTISIEM_VERIFY_SSL=true` (with valid staging CA bundle).
3. Run PostgreSQL Alembic migrations: `alembic upgrade head` (verifying `007_distributed_locks`).
4. Start Celery worker & FastAPI API service (`uvicorn app.main:app` + `celery -A app.worker worker`).
5. Verify `GET /api/health` returns `local_llm.status = "HEALTHY"` (and `/api/system/servers` reflects live Server 2 telemetry) with sensitive URLs hidden unless authenticated.
6. Run live evaluation and historical replay (`POST /api/prompts/rule/{rule_id}/simulate`) against at least 5+ independent human-labeled non-synthetic incidents per active rule, requiring `G8_SIMULATION_REGRESSION == PASSED` before promotion.
