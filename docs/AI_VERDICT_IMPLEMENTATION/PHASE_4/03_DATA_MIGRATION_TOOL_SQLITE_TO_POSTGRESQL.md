# Report 03: Safe SQLite to PostgreSQL Data Migration Tool (P4-REQ-03)

## 1. Overview & Purpose

To enable existing deployments to transition safely from local SQLite storage to production PostgreSQL without downtime, data loss, or reference corruption, Phase 4 introduces the standalone, operator-controlled migration utility:
`backend/app/scripts/migrate_sqlite_to_postgres.py`

---

## 2. Migration Safety Principles

1. **Mandatory Pre-Flight Snapshot Backup:** Before a single row is read, the source SQLite database is physically copied into the target backup directory, and a cryptographic SHA-256 hash is computed and recorded.
2. **Topological Foreign Key Dependency Ordering:** Tables are migrated in a strict dependency sequence to ensure child foreign keys always reference pre-existing parent rows.
3. **Chunked Streaming & Batch Inserts:** Data is streamed in configurable batch sizes (`--batch-size 500`) to prevent memory exhaustion when transferring tens of thousands of records.
4. **Data Type Normalization:**
   - JSON string fields in SQLite are parsed and loaded into PostgreSQL native `JSON` / `JSONB` columns.
   - Integer boolean representations (`0` / `1`) in SQLite are cast to native boolean (`True` / `False`).
5. **Dry-Run Inspection Mode:** Operators can run `--dry-run` to inspect source row counts, test network connectivity, and verify destination table schemas without modifying PostgreSQL.
6. **Post-Migration Record Reconciliation:** Compares row counts table-by-table between SQLite and PostgreSQL, outputting a structured JSON verification report.

---

## 3. Table Migration Sequence

```
 1. users
 2. rules
 3. rule_prompts
 4. prompt_versions
 5. import_jobs
 6. incidents
 7. incident_events
 8. historical_ground_truth
 9. investigations
10. investigation_questions
11. investigation_evidence
12. learning_records
13. audit_logs
14. dry_run_configs
15. dry_run_jobs
16. dry_run_results
17. rule_maturity_evaluations
18. system_server_samples
19. token_usage_records
20. telemetry_timeline_records
21. queued_tasks
```

---

## 4. CLI Execution & Parameter Reference

```bash
# Preview migration, inspect record counts, and verify schema (No writes)
python -m app.scripts.migrate_sqlite_to_postgres \
  --sqlite-path backend/ai_verdict.db \
  --pg-url "postgresql://aiverdict_user:password@localhost:5432/ai_verdict" \
  --dry-run

# Execute full live migration with pre-migration backup
python -m app.scripts.migrate_sqlite_to_postgres \
  --sqlite-path backend/ai_verdict.db \
  --pg-url "postgresql://aiverdict_user:password@localhost:5432/ai_verdict" \
  --backup-dir backups/ \
  --batch-size 500 \
  --output-report migration_reconciliation.json
```

---

## 5. Verification Output Sample

```json
{
  "timestamp": "2026-11-08T17:04:05.537Z",
  "sqlite_path": "backend/ai_verdict.db",
  "pg_url_redacted": "localhost:5432/ai_verdict",
  "backup": {
    "path": "backups/ai_verdict.db.pre_migration_backup_20261108_113405",
    "sha256": "4cd6c13b847caacbb8d1bab0552c2053b03d9e3ef3a4670ec1d22895e65c352b"
  },
  "reconciliation": {
    "users": { "sqlite_count": 3, "pg_count": 3, "transferred": 3, "matched": true },
    "rules": { "sqlite_count": 14, "pg_count": 14, "transferred": 14, "matched": true },
    "incidents": { "sqlite_count": 128, "pg_count": 128, "transferred": 128, "matched": true },
    "historical_ground_truth": { "sqlite_count": 128, "pg_count": 128, "transferred": 128, "matched": true },
    "audit_logs": { "sqlite_count": 85, "pg_count": 85, "transferred": 85, "matched": true }
  },
  "total_records_migrated": 435,
  "status": "SUCCESS"
}
```

