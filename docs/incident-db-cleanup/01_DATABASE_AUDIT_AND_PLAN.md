# Verdictum AI — Incident Database Audit & Safe Cleanup Plan
**Document ID:** `VAI-DOC-INC-CLEANUP-01`  
**Execution Phase:** Audit, Preflight Verification & Governance Approval  
**Timestamp:** 2026-11-19T10:28:00Z  
**Target Database:** `backend/ai_verdict.db` (SQLite 3 / SQLite + aiosqlite)  
**Database Size:** 6,090,752 bytes (5.81 MB)  
**Total Tables In Schema:** 44 tables  

---

## 1. Executive Summary

This audit assesses the database structure, foreign-key hierarchies, and dependency graph of the Verdictum AI platform to prepare a zero-risk, transaction-controlled purge of all historical and active incident records.

### Mandatory Safety Guarantees
- **Zero Configuration Regression:** All users (7), system rules (51), policy prompts (42), prompt versions (45), production automation policies (50), G1–G8 static quality assessments (37), and LLM configurations remain completely untouched.
- **Audit & Governance Preservation:** All 210 audit logs and 50 lifecycle state transitions are strictly preserved.
- **Strict Verification:** Pre-cleanup database backup created and byte-verified via SHA-256 before any deletion commands are executed.
- **Transaction-Controlled Deletion:** No destructive `DROP TABLE` or database-wide `TRUNCATE` operations are used. All deletions execute inside a single atomic transaction in exact reverse foreign-key dependency order.

---

## 2. Comprehensive Table Inventory & Classification

Across all 44 tables in the schema, data is classified into six distinct tiers:

### Tier A: Core Incident Tables (Direct Purge Target)
| Table Name | Current Rows | Foreign Key Dependencies | Description | Action |
| :--- | :--- | :--- | :--- | :--- |
| `incidents` | **155** | `rules.id`, `import_jobs.id` | Primary incident ledger (telemetry, AI verdicts, status) | **DELETE** (Parent) |
| `incident_events` | **197** | `incidents.id` (`CASCADE`) | Raw normalized SIEM event payloads | **DELETE** (Child) |
| `investigations` | **155** | `incidents.id` (`CASCADE`), `users.id` | Analyst investigation queue records | **DELETE** (Child) |

### Tier B: Incident-Dependent Processing & Review Records (Direct Purge Target)
| Table Name | Current Rows | Foreign Key Dependencies | Description | Action |
| :--- | :--- | :--- | :--- | :--- |
| `analyst_verdict_reviews` | **1** | `incidents.id` (`CASCADE`), `investigations.id` | Double-blind and manual analyst reviews | **DELETE** |
| `historical_ground_truth` | **25** | `incidents.id` (`CASCADE`) | SIEM historical manual closure resolutions | **DELETE** |
| `learning_records` | **20** | `incidents.id` (`CASCADE`), `rules.id` | Dynamic few-shot RAG verified cases | **DELETE** |
| `telemetry_timeline_records` | **6** | `incident_id` (Loose) | Chronological telemetry pipeline milestones | **DELETE** |
| `token_usage_records` | **6** | `incident_id` (Loose) | Per-incident inference token consumption | **DELETE** |
| `import_jobs` | **5** | None | File upload and batch ingest tracker | **DELETE** |
| `investigation_questions` | **0** | `investigations.id` (`CASCADE`) | Contextual analyst inquiry threads | **CLEAN** (0 rows) |
| `investigation_evidence` | **0** | `investigations.id` (`CASCADE`) | Analyst tagged evidence items | **CLEAN** (0 rows) |
| `analyst_review_adjudications` | **0** | `analyst_verdict_reviews.id` | L2 dispute adjudication records | **CLEAN** (0 rows) |
| `actual_llm_prompt_captures` | **0** | `incident_id` (Loose) | Exact serialized prompt captures | **CLEAN** (0 rows) |
| `evidence_sufficiency_assessments`| **0** | `incident_id` (Loose) | Telemetry contract preflight logs | **CLEAN** (0 rows) |
| `ground_truth_validations` | **0** | `incident_id` (Loose) | Empirical ground truth integrity checks | **CLEAN** (0 rows) |
| `incident_automation_audits` | **0** | `incident_id` (Loose) | Automated rule trigger logs | **CLEAN** (0 rows) |
| `verdict_trust_assessments` | **0** | `incident_id` (Loose) | Empirical reliability calculations | **CLEAN** (0 rows) |
| `pilot_evaluations` | **0** | `incident_id` (Loose) | Pilot program incident evaluations | **CLEAN** (0 rows) |

### Tier C: Incident Evaluation & Simulation Results (Direct Purge Target)
| Table Name | Current Rows | Foreign Key Dependencies | Description | Action |
| :--- | :--- | :--- | :--- | :--- |
| `historical_evaluation_results` | **62** | `historical_evaluation_runs.id` (`CASCADE`) | Per-incident test replay evaluation outcomes | **DELETE** |
| `historical_evaluation_runs` | **10** | `rules.id` (Loose) | Evaluation run headers for historical incident datasets | **DELETE** |
| `dry_run_results` | **0** | `dry_run_jobs.id`, `incidents.id` | Dry run incident simulation results | **CLEAN** (0 rows) |

### Tier D: Aggregated Metrics & Profiles (Reset Counters, Preserve Profiles)
| Table Name | Current Rows | Foreign Key Dependencies | Description | Action |
| :--- | :--- | :--- | :--- | :--- |
| `rule_learning_profiles` | **51** | `rules.id` (`CASCADE`) | Per-rule operational accuracy & volume metrics | **RESET COUNTERS TO 0** (Preserve all 51 rule profiles) |

*Metrics to reset on all 51 profiles:*  
`total_incidents_processed = 0`, `total_analyst_reviews = 0`, `verified_tp_count = 0`, `verified_fp_count = 0`, `ai_correct_count = 0`, `ai_incorrect_count = 0`, `abstention_count = 0`, `validation_failure_count = 0`, `empirical_accuracy = NULL`, `fp_precision = NULL`, `tp_recall = NULL`, `wilson_lower_bound = NULL`, `error_distribution = '{}'`, `last_evaluated_at = NULL`.

### Tier E: Preserved Configuration, Policies & Governance (STRICTLY PRESERVED)
| Table Name | Current Rows | Purpose | Retention Reason |
| :--- | :--- | :--- | :--- |
| `users` | **7** | User accounts, credentials & roles | Preserves RBAC, administrator and analyst accounts |
| `rules` | **51** | Detection rule definitions & FortiSIEM sync | Core platform detection catalog |
| `rule_prompts` | **42** | Rule policy containers | Connects rules to prompt versions |
| `prompt_versions` | **45** | Synthesized and approved policy versions | Preserves all approved detection policies (AIS 2.0) |
| `production_automation_policies` | **50** | Deployment and gating thresholds | Preserves production automation governance |
| `policy_quality_assessments` | **37** | Static quality gate (G1–G7) scorecards | Preserves syntactic quality validation scores |
| `rule_intelligence_snapshots` | **1** | Rule metadata cache | Authoritative rule structure cache |
| `pilot_configurations` | **1** | Supervised pilot gating rules | Production pilot governance |
| `pilot_config_history` | **1** | Pilot configuration change log | Change management compliance |
| `rule_learning_state_history` | **50** | Audit log of rule lifecycle transitions | ISO/SOC-2 lifecycle state transition history |
| `audit_logs` | **210** | User actions, logins, rule updates, exports | Security audit trail (preserved without FK violation) |
| `dry_run_configs` | **0** | Simulation test harnesses | Reusable simulation configurations |
| `dry_run_jobs` | **0** | Simulation job definitions | Reusable simulation templates |
| `policy_drift_events` | **0** | Drift tracking alerts | Drift detection monitoring framework |
| `rule_maturity_evaluations` | **0** | Maturity milestones | Rule maturity tracking framework |
| `rule_promotion_requests` | **0** | Formal promotion requests | Governance request tracking |
| `rule_promotion_approvals` | **0** | Human approval records | Governance approval tracking |

### Tier F: Preserved Infrastructure & System Telemetry (STRICTLY PRESERVED)
| Table Name | Current Rows | Purpose | Retention Reason |
| :--- | :--- | :--- | :--- |
| `system_server_samples` | **102** | Hardware metrics (CPU, RAM, GPU on Server 1 & 2) | Telemetry Hub system observability |
| `alembic_version` | **1** | Database schema migration head | Database version integrity |
| `bulk_quality_audit_jobs` | **0** | Bulk rule auditing jobs | Studio maintenance framework |
| `distributed_locks` | **0** | Concurrency control locks | Active session locks |
| `queued_tasks` | **0** | Background Celery task queue | Job execution queue |

---

## 3. Pre-Cleanup Backup Verification Evidence

An online database snapshot was created and validated prior to executing any deletion plan:

- **Source Database:** `backend/ai_verdict.db`
- **Backup Directory:** `docs/incident-db-cleanup/backups/backup_20261119_102800`
- **Backup Archive File:** `ai_verdict.db` (6,090,752 bytes)
- **Manifest File:** `manifest.json`
- **Cryptographic Checksum:**  
  `SHA-256: 8f2a06901606ccb43908ee7f3bcd414015169ccd605a02793817336924ebe400`
- **Restore Capability Test:**  
  Executed physical restore to an isolated test file `test_restore_verify.db`. Checksum verified bit-for-bit identical (`8f2a06901606ccb43908ee7f3bcd414015169ccd605a02793817336924ebe400`). Queried `SELECT COUNT(*) FROM incidents` against the restored archive, successfully returning **155 records**. Verified 100% restorable.

---

## 4. Deletion Impact & Dependency Analysis

### A. Impact on Agent Intelligence Studio (AIS 2.0)
- **G1–G7 Structural Quality Gates:** Completely unaffected. G1–G7 evaluate rule logic and prompt syntax (`policy_quality_assessments`), which remain 100% preserved.
- **G8 Empirical Validation:** Will accurately display `INSUFFICIENT_DATA` (N=0) because no historical incident ground-truth remains. This is the correct, intended behavior for an empty database ready for fresh data.
- **Production Readiness Checklist:** Displays `Pending Empirical Validation (0/30 verified reviews required)`. All policy approvals and SIEM rule statuses remain intact.

### B. Impact on RAG Learning & Few-Shot Prompts
- The 20 `learning_records` derived from previous incidents will be purged.
- When new incidents are ingested and verified by analysts, fresh, authoritative few-shot examples will immediately populate the RAG store.

### C. Impact on Audit Logs
- All 210 `audit_logs` records are preserved. Historical entries recording past incident views or imports remain as immutable historical activity logs without referencing deleted rows via foreign keys (since `resource_id` is an unconstrained string identifier).

---

## 5. Execution Protocol (Reverse Foreign-Key Order)

To guarantee foreign-key integrity and prevent constraint violations, deletions must execute inside a single atomic transaction in the following deterministic sequence:

```sql
BEGIN TRANSACTION;

-- Step 1: Ingestion / Polling Guard (Disable automatic ingestion)
-- Handled at application layer via SentinelIngestWorker.stop()

-- Step 2: Delete Child Incident Evaluation & Feedback Records
DELETE FROM analyst_review_adjudications;
DELETE FROM analyst_verdict_reviews;
DELETE FROM historical_evaluation_results;
DELETE FROM historical_evaluation_runs;
DELETE FROM historical_ground_truth;
DELETE FROM learning_records;
DELETE FROM dry_run_results;
DELETE FROM actual_llm_prompt_captures;
DELETE FROM evidence_sufficiency_assessments;
DELETE FROM ground_truth_validations;
DELETE FROM incident_automation_audits;
DELETE FROM verdict_trust_assessments;
DELETE FROM pilot_evaluations;

-- Step 3: Delete Investigation Child Data
DELETE FROM investigation_questions;
DELETE FROM investigation_evidence;

-- Step 4: Delete Investigation Queue Records
DELETE FROM investigations;

-- Step 5: Delete Incident Events & Telemetry
DELETE FROM incident_events;
DELETE FROM telemetry_timeline_records;
DELETE FROM token_usage_records;

-- Step 6: Delete Core Incidents
DELETE FROM incidents;

-- Step 7: Delete Historical Import Batch Trackers
DELETE FROM import_jobs;

-- Step 8: Reset Aggregate Incident Metrics on Rule Profiles (Preserving Rule Definitions)
UPDATE rule_learning_profiles SET
    total_incidents_processed = 0,
    total_analyst_reviews = 0,
    verified_tp_count = 0,
    verified_fp_count = 0,
    ai_correct_count = 0,
    ai_incorrect_count = 0,
    abstention_count = 0,
    validation_failure_count = 0,
    empirical_accuracy = NULL,
    fp_precision = NULL,
    tp_recall = NULL,
    wilson_lower_bound = NULL,
    error_distribution = '{}',
    last_evaluated_at = NULL,
    updated_at = CURRENT_TIMESTAMP;

-- Step 9: Commit Transaction Atomically
COMMIT;

-- Step 10: VACUUM database to reclaim storage and reindex
VACUUM;
```

---

## 6. Target Numbers Summary

| Metric | Before Purge | Expected After Purge |
| :--- | :--- | :--- |
| **Total Incidents** | **155** | **0** |
| **Incident Events (Telemetry)** | **197** | **0** |
| **Investigations** | **155** | **0** |
| **Analyst Verdict Reviews** | **1** | **0** |
| **Historical Ground Truth** | **25** | **0** |
| **Learning Records (Few-Shot RAG)** | **20** | **0** |
| **Historical Evaluation Results** | **62** | **0** |
| **Historical Evaluation Runs** | **10** | **0** |
| **Telemetry Timeline Records** | **6** | **0** |
| **Token Usage Records** | **6** | **0** |
| **Import Jobs** | **5** | **0** |
| **Preserved Users** | **7** | **7** (100% Intact) |
| **Preserved Rules** | **51** | **51** (100% Intact) |
| **Preserved Prompts & Policies** | **45** | **45** (100% Intact) |
| **Preserved Audit Logs** | **210** | **210** (100% Intact) |
| **Orphaned References** | **0** | **0** |
