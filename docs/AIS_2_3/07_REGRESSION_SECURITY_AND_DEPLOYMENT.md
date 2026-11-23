# AIS 2.3 — Regression Testing, Security Verification & Deployment Report

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3 (Real Evidence Delivery & Verdict Accuracy Pilot)  
**Date:** November 23, 2026  
**Status:** PASS & CERTIFIED  

---

## 1. Regression Test Suite Execution

Full regression testing was conducted across both backend and frontend suites to guarantee zero regressions following the pipeline and evidence repairs:

### 1.1 Backend Pytest Regression Suite
- **Command:** `pytest backend/tests/test_ais_unified_population_contract.py backend/tests/test_ais_evaluation_tracking.py backend/tests/test_api_422_remediation.py -q`
- **Results:** **33 passed**, 0 failed, 0 warnings (100% success)
- **Duration:** 25.73 seconds
- **Verified Domains:**
  - `test_ais_unified_population_contract.py`: 6 tests verifying authoritative census calculations, population isolation between active inventory and historical archives, and dual-scope contract guarantees.
  - `test_ais_evaluation_tracking.py`: 20 tests verifying canonical evaluation status logic, double-blind review masking, search filtering, and safe PostgreSQL session rollback isolation.
  - `test_api_422_remediation.py`: 7 tests verifying request payload serialization, query parameter validation, and error response formatting.

### 1.2 Frontend Test Suite
- **Command:** `npm.cmd --prefix frontend test -- --watchAll=false`
- **Results:** **16 suites passed**, 16 total; **85 tests passed**, 85 total (100% success)
- **Duration:** 3.82 seconds
- **Verified Domains:**
  - `admin-guide.test.mjs`: Platform control walkthrough, non-fabrication walkthroughs.
  - `phase3-compact-ui.test.mjs`: Simplified 3-tab layout (Review Incidents, Test AI, Accuracy & Learning), decoupled status badges, error handling.
  - `blind-review-and-analyst-workflow.test.mjs`: Double-blind review masking and post-submission reveal workflows.
  - `evaluate-accuracy-and-empirical-readiness.test.mjs`: Accuracy mathematical evaluation and zero-matrix unmeasured dataset handling.

### 1.3 Total Regression Census
$$\text{Total Verified Regression Tests} = 33 \text{ (backend)} + 85 \text{ (frontend)} = \mathbf{118 \text{ passed tests (100\%)}}$$

---

## 2. Security & Anti-Leakage Verification

1. **Model Payload Allowlist Audit:**
   - Every incident evaluated during the GPU pilot was verified using `HistoricalGroundTruthValidator.sanitize_incident_for_inference`.
   - All 20 payloads showed 100% zero ground-truth leakage.
   - Forbidden keys (`resolution`, `clearedReason`, `comments`, `clearedUser`, `clearedTime`, `analyst_verdict`, `ground_truth`) were completely purged prior to model transmission.
2. **Untrusted Telemetry Isolation:**
   - All raw event telemetry and syslog messages were enclosed within `<UNTRUSTED_INCIDENT_DATA>` structural delimiters.
   - Prompt injection resistance was audited: raw strings containing instruction phrases did not alter system directives.
3. **Database Integrity & Transaction Safety:**
   - Evaluated incidents operate under PostgreSQL MVCC snapshot isolation without unhandled greenlet rollbacks.
   - Historical ground truth is maintained in the dedicated `historical_ground_truth` table, strictly inaccessible to model-facing queries.

---

## 3. Server Deployment & System Health

- **Server 1 Staging Endpoint:** `http://172.26.41.240`
  - Health check endpoint `/api/health` returning `healthy`.
  - Ingested 20 historical benchmark incidents into PostgreSQL 16.
  - Rule evaluation endpoints active for `PH_RULE_CS_SUSPICIOUS_ACTIVITY` and `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`.
- **Server 2 GPU Inference Host:** `http://13.204.214.64:8000/v1`
  - Model `Qwen/Qwen2.5-7B-Instruct-AWQ` online, healthy, and operational.
  - Context window bounded at 4,096 tokens.
  - Mean latency across 20 live executions: 15.17 seconds.
