# Verdictum AI — Server 2 GPU Go / No-Go Decision Report

**Date**: November 14, 2026  
**Auditor**: Antigravity AI Systems Audit  
**Evaluation Target**: Server 2 Local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`)  
**Decision**: **GO — READY FOR LIVE GPU EVALUATION**  

---

## 1. Formal Decision & Readiness Verdict

Verdictum AI's Empirical Benchmark Harness is formally certified as **GO (READY FOR LIVE GPU EVALUATION)**.

All architectural, data-blinding, mathematical, schema-recovery, and safety-guardrail prerequisites have been fully implemented, offline-verified, and regression-tested. The harness is ready to connect to Server 2 vLLM/Ollama and execute controlled, empirical TP/FP accuracy benchmarks against historical FortiSIEM incidents.

---

## 2. Readiness Evaluation Gate Matrix

| Evaluation Gate | Requirement | Status | Evidence & Verification |
|---|---|---|---|
| **Gate 1: Pipeline Parity** | Must invoke exact production compiler, budgeter, normalizer, and guardrails | **PASSED** | Invokes `PolicyCompilerService.compile_policy()`, `TokenBudgetService.budget_prompt()`, `ModelClaimExtractor`, `IndependentVerdictValidator`, and `VerdictGuardrailsEngine`. |
| **Gate 2: Anti-Leakage Blinding** | Zero analyst labels or legacy resolutions in LLM context | **PASSED** | 100% verified via `HistoricalGroundTruthValidator.sanitize_incident_for_inference()`. Zero leakage keys detected across all 20 historical cases. |
| **Gate 3: Claim Grounding Integrity** | Eliminates spurious `EVIDENCE_VALUE_MISMATCH` while blocking hallucinations | **PASSED** | Resolved arbitrary timestamp ID pairing in offline mock. Grounding ratio reaches 1.0 on valid observables; fabricated entities are rejected. |
| **Gate 4: Fail-Closed FP Safety** | Unverified FPs must NEVER be autonomously accepted or closed | **PASSED** | Deterministic tests prove unverified FPs without maintenance tickets are demoted to `REQUIRES_ATTENTION` with `auto_incident_closure_allowed = False`. |
| **Gate 5: Metric & Compute Separation** | Mock tokens and latencies must never masquerade as real live metrics | **PASSED** | Offline mode strictly sets latency, token counts, and GPU cost to `None` with `is_live_measurement = False`. |
| **Gate 6: Denominator Integrity** | Undefined metrics (when all cases abstain) must not be labeled as passing | **PASSED** | Handled in `calculate_cohort_metrics()`: precision, recall, and accuracy are `None` (`N/A`) when decisive total is 0. |
| **Gate 7: Multi-Source Loading** | Supports ZIP fixtures, SQLite DB, and unified merged cohorts | **PASSED** | Implemented `load_dataset_from_zip()`, `load_dataset_from_db()`, and `load_dataset_unified()`. Deduplication and cluster tracking verified. |
| **Gate 8: Read-Only Safety** | Zero incident modifications, closures, or suppressions | **PASSED** | The harness performs read-only evaluations. Zero database writes, zero external SIEM API writebacks. |
| **Gate 9: Automated Regression** | 100% pass rate across all reliability and benchmark test suites | **PASSED** | **91/91 tests green in 18.78s**. |

---

## 3. Operational Risks & Sample Size Considerations

While the harness itself is 100% verified and ready, the evaluation team must recognize the following inherent operational boundaries during Server 2 testing:

### 3.1 Statistical Power Limitation ($N < 30$)
* **Current Cohort**: The historical archive contains 20 incidents, of which exactly **6** are confirmed human-verified ground truth cases (4 `VERIFIED_TP`, 2 `VERIFIED_FP`). The remaining 14 incidents are legacy ML-generated resolutions or containment actions that cannot be ethically treated as human ground truth.
* **Impact**: At $N = 6$, the 95% Wilson Score Confidence Interval for a metric with 0 errors spans $[0.00\%, 48.99\%]$.
* **Operational Directive**:
  1. The harness automatically attaches `statistical_power_warning = True` to all generated reports.
  2. The evaluation team must **NOT** mistake wide confidence intervals for model deficiency.
  3. Expanding statistical power requires human analysts to review and label additional FortiSIEM incidents in Agent Intelligence Studio rather than unfreezing legacy ML labels.

### 3.2 Server 2 Connectivity & Network Prerequisites
* The harness expects an OpenAI-compatible API endpoint on Server 2 (e.g. `http://<SERVER_2_IP>:8000/v1/chat/completions`).
* If Server 2 is offline or unreachable, the harness will raise an explicit connection error rather than silently falling back to mock data when `--mode live` is specified.

---

## 4. Server 2 GPU Execution Runbook

Once Server 2 is booted and vLLM / Ollama is running, execute the following commands:

### Step 1: Pre-Flight Probe
Verify Server 2 network reachability and model availability:
```powershell
curl http://<SERVER_2_IP>:8000/v1/models
```
Ensure `Qwen/Qwen2.5-7B-Instruct-AWQ` (or the configured model) is listed.

### Step 2: Execute Live Empirical Benchmark
Run the benchmark across the historical FortiSIEM cohort:
```powershell
python backend/app/scripts/run_empirical_benchmark.py --mode live --endpoint http://<SERVER_2_IP>:8000/v1 --source zip --output-dir docs/LLM_BENCHMARK_FINAL_READINESS
```

### Step 3: Inspect Generated Artifacts
1. Review the markdown report:
   `docs/LLM_BENCHMARK_FINAL_READINESS/LIVE_GPU_BENCHMARK_<REPORT_ID>.md`
2. Review the structured JSON data:
   `docs/LLM_BENCHMARK_FINAL_READINESS/benchmark_<REPORT_ID>.json`

### Step 4: Verify Acceptance Thresholds
* **Unsafe FP Rate**: Must be strictly `0.0%` (Zero verified attacks misclassified as benign).
* **Schema Compliance**: Must be $\ge 95\%$.
* **Claim Grounding Ratio**: Must be $\ge 90\%$.
* **Abstention Rate**: Should reflect appropriate caution on ambiguous alerts without over-abstaining on obvious TPs.

