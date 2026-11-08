# Report 01: Database Schema & Alembic Migration Hardening (Finding AV-012)

## 1. Finding Overview & Prior Vulnerability

During the Phase 0 audit, Finding **AV-012** identified that the backend application executed uncontrolled runtime DDL in `app/main.py` during startup:
```python
# Legacy Insecure Startup (AV-012)
async with async_engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    try:
        await conn.execute(text("ALTER TABLE incidents ADD COLUMN ai_verdict JSON"))
    except Exception:
        pass
    try:
        await conn.execute(text("ALTER TABLE dry_run_results ADD COLUMN prompt_tokens INTEGER DEFAULT 0"))
        # ...
    except Exception:
        pass
```

### Operational Risks of Legacy Architecture:
1. **Uncontrolled Concurrent DDL:** Multiple worker processes running under uvicorn simultaneously attempted table creation and `ALTER TABLE` statements, triggering lock contention, database deadlocks, and silent failure swallows via bare `except Exception: pass`.
2. **Schema Drift:** Changes between development and staging environments went unrecorded in migration histories.
3. **Rollback Impossibility:** Schema changes made on startup could not be cleanly rolled back or reproduced in CI/CD pipelines.

---

## 2. Hardened Architecture & Alembic Revision Chain

All application database entities are now strictly governed by versioned Alembic migration scripts located in `backend/alembic/versions/`:

```
+-------------------------------------------------------+
|  001_initial_schema.py                                |
|  - users, rules, import_jobs, incidents,             |
|    incident_events, historical_ground_truth,          |
|    audit_logs                                         |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  002_phase2_investigation_and_learning.py             |
|  - investigations, investigation_questions,           |
|    investigation_evidence, rule_prompts,              |
|    prompt_versions, learning_records                  |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  003_phase3_dryrun_and_evaluation.py                  |
|  - dry_run_configs, dry_run_jobs, dry_run_results,    |
|    rule_maturity_evaluations                          |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  004_phase4_production_hardening.py (HEAD)           |
|  - system_server_samples, token_usage_records,        |
|    telemetry_timeline_records, queued_tasks           |
|  - Column additions:                                  |
|    * incidents.ai_verdict (JSON)                      |
|    * dry_run_results token metrics                    |
|    * audit_logs HMAC signature and key_id             |
+-------------------------------------------------------+
```

---

## 3. Strict Startup Schema Verification Gate

In `app/services/migration_service.py` and `app/main.py`, runtime DDL has been completely eliminated in production. Application startup now executes a non-mutating schema verification check:

```python
async def verify_schema_on_startup(conn, is_production: bool, auto_migrate: bool = False):
    head_rev = get_head_revision()
    current_rev = await get_current_db_revision(conn)

    if current_rev == head_rev:
        return True, f"Database up to date ({head_rev})"

    if is_production:
        msg = (
            f"Critical Schema Blocker (AV-012): Production database schema is out of date. "
            f"Expected revision '{head_rev}', but database is at '{current_rev}'. "
            f"Runtime DDL is forbidden in production. "
            f"Run 'alembic upgrade head' as an authorized migration step before launching the application."
        )
        logger.critical(msg)
        raise RuntimeError(msg)
```

### Operational Behavior:
- **Production (`APP_ENV=production`):** If the database has not been upgraded to the head revision, the application refuses to start and raises a `RuntimeError`. It never mutates database structure automatically.
- **Development/Testing:** If configured via `AUTO_MIGRATE_ON_STARTUP=true`, the migration service executes `alembic upgrade head` programmatically, stamping the database correctly.

---

## 4. Verification & Test Evidence

Test module `backend/tests/test_database_migrations.py` validates the schema gate:
- `test_get_head_revision_matches_phase4`: PASSED. Confirms head revision is `004_phase4_production_hardening`.
- `test_production_startup_blocks_unmigrated_db`: PASSED. Confirms `RuntimeError` is raised in production when unmigrated.
- `test_development_startup_allows_clean_initialization`: PASSED. Confirms clean development initialization.

