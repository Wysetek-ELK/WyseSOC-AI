# 01 — Deployment, Git Revision & Current Implementation Audit

**Rule Name:** `Heavy TCP Host Scan On Fixed Port`  
**Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`  
**Canonical Rule UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Active Production Policy:** **v7 APPROVED** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a` — preserved unchanged)  
**Candidate Evaluation Policy:** **v8 DRAFT** (`20d4f788-85a5-437d-afbe-fe7fd80abca1` — strictly retained as DRAFT)  
**Sibling Rule Isolation:** `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`, **v2 APPROVED**)  
**Audit Timestamp (UTC):** `2026-11-19T04:45:00Z`  

---

## 1. Executive Summary & Git Revision Reconciliation

In earlier V8.2 and V8.3 reports, discrepancies were observed where benchmark evidence referenced commit `47a49510...` while code changes and tests referenced later revisions. This audit reconciles the exact lifecycle of all commits, GitHub synchronizations, server deployments, regression test executions, and LLM inference runs.

### Full Lineage Matrix Across Revisions

| Stage | Git SHA | Date & Time (UTC) | State / Action | Evidence & Verification |
| :--- | :---: | :---: | :--- | :--- |
| **V8.2 Baseline Deployed** | `47a49510...` | `2026-11-19T03:21Z` | Deployed to Server 1 (`/opt/wysesoc-ai`) | UPLA execution `upla-20261119-032142-a3784a`. 25 automated tests passed. |
| **V8.3 Real LLM Benchmark** | `47a49510...` (Server 1 API) | `2026-11-19T04:14Z` | Executed live against Server 2 GPU endpoint | Execution ID `5895b463-4a86-4309-83ed-c1b8d2e9765e`. Tested 6 canonical incidents on Server 2 (`Qwen2.5-7B-AWQ`). |
| **V8.3 Initial Commit** | `cb21e27f...` | `2026-11-19T04:24Z` | Committed and pushed to GitHub | UPLA Gate 1 approved. 15 files changed. Remote SHA verified on `origin/feature/phase3-compact-ui`. |
| **V8.3 Deployment Attempt 1** | `cb21e27f...` | `2026-11-19T04:26Z` | Deployment halted by safe rollback | Pytest on Server 1 failed on `test_13` (`sentbyte=0` in test mock). Safe rollback restored Server 1 to previous SHA `9bafdd92...`. |
| **V8.3 Test Hotfix Commit** | `952eec6c...` | `2026-11-19T04:34Z` | Committed and pushed to GitHub | Fixed probe `sentbyte` generation in `test_13`. Remote SHA verified on GitHub. |
| **V8.3 Verified Deployment** | `952eec6c...` | `2026-11-19T04:35Z` | Deployed & verified on Server 1 | UPLA execution `upla-20261119-042818-aac442`. All 26 pytest tests passed on Server 1. Frontend rebuilt. Health check `healthy`. |
| **V8.3a Target Hotfix** | `HEAD` (Local) | `2026-11-19T04:45Z` | Evidence-verified reasoning guardrails hotfix | Replaces narrative-keyword searches with evidence-backed verification in `ReasoningIntegrityEngine`. |

---

## 2. Server 1 Live Baseline Audit

The live Verdictum Core deployment on Server 1 (`172.26.41.240`) was audited via direct API inspection:

- **System Health:** `healthy` (HTTP 200 via `http://172.26.41.240/api/health`).
- **PostgreSQL Database:** Active, zero connection pool exhaustion.
- **Redis & Celery Workers:** `healthy`, background queue active.
- **Active Rule Version:** Policy v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`).
- **Candidate Policy:** Policy v8 (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `DRAFT`, Quality Score `85.0`, G1–G7 PASS, G8 BLOCKED).
- **Sibling Rule Status:** `Heavy TCP Host Scan` (UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`, `APPROVED v2`, `ACTIVE`).
- **Total Historical Incidents Available:** Exactly `69` in live database.
  - Rich FortiGate Telemetry Incidents: `32` (with raw connection logs, firewall actions, and packet bytes).
  - Header-Only Incidents: `37` (FortiSIEM aggregation headers only, zero raw events).
- **Total Real Human Analyst Reviews:** Exactly **`0`** (`total_analyst_reviews = 0`, `verified_tp = 0`, `verified_fp = 0`).
- **Empirical Accuracy Status:** **`NOT MEASURABLE`** (honest reporting, zero synthetic labels).
- **Production Automation Status:** **`DISABLED`** (`is_enabled: false`, zero automated closures against FortiSIEM).

---

## 3. Server 2 (Verdictum Cortex) LLM Baseline Audit

The live Local LLM inference engine on Server 2 (`13.204.214.64:8000`) was verified:

- **Model Identifier:** `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **Inference Server:** `vLLM` (OpenAI-compatible `/v1/chat/completions`)
- **Max Model Context Length:** `4,096` tokens
- **Reserved Completion Budget:** `768` tokens
- **Available Prompt Token Budget:** `3,328` tokens
- **Instance State:** Unchanged and un-restarted (GPU billing safeguards strictly enforced).

---

## 4. Component Inventory & Audit Findings

| Component | File Path | Audit Finding | V8.3a Hotfix Action |
| :--- | :--- | :--- | :--- |
| **`ReasoningIntegrityEngine`** | `backend/app/services/reasoning_integrity_engine.py` | V8.3 relied on `any(term in combined_narrative)` keyword checks for threat corroboration and scanner authorization, susceptible to model prose hallucination and negated claims. | **CRITICAL FIX:** Replaced narrative-keyword trust with evidence-backed verification (`verify_threat_corroboration` and `verify_authorization`). |
| **`IndependentVerdictValidator`** | `backend/app/services/independent_verdict_validator.py` | Line 236 hardcoded `VERDICT_EVIDENCE_CONFLICT` overriding specific status. | Repaired to propagate `consistency_res.validation_status` cleanly. |
| **`ModelClaimExtractor`** | `backend/app/services/model_claim_extractor.py` | Verified claim grounding against `CanonicalEvidenceRecord`. Catches hallucinated entities. | Verified operational. |
| **`HistoricalGroundTruthValidator`** | `backend/app/services/historical_ground_truth_validator.py` | Deep recursive stripping of 26 resolution/analyst keys prevents data leakage. | Verified operational. |
| **`AnalystReviewService`** | `backend/app/services/analyst_review_service.py` | Double-blind masking, dispute detection, duplicate idempotency, and post-submission reveal verified. | Verified operational. Tested via fixtures. |
| **`VerifiedSemanticRetrievalService`** | `backend/app/services/verified_semantic_retrieval_service.py` | Precedent retrieval strictly filters for `VERIFIED` labels and enforces tenant isolation. | Verified operational. Zero precedents in DB currently. |
| **`RuleLearningDashboard` (UI)** | `frontend/src/components/learning/RuleLearningDashboard.tsx` | Double-Blind Review Workbench tab verified with incident queue, sanitized evidence, and masked AI shield. | Verified operational on Server 1 frontend. |
