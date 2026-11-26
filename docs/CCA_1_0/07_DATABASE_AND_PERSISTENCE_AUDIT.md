# 07 — Database & Persistence Audit

## 1. Schema & Migration Overview
- **ORM Framework:** SQLAlchemy 2.0 Async (`DeclarativeBase` in `backend/app/database.py`), supporting PostgreSQL (`asyncpg`) in production and SQLite (`aiosqlite`) in dev/testing.
- **Migration Framework:** Alembic (`backend/alembic/versions/001_initial_schema.py` through `016_ground_truth_certification_and_cohort_isolation.py`, 16 migrations).
- **Startup Guard & Self-Healing:** `backend/app/core/db_guard.py` enforces DB safety; `main.py` runs `verify_schema_on_startup` (`is_production=True` blocks runtime DDL), plus legacy self-healing backfills in `lifespan()` (lines 84–227).
- **Limitation:** Read-only local audit did not query live Server 1 PostgreSQL row counts or index bloat.

## 2. ORM Model Inventory (46 Models Across 25 Model Files)
Every registered SQLAlchemy model in `backend/app/models/__init__.py` has active production consumers (`app_refs > 0`):

| Model Class | Table Name | Definition | Columns | App Refs | Test Refs | Status |
|---|---|---|---:|---:|---:|---|
| `ActualLLMPromptCapture` | `actual_llm_prompt_captures` | `backend/app/models/actual_prompt_capture.py:10` | 41 | 5 | 4 | `ACTIVE` |
| `AnalystVerdictReview` | `analyst_verdict_reviews` | `backend/app/models/analyst_feedback.py:10` | 31 | 11 | 12 | `ACTIVE` |
| `AnalystReviewAdjudication` | `analyst_review_adjudications` | `backend/app/models/analyst_feedback.py:63` | 8 | 2 | 1 | `ACTIVE` |
| `BenchmarkCohort` | `benchmark_cohorts` | `backend/app/models/analyst_feedback.py:82` | 9 | 4 | 1 | `ACTIVE` |
| `BenchmarkCohortItem` | `benchmark_cohort_items` | `backend/app/models/analyst_feedback.py:104` | 24 | 4 | 2 | `ACTIVE` |
| `BenchmarkReviewRevision` | `benchmark_review_revisions` | `backend/app/models/analyst_feedback.py:150` | 10 | 1 | 1 | `ACTIVE` |
| `AuditLog` | `audit_logs` | `backend/app/models/audit.py:10` | 11 | 13 | 6 | `ACTIVE` |
| `BulkQualityAuditJobRecord` | `bulk_quality_audit_jobs` | `backend/app/models/bulk_audit.py:10` | 15 | 2 | 0 | `ACTIVE` |
| `DistributedLock` | `distributed_locks` | `backend/app/models/distributed_lock.py:8` | 4 | 1 | 2 | `ACTIVE` |
| `DryRunConfig` | `dry_run_configs` | `backend/app/models/dry_run.py:10` | 10 | 3 | 5 | `ACTIVE` |
| `DryRunJob` | `dry_run_jobs` | `backend/app/models/dry_run.py:36` | 10 | 6 | 4 | `ACTIVE` |
| `DryRunResult` | `dry_run_results` | `backend/app/models/dry_run.py:63` | 18 | 6 | 3 | `ACTIVE` |
| `ImportJob` | `import_jobs` | `backend/app/models/import_job.py:10` | 13 | 3 | 1 | `ACTIVE` |
| `Incident` | `incidents` | `backend/app/models/incident.py:10` | 27 | 57 | 69 | `ACTIVE` |
| `IncidentEvent` | `incident_events` | `backend/app/models/incident.py:62` | 8 | 8 | 21 | `ACTIVE` |
| `HistoricalGroundTruth` | `historical_ground_truth` | `backend/app/models/incident.py:78` | 11 | 18 | 28 | `ACTIVE` |
| `Investigation` | `investigations` | `backend/app/models/investigation.py:10` | 12 | 20 | 28 | `ACTIVE` |
| `InvestigationQuestion` | `investigation_questions` | `backend/app/models/investigation.py:42` | 8 | 1 | 0 | `ACTIVE` |
| `InvestigationEvidence` | `investigation_evidence` | `backend/app/models/investigation.py:61` | 7 | 2 | 0 | `ACTIVE` |
| `LearningRecord` | `learning_records` | `backend/app/models/learning.py:10` | 13 | 11 | 8 | `ACTIVE` |
| `RuleMaturityEvaluation` | `rule_maturity_evaluations` | `backend/app/models/maturity.py:10` | 17 | 2 | 0 | `ACTIVE` |
| `PilotConfiguration` | `pilot_configurations` | `backend/app/models/pilot.py:10` | 26 | 1 | 1 | `ACTIVE` |
| `PilotConfigHistory` | `pilot_config_history` | `backend/app/models/pilot.py:54` | 10 | 1 | 0 | `ACTIVE` |
| `PilotEvaluationRecord` | `pilot_evaluations` | `backend/app/models/pilot.py:72` | 46 | 5 | 1 | `ACTIVE` |
| `PolicyDriftEvent` | `policy_drift_events` | `backend/app/models/policy_drift.py:10` | 10 | 5 | 2 | `ACTIVE` |
| `PolicyQualityAssessmentRecord` | `policy_quality_assessments` | `backend/app/models/policy_quality.py:10` | 19 | 9 | 5 | `ACTIVE` |
| `RulePromotionRequest` | `rule_promotion_requests` | `backend/app/models/production_governance.py:10` | 12 | 2 | 2 | `ACTIVE` |
| `RulePromotionApproval` | `rule_promotion_approvals` | `backend/app/models/production_governance.py:37` | 7 | 1 | 1 | `ACTIVE` |
| `ProductionAutomationPolicy` | `production_automation_policies` | `backend/app/models/production_governance.py:55` | 13 | 5 | 6 | `ACTIVE` |
| `IncidentAutomationAudit` | `incident_automation_audits` | `backend/app/models/production_governance.py:79` | 12 | 2 | 2 | `ACTIVE` |
| `RulePrompt` | `rule_prompts` | `backend/app/models/prompt.py:10` | 8 | 24 | 37 | `ACTIVE` |
| `PromptVersion` | `prompt_versions` | `backend/app/models/prompt.py:38` | 30 | 31 | 41 | `ACTIVE` |
| `Rule` | `rules` | `backend/app/models/rule.py:10` | 16 | 60 | 69 | `ACTIVE` |
| `RuleIntelligenceSnapshot` | `rule_intelligence_snapshots` | `backend/app/models/rule_intelligence.py:10` | 15 | 11 | 14 | `ACTIVE` |
| `RuleLearningProfile` | `rule_learning_profiles` | `backend/app/models/rule_learning.py:10` | 24 | 13 | 9 | `ACTIVE` |
| `RuleLearningStateHistory` | `rule_learning_state_history` | `backend/app/models/rule_learning.py:57` | 8 | 2 | 3 | `ACTIVE` |
| `SystemServerSample` | `system_server_samples` | `backend/app/models/system_metric.py:10` | 20 | 1 | 0 | `ACTIVE` |
| `QueuedTask` | `queued_tasks` | `backend/app/models/task_queue.py:10` | 14 | 3 | 1 | `ACTIVE` |
| `TelemetryTimelineRecord` | `telemetry_timeline_records` | `backend/app/models/telemetry_timeline.py:10` | 13 | 3 | 3 | `ACTIVE` |
| `TokenUsageRecord` | `token_usage_records` | `backend/app/models/token_usage.py:10` | 15 | 7 | 6 | `ACTIVE` |
| `User` | `users` | `backend/app/models/user.py:10` | 10 | 41 | 34 | `ACTIVE` |
| `VerdictTrustAssessmentRecord` | `verdict_trust_assessments` | `backend/app/models/verdict_intelligence.py:10` | 25 | 5 | 10 | `ACTIVE` |
| `EvidenceSufficiencyAssessmentRecord` | `evidence_sufficiency_assessments` | `backend/app/models/verdict_intelligence.py:50` | 17 | 3 | 6 | `ACTIVE` |
| `GroundTruthValidationRecord` | `ground_truth_validations` | `backend/app/models/verdict_intelligence.py:78` | 11 | 1 | 0 | `ACTIVE` |
| `HistoricalEvaluationRunRecord` | `historical_evaluation_runs` | `backend/app/models/verdict_intelligence.py:99` | 20 | 11 | 14 | `ACTIVE` |
| `HistoricalEvaluationResultRecord` | `historical_evaluation_results` | `backend/app/models/verdict_intelligence.py:138` | 17 | 6 | 6 | `ACTIVE` |

## 3. Potentially Unused Columns (Batch 6 Restricted — Requires Explicit Approval)

| Model | Column | File & Line | App Refs | Test Refs | Classification | Action |
|---|---|---|---:|---:|---|---|
| `TokenUsageRecord` | `estimated_cost_usd` | `backend/app/models/token_usage.py:41` | 0 | 0 | `POSSIBLY_UNUSED` | `VERIFY_FIRST` (Batch 6) |
| `GroundTruthValidationRecord` | `is_eligible_for_evaluation` | `backend/app/models/verdict_intelligence.py:94` | 0 | 0 | `POSSIBLY_UNUSED` | `VERIFY_FIRST` (Batch 6) |

## 4. Redundant Persistence Notice
- `DryRunConfig`, `DryRunJob`, and `DryRunResult` persist Phase 3 simulation runs alongside `HistoricalEvaluationRunRecord` and `HistoricalEvaluationResultRecord` (`DryRunService` dual-writes both via `LEGACY_DRY_RUN_ADAPTER`). Treated as **protected historical evidence**; do NOT drop tables without explicit migration/archival plan.
