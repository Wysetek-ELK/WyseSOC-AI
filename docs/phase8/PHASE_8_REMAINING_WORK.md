# Phase 8 Remaining Work (Environment-Blocked & Operational Items)

The items below could not be verified locally because the external hardware appliances and broker services required for live execution are unreachable in this offline Windows environment:

| Feature / Criteria ID | Blocked Area | Reason Unverified Locally | Required Staging / Production Validation Action |
|---|---|---|---|
| `LLM-01-C2`, `QGS-02-C3` | Live Server 2 Local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | Configured host port `8000` unreachable (`TimeoutError`) | Execute Stage 3 & Stage 5 live `OPENAI_COMPATIBLE` inference against Server 2 GPU node (`LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`) to establish true model accuracy, Wilson CIs, and calibration curve fit. |
| `MON-02-C2` | Live vLLM Prometheus `/metrics` Scraping | No reachable GPU `/metrics` endpoint | Verify live KV-cache usage, active queue requests, and tokens/sec scraping against Server 2. |
| `FSI-01-C3` | Live FortiSIEM Supervisor Sync | Configured Supervisor host port `443` unreachable (`gaierror`) | Execute live paginated REST/XML sync against staging/customer FortiSIEM appliance with valid TLS certificates (`FORTISIEM_VERIFY_SSL=true`, `FORTISIEM_MOCK_FALLBACK=false`). |
| `DBM-01-C2` | Live External PostgreSQL Schema & `asyncpg` | PostgreSQL `5432` closed; `psql` absent locally | Run `alembic upgrade head` (`007_distributed_locks`) and full write/concurrency suite against a live staging PostgreSQL instance with `asyncpg`. |
| `WRK-02-C2` | Live Redis & Multi-Worker Celery Execution | Redis `6379` closed (`USE_ASYNC_CELERY=false`) | Start staging Celery workers connected to Redis broker and exercise parallel task dispatch under concurrent incident bursts. |
| `ENV-PROD-FLAGS` | `.env` Production Hardening | Local `backend/.env` sets `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true`, `FORTISIEM_MOCK_FALLBACK=true`, `FORTISIEM_VERIFY_SSL=false` | Ensure production environment variables set `APP_ENV=production`, `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`, `FORTISIEM_MOCK_FALLBACK=false`, and `FORTISIEM_VERIFY_SSL=true`. |

