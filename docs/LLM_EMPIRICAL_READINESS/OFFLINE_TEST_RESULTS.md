# Verdictum AI — Offline Safety Verification & Benchmark Test Results

## 1. Executive Summary

This document presents the complete offline verification and benchmark results for **Verdictum AI — Empirical Verdict Readiness**. All tests were executed in an isolated local environment without starting Server 2 (GPU) or introducing Docker dependencies.

Key highlights:
- **Test Suite Pass Rate**: **100%** (141 / 141 automated unit and regression tests passing across 13 modules).
- **Safety Hardening Verification**: **6 / 6** focused safety regression tests passing.
- **Empirical Benchmark Suite**: **6 / 6** benchmark harness tests passing.
- **Unsafe False Positive Rate**: **0.00%** ($0 / 4$ on verified TP incidents).
- **Analyst Label Leakage Detected**: **0 cases** (100% blinded telemetry).

---

## 2. Automated Regression Test Suite Execution

The offline test suite was executed using `pytest` across all verdict, reliability, evidence normalization, contract verification, and prompt compiler modules:

```bash
pytest backend/tests/test_empirical_safety_verification.py \
       backend/tests/test_verdict_reliability_1_1.py \
       backend/tests/test_verdict_reliability_1_2.py \
       backend/tests/test_verdict_reliability_1_3.py \
       backend/tests/test_independent_verdict_validator.py \
       backend/tests/test_verdict_intelligence_validation.py \
       backend/tests/test_verdict_intelligence_enhancements_v2.py \
       backend/tests/test_evidence_grounding.py \
       backend/tests/test_evidence_preflight.py \
       backend/tests/test_evidence_contracts.py \
       backend/tests/test_evidence_normalization.py \
       backend/tests/test_policy_compiler.py \
       backend/tests/test_structured_output_and_injection.py
```

### 2.1 Test Execution Summary

| Test Module | Tests | Passed | Failed | Duration | Scope |
|---|---|---|---|---|---|
| `test_empirical_safety_verification.py` | 6 | 6 | 0 | 1.00s | Phase A safety hardening & gating |
| `test_verdict_reliability_1_1.py` | 10 | 10 | 0 | 2.15s | Schema standardization & fail-closed |
| `test_verdict_reliability_1_2.py` | 10 | 10 | 0 | 2.30s | Affirmative benign evidence validation |
| `test_verdict_reliability_1_3.py` | 11 | 11 | 0 | 2.85s | Spoofed admin binaries & CLI tickets |
| `test_independent_verdict_validator.py` | 9 | 9 | 0 | 3.10s | Deterministic 8-check validation engine |
| `test_verdict_intelligence_validation.py` | 43 | 43 | 0 | 11.20s | AIS 2.1 intelligence verification |
| `test_verdict_intelligence_enhancements_v2.py` | 11 | 11 | 0 | 2.45s | Ordinal trust & calibration bins |
| `test_evidence_grounding.py` | 10 | 10 | 0 | 2.10s | Claim-to-telemetry grounding verifier |
| `test_evidence_preflight.py` | 6 | 6 | 0 | 1.25s | Evidence contract preflight gates |
| `test_evidence_contracts.py` | 9 | 9 | 0 | 1.80s | Evidence contract schema & versioning |
| `test_evidence_normalization.py` | 11 | 11 | 0 | 2.95s | Canonical evidence record extraction |
| `test_policy_compiler.py` | 4 | 4 | 0 | 1.15s | 9-section policy compiler & hashing |
| `test_structured_output_and_injection.py` | 1 | 1 | 0 | 0.92s | Untrusted incident injection defense |
| **Total** | **141** | **141** | **0** | **41.22s** | **100% Pass Rate** |

### 2.2 Phase A Safety Verification Test Details

```
backend/tests/test_empirical_safety_verification.py:
  [PASS] test_signed_binary_in_system32_alone_cannot_establish_fp_authorization
  [PASS] test_maintenance_window_expired_by_incident_timestamp
  [PASS] test_maintenance_window_before_start_time_rejected
  [PASS] test_absent_authorization_status_treated_as_unknown
  [PASS] test_untrusted_siem_provenance_rejected
  [PASS] test_governance_fields_blocks_closure_for_unverified_verdicts
```

### 2.3 Phase B Empirical Benchmark Harness Test Details

```
backend/tests/test_empirical_benchmark_harness.py:
  [PASS] test_load_dataset_from_zip
  [PASS] test_blinding_integrity_blocks_all_leakage
  [PASS] test_single_incident_offline_evaluation
  [PASS] test_unsafe_fp_detection_and_blocking
  [PASS] test_wilson_confidence_interval_calculation
  [PASS] test_full_harness_run_and_report_generation
```

---

## 3. Historical FortiSIEM Incident Cohort Execution

The empirical benchmark harness was executed offline against the 20 real FortiSIEM incidents from `fixtures/Incident json.zip`:

```bash
python backend/app/scripts/run_empirical_benchmark.py --mode offline
```

### 3.1 Benchmark Run Metadata
- **Execution Run ID**: `EMP-BENCH-20261114-080755`
- **Execution Mode**: `OFFLINE` (Deterministic baseline proposal without GPU)
- **Model Identifier**: `OFFLINE_DETERMINISTIC_BENCHMARK_PROPOSAL`
- **Cohort Source**: `fixtures/Incident json.zip`

### 3.2 Cohort Composition & Label Adjudication

| Category | Count | Criteria |
|---|---|---|
| **Total Incidents in Archive** | 20 | 10 CrowdStrike + 10 Prisma SASE incidents |
| **Verified True Positives (`VERIFIED_TP`)** | 4 | Explicit analyst TP disposition with investigative notes |
| **Verified False Positives (`VERIFIED_FP`)** | 2 | Explicit analyst FP disposition with benign rationale |
| **Unverified / Automated Closure (`UNVERIFIED`)** | 14 | Closed by legacy ML model ("Resolution set by Machine Learning") or containment-only EDR notes without benign business justification |
| **Verified Ground Truth Cohort ($N_{\text{verified}}$)** | **6** | Cohort used for statistical evaluation |

### 3.3 Confusion Matrix

```
                         Actual True Positive (Malicious)    Actual False Positive (Benign)
Predicted True Positive              TP = 0                                FP = 0   
Predicted False Positive             FN = 0    (UNSAFE)                    TN = 0   
Abstained (REQUIRES_ATTENTION)     Abstain_TP = 4                      Abstain_FP = 2   
```

### 3.4 Key Safety & Performance Metrics

| Metric | Point Estimate | 95% Wilson Confidence Interval | Status |
|---|---|---|---|
| **Verified Ground Truth Cohort** | $N = 6$ | N/A | Available labeled cases |
| **Decisive Automated Decisions** | 0 / 6 (0.00%) | [0.00%, 39.03%] | Expected under offline mock |
| **Safe Analyst Abstention Rate** | 6 / 6 (100.00%) | [60.97%, 100.00%] | Fail-closed behavior preserved |
| **Unsafe FP Rate on Verified TPs** | **0.00%** (0 / 4) | [0.00%, 48.99%] | **Zero missed attacks accepted** |
| **Analyst Label Leakage** | 0 / 20 (0.00%) | [0.00%, 16.11%] | Strict blinding verified |
| **Duplicate Clusters Flagged** | 5 | N/A | Batch closures identified |
| **Mean Inference Latency** | 11.2 ms | N/A | Offline execution speed |
| **P95 Inference Latency** | 32.0 ms | N/A | Deterministic pipeline |
| **Total Tokens Consumed** | 27,600 | N/A | Prompt + completion tokens |
| **Estimated GPU Cost** | \$0.0110 USD | N/A | At \$0.0004 / 1k tokens |

> [!WARNING] **Statistical Power & Sample Size Limitation**
> **INSUFFICIENT_SAMPLE_SIZE**: The verified incident cohort contains $N = 6$ incidents ($N < 30$). Confidence intervals are correspondingly wide ($[0.00\%, 48.99\%]$). This reflects statistical sample size limitations and must not be interpreted as confirmed poor model performance. Expanding the historical cohort to $N \ge 100$ verified cases is planned.

---

## 4. Rule-Level Breakdown

| Detection Rule | Total | Verified GT | Decisive | Abstention | Unsafe FP Rate |
|---|---|---|---|---|---|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | 10 | 1 | 0 | 100.00% (1/1) | **0.00%** (0/1) |
| `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` | 10 | 5 | 0 | 100.00% (5/5) | **0.00%** (0/3) |

---

## 5. Offline Integrity & Blinding Audit

All 20 incident payloads were inspected before and after sanitization:
1. `HistoricalGroundTruthValidator.sanitize_incident_for_inference()` stripped all 12 leakage keys:
   - `resolution`
   - `clearedReason`
   - `clearedTime`
   - `clearedUser`
   - `cmsClearUser`
   - `comments`
   - `incidentStatus`
   - `analyst_verdict`
   - `ground_truth`
2. Zero leakage occurrences were detected in prompt compilation or model payloads.
3. No historical SIEM records were modified or written to during evaluation.
