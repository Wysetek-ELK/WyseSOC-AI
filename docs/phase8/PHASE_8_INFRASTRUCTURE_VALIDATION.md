# Phase 8 Infrastructure, Database & Multi-Worker Concurrency Validation

**Stages Covered:** Stage 1 (Environment Discovery) & Stage 2 (Database, Migrations, Workers & Concurrency)

## 1. Dependency Availability Classification

Sanitized environment probes executed from the workspace (recorded in [`stage1_env_audit.json`](./evidence/execution-logs/stage1_env_audit.json)) established the following runtime status without exposing credentials or internal IPs:

| Dependency / Component | Status | Verified Probe Result |
|---|---|---|
| **Python Runtime & Core Packages** | `AVAILABLE` | Python `3.13.13`; `fastapi`, `sqlalchemy`, `alembic`, `asyncpg`, `psycopg2`, `aiosqlite`, `redis`, `celery`, `httpx`, `pytest`, `playwright` import cleanly |
| **Chromium Browser Engine** | `AVAILABLE` | Playwright headless Chromium binary verified via interactive Playwright test execution |
| **Node.js & Next.js Frontend** | `AVAILABLE` | Node `v22.12.0`; `tsc`, `admin-guide` test suite, and Next.js `16.4.5` (Turbopack) build succeed locally |
| **PostgreSQL Server / `psql`** | `UNAVAILABLE` | Port `5432` unreachable (`TimeoutError`); `psql` and `pg_isready` binaries absent from local PATH |
| **Redis / Celery Worker Broker** | `UNAVAILABLE` | Port `6379` unreachable (`TimeoutError`); `redis-server` / `redis-cli` absent (`USE_ASYNC_CELERY=false`) |
| **Server 2 Local LLM (`<REDACTED_HOST>:8000/v1`)** | `UNAVAILABLE` | TCP port `8000` timed out (`TimeoutError`); configured model `Qwen/Qwen2.5-7B-Instruct-AWQ` |
| **FortiSIEM Supervisor (`443`)** | `UNAVAILABLE` | TCP port `443` unreachable (`gaierror` DNS/network isolation in offline sandbox) |
| **Development Fallback Flags (`backend/.env`)** | `MISCONFIGURED` *(for prod)* | `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true`, `FORTISIEM_MOCK_FALLBACK=true`, `FORTISIEM_VERIFY_SSL=false` — acceptable only when `APP_ENV=development`; blocked in production by [`Settings.validate_security`](../../backend/app/config.py) |

## 2. Schema Compatibility & Alembic Migration Chain (`001`–`007`)

- Added Alembic revision [`007_distributed_locks.py`](../../backend/alembic/versions/007_distributed_locks.py) creating the [`DistributedLock`](../../backend/app/models/distributed_lock.py) (`distributed_locks`) table to close single-process lock coordination gaps across multi-worker Gunicorn/Celery deployments.
- Verified clean `upgrade head` (`001` -> `007_distributed_locks`), clean `downgrade 006_ai_verdict_v2`, and clean re-upgrade `006_ai_verdict_v2` -> `007_distributed_locks` inside [`test_phase8_alembic_007_upgrade_downgrade_roundtrip`](../../backend/tests/test_phase8_integration.py).
- Verified zero missing tables or column diffs between Alembic head and SQLAlchemy ORM metadata (`Base.metadata`). No destructive migrations were executed against `backend/ai_verdict.db` or any production database.

## 3. PostgreSQL `asyncpg` Dialect Compatibility Remediations (`P8-DEF-02`, `P8-DEF-03`)

During Stage 2 audit of runtime SQL queries under the PostgreSQL dialect (`postgresql+asyncpg`), two runtime incompatibilities hidden under SQLite were identified and remediated:

1. **Naive vs. Aware `DateTime` Mismatch (`P8-DEF-02`)**: [`SystemServerSample.timestamp`](../../backend/app/models/telemetry.py) and `TokenUsageRecord.timestamp` declare `DateTime` without `timezone=True`. Under `asyncpg`, binding timezone-aware ISO strings or `datetime.now(timezone.utc)` raises `DataError`. Remediated via `_coerce_naive_utc_datetime()` in [`system_monitor_service.py`](../../backend/app/services/system_monitor_service.py) and naive `datetime.utcnow()` alignment in [`chat.py`](../../backend/app/api/chat.py#L213).
2. **`json = json` Equality & Session Rollback (`P8-DEF-03`)**: [`main.py`](../../backend/app/main.py) previously checked `IncidentEvent.attributes == {}`, which PostgreSQL rejects (`operator does not exist: json = json`), and lacked `await session.rollback()` inside startup backfill `except` handlers. Updated to `IncidentEvent.attributes.is_(None) | cast(IncidentEvent.attributes, Text).in_(["{}", "null", ""])` with rollback protection.

Compiled SQL statements under `postgresql.dialect()` and write paths are verified in [`test_phase8_postgresql_dialect_safety_and_monitor_writes`](../../backend/tests/test_phase8_integration.py). Live execution against an external PostgreSQL daemon remains `NOT_TESTED` / `BLOCKED` until a PostgreSQL instance is provisioned.

## 4. Multi-Process Locking & Idempotent Triage (`P8-DEF-01`)

- **Root Cause Found:** [`_get_incident_lock`](../../backend/app/services/ai_verdict_service.py) used an in-memory `asyncio.Lock` dictionary, which fails to serialize concurrent workers across separate OS processes and read stale `Incident` ORM snapshots prior to lock acquisition.
- **Remediation Implemented:** Created [`DistributedLockManager`](../../backend/app/services/distributed_lock.py) performing atomic `ON CONFLICT (lock_key) DO UPDATE ... WHERE expires_at <= now` UPSERT coordination across OS processes (plus optional Redis `SET NX PX` when enabled), reloaded `Incident` with `populate_existing=True` *inside* the lock, and enforced `only_if_pending=True` on batch triage callers.
- **Verification Proof:** [`test_phase8_multiprocess_distributed_lock_and_idempotent_triage`](../../backend/tests/test_phase8_integration.py) spawns real OS worker subprocesses contending on `distributed_locks`, proves strict mutual exclusion and stale-lease recovery, and verifies idempotent triage skips already-evaluated incidents without duplicate notes.

