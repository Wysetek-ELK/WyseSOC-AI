# Verdictum AI — Incident Database Cleanup Execution Results
**Document ID:** `VAI-DOC-INC-CLEANUP-02`  
**Execution Phase:** Phase 4 — Transactional Cleanup Execution  
**Timestamp:** 2026-11-19T10:31:25Z  
**Target Database:** `backend/ai_verdict.db`  
**Status:** `SUCCESS` (Atomic Transaction Committed)  
**Database Optimization:** `VACUUM` and `ANALYZE` completed successfully  

---

## 1. Execution Log

The cleanup script executed with `PRAGMA foreign_keys = ON` inside a single atomic transaction. All dependent records were removed in exact reverse foreign-key order prior to deleting core incident records:

| Step | Target Table | Records Before | Records Deleted | Records After | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.1** | `analyst_review_adjudications` | 0 | 0 | 0 | `CLEAN` |
| **1.2** | `analyst_verdict_reviews` | 1 | 1 | 0 | `CLEAN` |
| **1.3** | `historical_evaluation_results` | 62 | 62 | 0 | `CLEAN` |
| **1.4** | `historical_evaluation_runs` | 10 | 10 | 0 | `CLEAN` |
| **1.5** | `historical_ground_truth` | 25 | 25 | 0 | `CLEAN` |
| **1.6** | `learning_records` | 20 | 20 | 0 | `CLEAN` |
| **1.7** | `dry_run_results` | 0 | 0 | 0 | `CLEAN` |
| **1.8** | `actual_llm_prompt_captures` | 0 | 0 | 0 | `CLEAN` |
| **1.9** | `evidence_sufficiency_assessments` | 0 | 0 | 0 | `CLEAN` |
| **1.10** | `ground_truth_validations` | 0 | 0 | 0 | `CLEAN` |
| **1.11** | `incident_automation_audits` | 0 | 0 | 0 | `CLEAN` |
| **1.12** | `verdict_trust_assessments` | 0 | 0 | 0 | `CLEAN` |
| **1.13** | `pilot_evaluations` | 0 | 0 | 0 | `CLEAN` |
| **2.1** | `investigation_questions` | 0 | 0 | 0 | `CLEAN` |
| **2.2** | `investigation_evidence` | 0 | 0 | 0 | `CLEAN` |
| **3.1** | `investigations` | 155 | 155 | 0 | `CLEAN` |
| **4.1** | `incident_events` | 197 | 197 | 0 | `CLEAN` |
| **4.2** | `telemetry_timeline_records` | 6 | 6 | 0 | `CLEAN` |
| **4.3** | `token_usage_records` | 6 | 6 | 0 | `CLEAN` |
| **5.1** | `incidents` | 155 | 155 | 0 | `CLEAN` |
| **6.1** | `import_jobs` | 5 | 5 | 0 | `CLEAN` |
| **7.1** | `rule_learning_profiles` | 51 profiles | 51 profiles reset | 51 profiles | `RESET TO 0` |

---

## 2. Quantitative Summary

- **Total Incident Rows Purged:** `642 rows`
- **Total Remaining Incidents:** `0 rows`
- **Total Remaining Incident Telemetry Events:** `0 rows`
- **Total Remaining Investigations:** `0 rows`
- **Total Remaining Analyst Reviews:** `0 rows`
- **Total Remaining Historical Ground Truth:** `0 rows`
- **Transaction Rollbacks:** `0` (Committed cleanly on first attempt)
- **Database Post-Shrink:** Optimized via SQLite `VACUUM` and `ANALYZE`
