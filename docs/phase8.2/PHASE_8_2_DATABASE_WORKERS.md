# Phase 8.2 — Stage D/H Database Migrations & Distributed Workers

**Evidence Sources:**
- `docs/phase8.2/evidence/database/stage_h_db_migration_snapshot.json`
- `docs/phase8.2/evidence/workers/stage_d_workers_and_lock_probe.json`

## 1. Schema & Alembic Migration Verification (`006 -> 007`)

- **Seeded Workspace DB (`backend/ai_verdict.db`):** Kept untouched during audit (`006_verdict_intelligence_validation`, 31 tables).
- **Isolated Cloned DB Migration (`alembic upgrade head`):**
  - Pre-upgrade Alembic head: `006_verdict_intelligence_validation` (`31` tables)
  - Post-upgrade Alembic head: `007_distributed_locks` (`32` tables)
  - Verified `distributed_locks` schema columns: `["lock_key", "owner_id", "acquired_at", "expires_at"]` (`distributed_locks_table_added: true`).

## 2. Live PostgreSQL & Redis/Celery Probe Status (`BLOCKED`)

- Local PostgreSQL (`127.0.0.1:5432`): `TimeoutError` (`psql`/`pg_ctl`/`postgres` binaries absent on Windows). Criteria `DBM-01-C2` remains `NOT_TESTED`.
- Local Redis (`127.0.0.1:6379`): `TimeoutError` (`redis-server`/`memurai` absent; `USE_ASYNC_CELERY="false"`). Criteria `WRK-02-C2` remains `NOT_TESTED`.

## 3. Distributed Lock Contention Verification (Offline Real-Engine)

- Verified via `test_phase8_1_validation.py` and `test_phase8_2_validation.py::test_stage_e_controlled_wire_scenarios`:
  - Concurrent dual-worker evaluation (`asyncio.gather` across separate `AsyncSession` workers targeting `"INC-P82-WIRE-DUAL"` with `only_if_pending=True`) executed **exactly 1 LLM HTTP POST (`dual_post_calls == 1`)**, persisted **exactly 1 `VerdictTrustAssessmentRecord`**, and returned identical `replay_signature` results across both callers.

