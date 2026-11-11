# Phase 8.1 Infrastructure Connectivity & Health Probe Report (Stage 2)

- **Status:** **`BLOCKED`** *(External appliances unreachable; fail-honest local health checks verified)*
- **Primary Evidence:** [`stage2_env_probe.json`](./evidence/environment/stage2_env_probe.json)

## 1. Dependency Availability Matrix (`2026-11-11`)

| Dependency | Configured Endpoint / Mode | Socket / Probe Result | Classification | Impact on Phase 8.1 |
|---|---|---|---|---|
| **Local PostgreSQL (`5432`)** | `127.0.0.1:5432` | `TimeoutError` | `UNAVAILABLE` / `BLOCKED` | Live Postgres connection pool & `pg_locks` untested; SQLite `aiosqlite` + dialect SQL compile verified |
| **Local/Remote Redis (`6379`)** | `CELERY_BROKER_URL` (`6379`) | `TimeoutError` | `UNAVAILABLE` / `BLOCKED` | Live multi-host Redis Celery queues untested (`USE_ASYNC_CELERY=false` skips cleanly) |
| **Server 2 Local LLM (`8000`)** | `LOCAL_LLM_BASE_URL` (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | `TimeoutError` | `UNAVAILABLE` / `BLOCKED` | Live GPU inference latency, real token throughput, and `/metrics` VRAM scrape blocked |
| **FortiSIEM Supervisor (`443`)** | `FORTISIEM_HOST:443` | `gaierror` | `UNAVAILABLE` / `BLOCKED` | Live customer incident pull & XML rule pull blocked offline |
| **FastAPI Backend + Next.js Build** | Local `127.0.0.1:8000` & `127.0.0.1:3000` (E2E) | HTTP `200 OK` | `AVAILABLE` | Verified full API + compiled Next.js UI in headless Chromium |
| **`/api/health` Endpoint** | Bounded probe (`1.5s` connect, `2.0s` wait) | `200 OK` in `< 3.5s` | `VERIFIED` | Verified `redis_celery.status == "disabled"` & `local_llm.status == "offline"` without hanging |

## 2. Fail-Honest Behavior Verified

Executed via [`test_stage11_security_rbac_injection_gt_leakage_and_siem_write_safety`](../../backend/tests/test_phase8_1_validation.py) and [`test_system_health_observability.py`](../../backend/tests/test_system_health_observability.py): `/api/health` remains responsive (`< 3.5s`) when Server 2 is offline and `USE_ASYNC_CELERY=false`, reporting degraded/offline dependency telemetry honestly with zero fabricated metrics.

