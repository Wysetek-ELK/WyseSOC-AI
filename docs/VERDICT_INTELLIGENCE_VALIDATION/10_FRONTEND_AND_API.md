# Frontend Dashboards and REST APIs (AIS 2.1)

## 1. Overview and Architecture

Agent Intelligence Studio 2.1 provides a complete full-stack interface for dry-run verdict validation, consisting of:
- **FastAPI Backend Router**: `backend/app/api/verdict_intelligence.py` (mounted at `/api/verdict-intelligence` and `/api/v1/verdict-intelligence`).
- **TypeScript API Client**: `frontend/src/lib/api.ts` with strongly-typed interfaces.
- **Next.js Dashboard**: `frontend/src/app/verdict-intelligence/page.tsx` containing five interactive view modes (Dashboards A through E).

---

## 2. REST API Endpoints Reference

### 1. `POST /evaluate-incident`
Evaluates a single incident payload against a candidate policy, running sufficiency checking, claim extraction, guardrail enforcement, and trustworthiness scoring.
- **Request Body**:
  ```json
  {
    "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
    "incident_id": "INC-88912",
    "telemetry": { "src_ip": "10.0.1.50", "dest_ip": "198.51.100.22", "sentBytes64": 2500000000, "direction": "outbound" },
    "model_suggested_verdict": "TRUE_POSITIVE",
    "model_reasoning": "Detected 2.5 GB transfer to external IP 198.51.100.22."
  }
  ```
- **Response**: `VerdictTrustAssessmentResult` (raw score, ordinal score 1–10, enforced verdict, demotion status, claim verification results, sufficiency breakdown).

### 2. `POST /run-evaluation`
Initiates a batch dry-run evaluation of a policy version against a historical incident cohort.
- **Request Body**:
  ```json
  {
    "policy_version_id": "pol-v2-exfil",
    "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
    "partition": "BLIND_BENCHMARK",
    "sample_limit": 50
  }
  ```
- **Response**: `HistoricalEvaluationRunRecord` with status `COMPLETED` and summary metrics.

### 3. `GET /runs/{run_id}`
Retrieves complete evaluation run details, including confusion matrix, Wilson 95% CIs, reliability diagram bins, and risk-coverage curve points.

### 4. `POST /runs/compare`
Compares a candidate evaluation run against a baseline run, performing paired regression detection.
- **Request Body**:
  ```json
  {
    "baseline_run_id": "run-base-101",
    "candidate_run_id": "run-cand-102"
  }
  ```
- **Response**: `RegressionComparisonReport` (`status: VALIDATED | REGRESSION_DETECTED | INSUFFICIENT_DATA`).

### 5. `GET /rules/{rule_id}/metrics`
Returns aggregated historical accuracy, average trust score, calibration status, and sample size for a specific detection rule.

### 6. `GET /export`
Exports evaluation run records and drill-down results in structured format.
- **Query Params**: `run_id=<id>&format=json|csv`
- **Output**: Returns either JSON payload or streaming `text/csv` attachment for external reporting.

---

## 3. Next.js Dashboard Structure (A through E)

The dashboard page (`frontend/src/app/verdict-intelligence/page.tsx`) features a top-level tab switcher to toggle between five specialized analytical modes:

### Dashboard A: Verdict Trust & Sufficiency Overview
- **Key Cards**: Average Trust Score (1–10 gauge), Evidence Sufficiency Pass Rate (%), Demotion Rate (%), Active Calibrated Rules Count.
- **Visualizations**: Sufficiency dimension breakdown bar charts (Coverage, Integrity, Consistency, Freshness) and recent incident evaluations stream.

### Dashboard B: Empirical Accuracy & Calibration Lab
- **Performance Table**: Balanced Accuracy, Precision, Recall, Specificity, F1-Score with Wilson 95% confidence intervals.
- **Interactive Graphs**:
  - **5-Bin Reliability Diagram**: Plots predicted confidence vs. observed accuracy with the ideal calibration line.
  - **Selective Risk-Coverage Curve**: Illustrates selective risk reduction as coverage thresholds are varied.

### Dashboard C: Rule-Wise & Archetype Trustworthiness Matrix
- **Matrix View**: Tabulates all 2,000+ SIEM rules grouped by detection archetype (Exfiltration, Brute Force, C2, Ransomware).
- **Columns**: Rule Identifier, Archetype, Verified Samples ($N$), Calibrated Status (`CALIBRATED` / `NOT_CALIBRATED`), Average Trust Score (1–10 badge), Enforcement Status.

### Dashboard D: Incident Drill-Down & Claim Grounding Explanation
- **Side-by-Side Inspector**:
  - Left Panel: Raw SIEM Telemetry with syntax highlighting.
  - Right Panel: Model Reasoning text with color-coded token annotations:
    - 🟩 Green highlight: Factually grounded entity (verified IP/domain/byte count).
    - 🟥 Red highlight: Hallucinated / unsupported entity.
    - 🟨 Amber highlight: Phantom threshold assertion or directional contradiction.
- **Guardrail Decision Log**: Detailed breakdown of triggered guardrails G1–G7, demotion rationale, and contract compliance.

### Dashboard E: Historical Replay & Paired Regression Studio
- **Run Comparator**: Side-by-side metric comparison between Baseline Policy and Candidate Policy.
- **Paired Diff Viewer**: Highlighting individual incidents where verdict flipped from TP to FP or vice versa.
- **Validation Banner**: Prominent badge displaying `VALIDATED` (Green) or `REGRESSION DETECTED` (Red) with specific blocker reasons.
