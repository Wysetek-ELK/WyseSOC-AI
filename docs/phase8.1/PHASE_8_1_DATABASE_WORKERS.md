# Phase 8.1 Database Migrations, Locking & Workers Validation (Stage 3)

- **Status:** **`PARTIAL`** *(Isolated SQLite `006 -> 007` upgrade, PostgreSQL dialect parity, multi-process OS locking, and `P8.1-DEF-001` lease-loss abort verified; live external PostgreSQL & Redis/Celery daemons `BLOCKED`)*
- **Primary Evidence:** [`stage1_db_snapshot_audit.json`](./evidence/database/stage1_db_snapshot_audit.json)

## 1. Repository DB State & Migration Verification

- **Seeded Dev Snapshot (`backend/ai_verdict.db`):** Observed at Alembic revision `006_verdict_intelligence_validation` (`31` tables pre-upgrade; `26` incidents, `197` events, `24` ground truth rows, `5` prompt versions, `4` rules).
- **Isolated Clone Upgrade Test (`scripts/run_phase8_1_audit.py`):** Running `alembic upgrade head` on a temporary cloned copy cleanly migrated `006_verdict_intelligence_validation -> 007_distributed_locks`, adding table `distributed_locks` (`32` total tables) without data loss.
- **Full `001 -> 007 -> 006 -> 007` Roundtrip & Postgres SQL Dialect Safety:** Verified in [`test_phase8_integration.py`](../../backend/tests/test_phase8_integration.py) (`test_phase8_alembic_007_upgrade_downgrade_roundtrip` and `test_phase8_postgresql_dialect_safety_and_monitor_writes`).

## 2. `P8.1-DEF-001` Remediation: Pre-Commit Distributed Lease Verification

- **Defect:** Previously, [`VerdictTriageAgent._evaluate_incident_locked`](../../backend/app/services/ai_verdict_service.py) acquired a `120s` distributed lock lease, executed slow LLM inference, and committed `ai_verdict`, `TokenUsageRecord`, trust/sufficiency rows, investigation notes, and `AuditLog` entries without verifying that the lease had not expired or been acquired by another worker.
- **Remediation:**
  1. Added [`DistributedLockManager.verify_or_renew`](../../backend/app/services/distributed_lock.py) and `DistributedLockLostError`. Uses `AsyncEngine(db.get_bind())` (avoiding SQLAlchemy `_GeneratorContextManager` sync-bind traps) to execute an atomic `UPDATE distributed_locks SET expires_at = ... WHERE lock_key = :k AND owner_id = :o AND expires_at > :now` on persistent databases (gracefully preserving `:memory:` SQLite single-process tests unless an explicit row exists).
  2. Added [`VerdictTriageAgent._assert_lock_held`](../../backend/app/services/ai_verdict_service.py) before every write/commit path (`POLICY_NOT_APPROVED`, `PREFLIGHT_GUARD`, `TOKEN_BUDGET_GUARD`, and main inference persistence), rolling back the session and aborting stale commits cleanly.
- **Verification:** [`test_p8_1_def_001_distributed_lock_lease_loss_aborts_stale_commit`](../../backend/tests/test_phase8_1_validation.py) proves Worker A aborts with `DistributedLockLostError`, persists **zero** stale `ai_verdict`/`TokenUsageRecord`/`VerdictTrustAssessmentRecord`/`AuditLog` rows, and preserves Worker B's takeover lock.

## 3. Live Postgres & Redis/Celery Status (`BLOCKED`)

Live multi-worker Celery task broker execution (`WRK-02-C2`) and external PostgreSQL server concurrency (`DBM-01-C2`) remain `NOT_TESTED` until non-production staging Redis and PostgreSQL instances are accessible.

