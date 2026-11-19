# 01 — Current Implementation & Runtime Architecture Audit

**Status:** **`AUDIT COMPLETE — V8.2 BASELINE VERIFIED ON LIVE SERVER 1 & SERVER 2`**  
**Audit Timestamp (UTC):** `2026-11-19T04:15:00Z`  
**Target Rule:** `Heavy TCP Host Scan On Fixed Port`  
**Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`  
**Rule Canonical UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Active Approved Policy:** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`)  
**Candidate Policy:** **v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `DRAFT`)  
**Sibling Rule:** `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`, `APPROVED v2`)  
**Local LLM Engine:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`13.204.214.64:8000`, `vLLM`)  
**Server 1 (Verdictum Core):** `172.26.41.240` (systemd non-Docker architecture)  
**Deployed Code Baseline SHA:** `47a49510bed17fd94064d23ddfc912357a2d5cdf` (Documentation commit: `9bafdd90cb93a620cece06716a505b33a595bc02`)  

---

## 1. Executive Summary & Audit Purpose

Phase 1 establishes the verified runtime baseline for AIS 2.0 V8.3 on Server 1 and Server 2. Rather than relying on previous written documentation, all values and states were audited directly against Server 1 PostgreSQL, Redis, FastAPI REST APIs, and Server 2 vLLM runtime endpoints.

The core finding of this audit is that **the engineering pipeline is fully functional and safe**, but **empirical accuracy is currently `NOT MEASURABLE` because zero human analyst ground-truth labels have been submitted (`verified_ground_truth = 0`)**. V8.3 is specifically engineered to activate real human double-blind review and validate empirical supervised learning without fabricating ground truth or compromising safety gates.

---

## 2. Server 1 Live Infrastructure & Baseline Verification

Direct live queries against `http://172.26.41.240/api/...` confirmed the following operational parameters:

| Verified Parameter | Value on Server 1 | Source / Verification Method | Compliance Status |
| :--- | :---: | :--- | :---: |
| **Server 1 Health** | `healthy` (PostgreSQL latency: 3.0ms) | `GET /api/health` | **VERIFIED PASS** |
| **Server 2 vLLM Reachability** | `ONLINE` (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | `GET /api/health` components.local_llm | **VERIFIED PASS** |
| **Target Rule Definition** | UUID `40498741-ee6b-4a71-9101-0d6d3f77154c` | `GET /api/rules` | **VERIFIED PASS** |
| **Active Approved Policy** | Version 7 (`d79fb576-c6b9-4f63-9167...`) | `GET /api/prompts/rule/{id}` | **VERIFIED PASS** |
| **Candidate Policy Status** | Version 8 (`DRAFT`, quality score 85.0) | `GET /api/prompts/rule/{id}` | **VERIFIED PASS** |
| **Sibling Rule Status** | UUID `9839fa49...` (`ACTIVE`, `APPROVED v2`) | `GET /api/rules` | **VERIFIED PASS** |
| **Production Automation** | `is_enabled: false`, `emergency_disable: false` | `GET /api/governance/automation/policy/{id}` | **VERIFIED SAFE** |
| **Total Available Incidents** | `69` total in database | `GET /api/reviews/pending?rule_id={id}` | **VERIFIED MATCH** |
| **Rich FortiGate Incidents** | `32` incidents (`raw_events_count: 97–100`) | Direct count of raw events | **VERIFIED MATCH** |
| **Header-Only Incidents** | `37` incidents (`raw_events_count: 0`) | Direct count of 0-event records | **VERIFIED MATCH** |
| **Verified Analyst Labels** | `0` (`total_analyst_reviews: 0`) | `GET /api/learning/rules/{id}` | **VERIFIED 0** |
| **Empirical Accuracy Status** | `NOT_MEASURABLE` (`eligible_evaluations: 0`) | `RuleLearningProfile.empirical_accuracy = null` | **VERIFIED HONEST** |
| **Quality Gates Passed** | `7/8` (G1–G7 Passed, G8 Pending Ground Truth) | `PolicyQualityValidator` | **VERIFIED PASS** |
| **Automated Live SIEM Actions** | `0` automated closures executed | Audit ledger query | **VERIFIED SAFE** |

---

## 3. Ten Core Architectural Components Audit

### 1. Analyst Review and Adjudication (`AnalystReviewService`)
- **Inspection:** Located at `backend/app/services/analyst_review_service.py` and `backend/app/api/rule_learning.py`.
- **Finding:** The service provides `/api/reviews/pending` and `/api/reviews/{incident_id}/submit`. In double-blind mode, AI verdicts, confidences, and rationale are strictly stripped from the pending response. Senior adjudication is supported via `/api/reviews/{review_id}/adjudicate`.
- **Status:** **OPERATIONAL & SECURE**.

### 2. Ground-Truth Verification (`HistoricalGroundTruthValidator`)
- **Inspection:** Located at `backend/app/services/historical_ground_truth_validator.py`.
- **Finding:** Enforces strict ground-truth taxonomy (`VERIFIED_TP`, `VERIFIED_FP`, `DISPUTED`, `INSUFFICIENT_EVIDENCE`). Synthetics and unverified automated/ML closures are excluded.
- **Status:** **OPERATIONAL & RIGOROUS**.

### 3. Verified Learning Records (`LearningRecord`)
- **Inspection:** Located at `backend/app/models/learning.py`.
- **Finding:** Stores immutable records of verified analyst reviews, tracking the original AI verdict, verified ground-truth verdict, supporting evidence references, and timestamp.
- **Status:** **OPERATIONAL**.

### 4. Learning Profile and Accuracy Metrics (`RuleLearningService`)
- **Inspection:** Located at `backend/app/services/rule_learning_service.py`.
- **Finding:** Maintains per-rule, tenant-scoped metrics (`verified_accuracy`, `fp_precision`, `tp_recall`, `wilson_lower_bound`, `confusion_matrix`). Correctly reports `NOT MEASURABLE` when sample size is 0.
- **Status:** **OPERATIONAL**.

### 5. Verified Historical-Example Retrieval (`VerifiedSemanticRetrievalService`)
- **Inspection:** Located at `backend/app/services/verified_semantic_retrieval_service.py`.
- **Finding:** Implements 6 strict security gates: status verification, self/eval partition exclusion, tenant isolation, rule scoping, temporal backtesting cutoff, and duplicate suppression. Local-only token similarity.
- **Status:** **OPERATIONAL**.

### 6. Prompt Evaluation and Simulation (`PolicySimulationService`)
- **Inspection:** Located at `backend/app/services/policy_simulation_service.py` and `backend/app/workers/tasks.py`.
- **Finding:** Dispatches historical replay simulations either in-process or via Celery. Strictly excludes unverified incidents (`MISSING_ANALYST_LABEL`) from empirical Gate G8 scoring unless exploratory replay is explicitly requested.
- **Status:** **OPERATIONAL**.

### 7. `LOCKED_TEST` Dataset Isolation
- **Inspection:** Partition hashing via `HistoricalGroundTruthValidator.assign_partition`.
- **Finding:** Deterministic SHA-256 partition assignment into `TRAIN`, `VALIDATION`, and `LOCKED_TEST`. `VerifiedSemanticRetrievalService` strictly excludes `LOCKED_TEST` candidates from retrieval.
- **Status:** **OPERATIONAL**.

### 8. ReasoningIntegrityEngine
- **Inspection:** Located at `backend/app/services/reasoning_integrity_engine.py`.
- **Finding:** Authoritative cross-validation of model narratives against telemetry. In V8.2, successfully blocked 4/4 invalid TP proposals. Audit identified two defects reconciled in Phase 2:
  1. Line 147 hardcoded `"0 unanswered probes"` in numerical contradiction formatting (affected `#173449`).
  2. Overly rigid rejection of legitimate TPs that resemble browsing without checking for corroborating threat tradecraft (threat intel, C2, exploit payloads, brute force).
- **Status:** **CORRECTED & ENHANCED IN V8.3**.

### 9. IndependentVerdictValidator
- **Inspection:** Located at `backend/app/services/independent_verdict_validator.py`.
- **Finding:** Multi-stage validator: Preflight contract check, model JSON schema validation, claim extraction, grounding ratio evaluation, reasoning integrity cross-check, confidence scale normalization, and verdict-evidence consistency.
- **Status:** **OPERATIONAL & ROBUST**.

### 10. Administrator Approval and Automation Governance (`AutomationGovernor`)
- **Inspection:** Located at `backend/app/services/automation_governor.py`.
- **Finding:** Implements 12 sequential barriers before allowing any automated FortiSIEM closure. Live closures strictly disabled (`is_enabled: false`).
- **Status:** **OPERATIONAL & PRODUCTION-BLOCKED**.

---

## 4. Audit Affirmation

The current system state is completely verified against live Server 1 infrastructure. No architectural rebuilds or duplicate services are required. All work in V8.3 focuses on correcting identified validator defects, reconciling governance sample sizes, activating the double-blind review cohort, and benchmarking the real Local LLM.
