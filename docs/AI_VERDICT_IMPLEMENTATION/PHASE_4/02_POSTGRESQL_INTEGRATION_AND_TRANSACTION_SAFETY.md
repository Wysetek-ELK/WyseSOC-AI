# Report 02: PostgreSQL Integration & Transaction Safety

## 1. Objectives & Capacity Context

Enterprise SOC deployment requires high-concurrency ingestion and triage for up to 10,000 incidents per day. SQLite is ill-suited for this concurrent write load due to single-writer database locking.

Phase 4 implements native, high-throughput PostgreSQL integration powered by `asyncpg` for asynchronous runtime I/O and `psycopg2` for synchronous administrative/migration operations, while maintaining full backwards compatibility with SQLite for development and automated testing.

---

## 2. Connection Pool Hardening

In `backend/app/database.py`, connection pooling has been parameterized and tuned for Server 1 production execution:

```python
is_postgres = "postgres" in settings.DATABASE_URL
if is_postgres:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,          # Default: 20 active connections
        "max_overflow": settings.DB_MAX_OVERFLOW,    # Default: 10 burst connections
        "pool_timeout": settings.DB_POOL_TIMEOUT,    # Default: 30.0s wait timeout
        "pool_recycle": settings.DB_POOL_RECYCLE,    # Default: 1800s (30m) connection recycle
        "pool_pre_ping": True,                       # Active ping validation before checkout
    })
elif "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
```

### Key Safety Mechanisms:
1. **`pool_pre_ping = True`:** Executes an immediate lightweight probe before returning a pooled connection. Prevents "server closed the connection unexpectedly" errors caused by firewall idle timeouts or server restarts.
2. **`pool_recycle = 1800`:** Recycles database connections after 30 minutes, preventing memory bloat on database backends and stale socket descriptors.
3. **Bounded Burst Capacity:** Limits maximum simultaneous active connections to 30 (`20 + 10`), preventing PostgreSQL connection exhaustion and preserving capacity for administrative connections.

---

## 3. Transaction Safety & Atomic Scope Management

To ensure zero partial writes during multi-table incident evaluations (which involve `incidents`, `investigations`, `audit_logs`, and `token_usage_records`), `app/database.py` introduces the `atomic_transaction` context manager:

```python
@asynccontextmanager
async def atomic_transaction(session: AsyncSession):
    if session.in_transaction():
        async with session.begin_nested():
            yield session
    else:
        async with session.begin():
            yield session
```

### Advantages:
- **Automatic Savepoint Support:** If a transaction is already active, `begin_nested()` creates an atomic savepoint rather than throwing an "Already in transaction" error.
- **Strict Rollback Guarantee:** Any unhandled exception triggers an immediate rollback of the current savepoint or transaction, preventing database corruption or orphaned records.

---

## 4. Active Health Probe (`check_db_health`)

`check_db_health` provides real-time connectivity telemetry for the `/health` and `/metrics` observability endpoints:
- Executes `SELECT 1` on the active connection pool.
- Measures query round-trip latency with microsecond precision (`time.perf_counter()`).
- Collects pool metrics (pool size, checked-in, checked-out, and overflow).
- Returns a standardized health dictionary:
  ```json
  {
    "status": "healthy",
    "database_type": "postgresql",
    "latency_ms": 1.45,
    "connected": true,
    "pool": {
      "pool_size": 20,
      "checked_in": 19,
      "checked_out": 1,
      "overflow": 0
    }
  }
  ```

---

## 5. Verification Evidence

Test module `backend/tests/test_postgresql_and_pooling.py` validates:
- `test_check_db_health_live_query`: PASSED. Confirms `SELECT 1` execution and latency measurement.
- `test_atomic_transaction_commit`: PASSED. Confirms clean commits within atomic scopes.
- `test_atomic_transaction_rollback`: PASSED. Confirms full rollback on simulated exceptions.

