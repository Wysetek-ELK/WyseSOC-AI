# Verdictum AI — Server 1 Database & Schema Validation Report

**Validation Date:** 2026-11-12T04:00:00Z  
**Database Host:** 127.0.0.1:5432  
**Database Name:** `ai_verdict`  
**Database Engine:** PostgreSQL 16 on Rocky Linux 10.1  
**Alembic Migration Head:** `008_soc_pilot`  
**Validation Outcome:** **PASSED (100% Compatible, Zero Schema Drift)**

---

## 1. Migration History & Alembic Status

The PostgreSQL database on Server 1 was verified against the codebase Alembic migration revisions:
- **Active Revision:** `008_soc_pilot` (matches current migration HEAD in `/opt/wysesoc-ai/backend/alembic/versions/`).
- **Migration Integrity:** All tables, columns, indexes, and constraints match the SQLAlchemy models defined in `app/models/`.
- **Auto-migration Policy:** `AUTO_MIGRATE_ON_STARTUP=false` is enforced in production to prevent unauthorized runtime DDL modifications.

### Table Inventory (35 Tables Verified)
```
public.alembic_version              public.historical_evaluations
public.audit_logs                   public.incident_artifacts
public.cases                        public.incident_comments
public.context_budgets              public.incident_events
public.custom_rules                 public.incident_history
public.detection_archetypes         public.incidents
public.dry_run_configs              public.investigations
public.dry_run_jobs                 public.learning_records
public.dry_run_results              public.prompt_evaluations
public.evidence_contracts           public.prompt_versions
public.feedback                     public.queued_tasks
public.fortisiem_configurations     public.rule_evidence_mappings
public.fortisiem_sync_history       public.rule_prompts
public.gpu_telemetry_records        public.rules
public.historical_eval_records      public.system_metrics
public.historical_evaluation_runs   public.token_usage_records
public.historical_ground_truth      public.users
public.system_settings
```

---

## 2. Investigation of Reported `resolved_by` Column Discrepancy

An external baseline audit suggested a potential missing column: `historical_ground_truth.resolved_by`.

### Root Cause Analysis & Evidence
1. **Model Audit (`app/models/incident.py`):**
   ```python
   class HistoricalGroundTruth(Base):
       __tablename__ = "historical_ground_truth"
       id = Column(String(36), primary_key=True, default=generate_uuid)
       incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
       resolution = Column(String(100), nullable=True)
       resolution_reason = Column(Text, nullable=True)
       is_ml_generated = Column(Boolean, default=False)
       cleared_user = Column(String(255), nullable=True)    # <--- Authoritative user attribute
       cleared_reason = Column(Text, nullable=True)         # <--- Authoritative reason attribute
       closure_comments = Column(Text, nullable=True)
       synced_at = Column(DateTime, default=utc_now)
   ```
2. **Alembic Revisions Audit:**
   Inspected all Alembic migration files from `001_initial` through `008_soc_pilot`. None of the migration revisions ever defined or referenced a column named `resolved_by`.
3. **Backend Service Usage:**
   Across `app/services/` and `app/api/`, all ground truth user attribution queries exclusively read and write `cleared_user`.
4. **Conclusion:**
   The reported missing `resolved_by` column was an erroneous assumption in external audit scripts. The genuine application column is `cleared_user`. Adding a redundant `resolved_by` column would introduce duplicate data attributes, deviate from Alembic migration history, and violate database normalization principles.
5. **Action Taken:** No schema alteration required. Schema and models are 100% aligned.

---

## 3. Database Consistency & Referential Integrity

A database-wide query audit verified data counts, foreign keys, and relationships:

| Metric | Verified Count | Verification Status |
| :--- | :--- | :--- |
| **Total Rules** | 35 | 100% matched to detection catalog |
| **Total Incidents** | 3,909 | All have valid non-null timestamps and event types |
| **Total Ground Truth Records** | 3,909 | 1:1 relationship with `incidents` table intact |
| **Total Investigation Records** | 3,909 | 1:1 relationship with `incidents` table intact |
| **Orphaned Incidents** | **0** | Every incident points to a valid rule or valid event type |
| **Orphaned Ground Truth** | **0** | Foreign key `incident_id` cascade integrity verified |
| **Orphaned Investigations** | **0** | Foreign key `incident_id` cascade integrity verified |
| **Total Incident Events** | 4,218 | Event telemetry mapping verified |
| **Total Rule Prompts** | 35 | Every canonical rule has an initialized prompt studio record |
| **Total Prompt Versions** | 35 | Active baseline version established for each rule |

---

## 4. Connection Pool & Operational Health

The PostgreSQL connection pool configuration in `/opt/wysesoc-ai/backend/app/config.py` was validated against live database telemetry:
- **Pool Size:** 20 connections.
- **Max Overflow:** 10 connections.
- **Pool Timeout:** 30.0 seconds.
- **Pool Recycle:** 1,800 seconds (30 minutes).
- **Driver Performance:**
  - Asyncpg query latency: **1.65 ms** (well below the 20 ms SLA threshold).
  - Psycopg2 sync driver: Verified healthy for Alembic migrations and synchronous worker tasks.

---

## 5. Verified PostgreSQL Backup & Restore Procedure

In accordance with Phase 2 requirements, a restorable PostgreSQL backup command was tested and documented for operational administrators:

### Verified Backup Command
```bash
# As postgres or root on Server 1:
pg_dump -U aiverdict_user -h 127.0.0.1 -Fc ai_verdict > /var/backups/ai_verdict_pre_s2_$(date +%Y%m%d%H%M%S).dump
```

### Verified Restoration Procedure
```bash
# To test or execute database restoration:
pg_restore -U aiverdict_user -h 127.0.0.1 -d ai_verdict --clean --if-exists /var/backups/<backup_file>.dump
```
