# AIS 2.2a Root Cause Investigation & Defect Remediations

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2a (Benchmark Evidence Integrity, Dataset Repair & GPU Smoke Validation)  
**Date:** November 23, 2026  
**Status:** REMEDIATED & VERIFIED  

---

## 1. Executive Summary

Phase AIS 2.2 established foundational infrastructure for empirical evaluation but suffered from five critical evidence and dataset integrity defects identified during acceptance auditing. Phase AIS 2.2a delivers minimal, targeted, code-grounded corrections addressing each verified defect without modifying unchanged application modules or violating core invariants:

1. **Defect A (Ground-Truth Mismatch):** Reconciled the discrepancy between operational triage adjudication (4 TP, 2 FP, 14 Unverified) and strict forensic adjudication (0 TP, 2 FP, 18 Unverified). Documented the authoritative dataset status as `INSUFFICIENT_VALIDATED_DATASET` for multi-class baseline accuracy.
2. **Defect B (Broken Event & Rule Extraction):** Corrected the schema mapping in `EmpiricalBenchmarkHarness`, `IncidentAdapter`, and `EventAdapter` to properly parse FortiSIEM fixture JSON fields (`eventName`, `eventType`, `rawEvents`, `target`). All 20 historical records now extract valid rule identities and real event counts (ranging from 1 to 34 events).
3. **Defect C (Duplicate Isolation Failure):** Repaired the synthetic cluster grouping key `Unknown Rule_0`. Re-clustered all 20 historical incidents by canonical `rule_id | target | events_count`, identifying exactly 15 unique clusters (13 standalone + 2 multi-incident clusters). Quarantined 5 duplicates and partitioned the 15 unique eligible incidents into 3 isolated cohorts (5 Dev, 5 Val, 5 Held-out) strictly enforcing `eligible_cohort_ids ∩ quarantined_ids = ∅`.
4. **Defect D (Unsupported Benchmark Comparisons):** Separated deterministic offline simulation metrics from empirical local LLM inference. Prohibited attributing unverified mock scores to live model performance.
5. **Defect E (Regression Evidence Mismatch):** Reconciled markdown claims of 121 tests against actual test suite execution artifacts showing 118 tests (33 backend + 85 frontend).
6. **Database & API Integrity Fix:** Identified and resolved a critical PostgreSQL greenlet error (`greenlet_spawn has not been called; can't call await_() here`) caused by session rollback expiring `current_user` in asyncpg. Introduced dedicated read-only `AsyncSessionLocal()` evaluation sessions and safe upfront user primitive extraction.

---

## 2. Detailed Defect Investigations & Technical Remediations

### 2.1 Defect A: Ground-Truth Mismatch

- **Symptom:** `03_HISTORICAL_DATASET_READINESS.md` reported 4 verified TPs, 2 verified FPs, and 14 unverified incidents, whereas `BENCHMARK_MANIFEST.json` recorded 0 verified TPs, 1 verified FP, and 19 unverified incidents.
- **Root Cause:**
  - The historical JSON fixtures contain two distinct classes of analyst metadata:
    - 12 incidents contain `comments: "Resolution set by Machine Learning"`. `HistoricalGroundTruthValidator.detect_automated_or_ml_text()` correctly marks all 12 as `UNVERIFIED` because ML auto-closures are circular and cannot serve as human ground truth.
    - 2 FP incidents (`132439932` and `132441815`) note `kill process is true` and `proccess is kiled`. `HistoricalGroundTruthValidator.is_containment_only_fp_note()` flags containment actions as unverified false alarm claims (containment indicates attack mitigation, contradicting FP disposition).
    - 4 TP incidents (`132596403`, `132599145`, `132599146`, `132599330`) note `Mail has been sent already` or `Case has been raised for the similar incidents.`. Under operational SOC triage, ticketing escalation is treated as operational confirmation (Score 1.0), yielding 4 TPs. Under strict forensic criteria requiring cryptographic hash or attack telemetry proof, ticketing actions remain unproven (`UNVERIFIED`, Score 0.6).
  - The previous manifest script failed to parse `resolution` correctly due to schema key mismatches, collapsing nearly all records to `UNVERIFIED`.
- **Remediation:**
  - Re-adjudicated all 20 records under both strict forensic and operational triage standards in `BENCHMARK_MANIFEST_CORRECTED.json`.
  - Authoritative ground-truth census:
    - **Strict Forensic Standard:** 0 Verified TP, 2 Verified FP (`132474210`, `132499009`), 18 Unverified.
    - **Operational Triage Standard:** 4 Verified TP (`132596403`, `132599145`, `132599146`, `132599330`), 2 Verified FP, 14 Unverified.
  - Formally reported dataset readiness as `INSUFFICIENT_VALIDATED_DATASET`. No synthetic TP samples were fabricated to artificially satisfy accuracy gates.

---

### 2.2 Defect B: Broken Event & Detection Rule Extraction

- **Symptom:** All 20 incident records in `BENCHMARK_MANIFEST.json` recorded `rule_name: "Unknown Rule"` and `events_count: 0`.
- **Root Cause:**
  - `generate_benchmark_artifacts.py` and `IncidentAdapter` looked for top-level keys `ruleName` and `events`.
  - The FortiSIEM JSON schema in `fixtures/Incident json.zip` stores:
    - Rule Display Name: `eventName` (e.g. `"Crowdstrike: Suspicious Activity"`, `"Prisma SASE: Suspicious File Threat Detection"`)
    - Rule Event Type ID: `eventType` (e.g. `"PH_RULE_CS_SUSPICIOUS_ACTIVITY"`, `"Prisma_SASE_Suspicious_File_Threat_Detection_"`)
    - Raw Event Log Array: `rawEvents` (list containing 1 to 34 individual event dictionaries)
    - Target Entity: `target` (e.g. `hostName:DESKTOP-E0G2R49,`, `appName:web-browsing,`)
- **Remediation:**
  - Created `EventAdapter` in `backend/app/services/empirical_benchmark_harness.py` exposing `id`, `event_id`, `event_type`, `event_receive_time`, `raw_log`, and `attributes`.
  - Updated `IncidentAdapter` to dynamically wrap `rawEvents` or `events` into structured event adapters.
  - Updated `load_dataset_from_zip` and `load_dataset_from_db` to read `eventName`, `eventType`, and `rawEvents`.
  - Added `events_count: int = 0` to `BenchmarkIncidentRecord`.
  - All 20 records now correctly reflect their true rule name, rule type, and extracted event counts (25, 8, 16, 34, 19, 30, 13, 2, 24, 2, 1, 1, 1, 1, 3, 1, 1, 2, 11, 2).

---

### 2.3 Defect C: Duplicate Isolation Failure

- **Symptom:** `BENCHMARK_MANIFEST.json` defined a single duplicate cluster `Unknown Rule_0` containing 19 quarantined duplicates, but concurrently placed all 19 incidents into evaluation cohorts.
- **Root Cause:**
  - Because `rule_name` was `"Unknown Rule"` and `events_count` was `0`, the clustering key `f"{rule_name}_{events_count}"` collapsed every incident into one cluster.
  - The partitioning code failed to filter out quarantined duplicates before cohort generation, causing `eligible_cohort_ids ∩ quarantined_ids` to equal all 19 incidents.
- **Remediation:**
  - Implemented real clustering key: `f"{rule_id}|{target}|{events_count}"`.
  - Re-clustered all 20 historical records:
    - 13 unique standalone incidents.
    - 1 cluster with 5 incidents: `Prisma_SASE|appName:web-browsing,|1` (Primary: `132499023`; Quarantined duplicates: `132499745`, `132578774`, `132595592`, `132596403`).
    - 1 cluster with 2 incidents: `Prisma_SASE|appName:indonis,|2` (Primary: `132599145`; Quarantined duplicate: `132599330`).
  - Total eligible unique incidents: **15**. Total quarantined duplicates: **5**.
  - Cohort assignment from eligible unique incidents:
    - `development_cohort`: 5 incidents
    - `validation_cohort`: 5 incidents
    - `held_out_blind_cohort`: 5 incidents
  - Enforced strict invariant:
    $$\text{eligible\_cohort\_ids} \cap \text{quarantined\_ids} = \emptyset$$
  - Verified cross-cohort cluster disjointness: Development, Validation, and Held-out cohorts share zero duplicate cluster keys.

---

### 2.4 Defect D: Unsupported Benchmark Comparisons

- **Symptom:** `BENCHMARK_RESULTS.json` in AIS 2.2 recorded candidate policy v8 metrics (100% grounding ratio, trust score 81.2) while simultaneously noting that the GPU execution was offline.
- **Root Cause:** Offline deterministic simulation outputs generated by `PolicySimulationService._simulate_model_output` were saved into benchmark summaries without explicitly distinguishing them from live model inference.
- **Remediation:**
  - Established unambiguous provenance tagging across all benchmark and evaluation artifacts:
    - `OFFLINE_DETERMINISTIC_SIMULATION`: Rule-based deterministic heuristics.
    - `REAL_LOCAL_GPU_INFERENCE`: Live Qwen-2.5-7B inference against Server 2 (`http://13.204.214.64:8000/v1`).
  - Formally documented that candidate policy v8 remains `DRAFT` and cannot be reported as empirically superior based on mock data.

---

### 2.5 Defect E: Regression Evidence Mismatch

- **Symptom:** Markdown documentation claimed 121 passing tests, whereas `TEST_RESULTS.json` recorded 118 passing tests.
- **Root Cause:** A clerical typographical error miscounted the 85 Jest frontend unit tests as 88 tests.
- **Remediation:**
  - Audited actual test run execution:
    - Backend Pytest Suite: **33 tests passed** (including `test_ais_unified_population_contract.py`, `test_ais_evaluation_tracking.py`, `test_api_422_remediation.py`).
    - Frontend Jest Suite: **85 tests passed** across 16 test suites.
    - Authoritative Total: **118 passed tests** (0 failures, 0 skipped).

---

### 2.6 Database & API Integrity Fix (SQLAlchemy Asyncpg Greenlet Spawn)

- **Symptom:** Calling `/api/ais/rules/{rule_uuid}/evaluation-status` on Server 1 returned HTTP 500:
  `{"detail":"Failed to retrieve evaluation tracking data: greenlet_spawn has not been called; can't call await_() here. Was IO attempted in an unexpected place?"}`
- **Root Cause:**
  - In `AisEvaluationService.get_rule_evaluation_tracking_overview()`, the service called `if db.in_transaction(): await db.rollback()` before issuing `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;`.
  - In SQLAlchemy's `AsyncSession`, calling `rollback()` on a session that previously loaded `current_user` during authentication expired all attributes on the `User` object.
  - When line 511 subsequently accessed `current_user.role`, SQLAlchemy attempted synchronous lazy loading in an asyncpg session, which throws `greenlet_spawn has not been called`.
- **Remediation:**
  - In `backend/app/api/ais_evaluation.py`: Updated `get_rule_evaluation_status` to create a dedicated read-only evaluation session using `AsyncSessionLocal()`. This isolates evaluation queries from the request's authentication session.
  - In `backend/app/services/ais_evaluation_service.py`:
    - Extracted all user attributes (`user_role`, `is_admin_user`, `user_cust`, `current_username`, `current_user_id`) upfront before any database calls.
    - Removed `await db.rollback()` prior to setting transaction isolation level.
    - Updated `get_incident_evaluation_history()` with identical safe primitive extractions.

---

## 3. Summary of Code Modifications

| File | Changes Made |
| :--- | :--- |
| `backend/app/api/ais_evaluation.py` | Added `AsyncSessionLocal` import; wrapped evaluation tracking call in dedicated session context. |
| `backend/app/services/ais_evaluation_service.py` | Extracted user primitives upfront; removed unsafe `await db.rollback()`; replaced lazy attribute accesses with cached primitives. |
| `backend/app/services/empirical_benchmark_harness.py` | Added `EventAdapter`; updated `IncidentAdapter` to wrap events; added `events_count` to `BenchmarkIncidentRecord`; fixed `load_dataset_from_zip` parser and duplicate clustering. |
| `scratch/generate_corrected_manifest.py` | Built authoritative generator creating `BENCHMARK_MANIFEST_CORRECTED.json` with strict cohort isolation. |
| `scratch/execute_gpu_smoke.py` | Built live inference harness executing bounded GPU smoke tests against Server 2 via Server 1. |
