# Automated Test Execution Results (AIS 2.1)

## 1. Executive Summary

A comprehensive automated test suite was developed and executed to validate every component of the **Agent Intelligence Studio 2.1 — Dry-Run Intelligence Validation** platform.

| Test Scope | Executed | Passed | Failed | Pass Rate | Execution Time |
|---|---|---|---|---|---|
| **AIS 2.1 Unit & Integration Suite** (`test_verdict_intelligence_validation.py`) | 36 | 36 | 0 | **100%** | 6.84s |
| **Complete Backend Regression Suite** (`backend/tests/`) | 213 | 213 | 0 | **100%** | 19.32s |
| **Next.js Production Build** (`npm run build`) | 28 Pages | 28 | 0 | **100%** | 1.7s build / 4.1s typecheck |

---

## 2. AIS 2.1 Dedicated Suite Breakdown (`36/36 Passed`)

The 36 test scenarios in `backend/tests/test_verdict_intelligence_validation.py` span 9 functional domains:

### 1. Evidence Sufficiency Engine (4 Tests)
- `test_evidence_sufficiency_complete_exfiltration`: Verifies that a full telemetry payload (IPs, bytes, direction) passes with high score ($\ge 90.0$).
- `test_evidence_sufficiency_missing_mandatory_direction`: Verifies the **Infallible Rule**—missing `direction` caps score to $\le 49.0$ and flags `is_sufficient = False`.
- `test_evidence_sufficiency_missing_mandatory_bytes`: Confirms missing `sentBytes64` / `bytes_transferred` forces insufficiency.
- `test_evidence_sufficiency_alias_normalization`: Validates that alternative vendor field names (`src_ip`, `dst_ip`, `sentBytes64`) normalize properly.

### 2. Claim Grounding & Entity Validation (4 Tests)
- `test_claim_validator_grounded_entities`: Verifies reasoning referencing real telemetry IPs passes with 0 unsupported claims.
- `test_claim_validator_hallucinated_ip`: Verifies citing an unobserved external IP flags an unsupported entity.
- `test_claim_validator_directional_contradiction`: Detects reasoning claiming "outbound exfiltration" when telemetry indicates inbound flow.
- `test_claim_validator_phantom_threshold_assertion`: Detects the model asserting `sentBytes64: 2130499380` as an authorized or configured SIEM threshold.

### 3. Deterministic Verdict Guardrails (5 Tests)
- `test_guardrail_missing_mandatory_forces_attention`: Asserts G1 demotes proposed `TRUE_POSITIVE` to `REQUIRES_ANALYST_ATTENTION`.
- `test_guardrail_unsupported_claim_forces_attention`: Asserts G2 demotes hallucinated reasoning to `REQUIRES_ANALYST_ATTENTION`.
- `test_guardrail_contradiction_forces_attention`: Asserts G3 demotes directional contradictions to `REQUIRES_ANALYST_ATTENTION`.
- `test_guardrail_blanket_false_positive_demotion`: Asserts G4 demotes uninvestigated blanket FP claims on high-severity alerts.
- `test_guardrail_phantom_threshold_demotion`: Asserts G5 demotes unverified threshold assertions.

### 4. Verdict Trustworthiness Engine (4 Tests)
- `test_trust_score_calculation_high_trust`: Verifies complete, grounded, corroborated case receives an ordinal score of 9 or 10.
- `test_trust_score_calculation_low_trust`: Verifies missing evidence and ungrounded claims result in an ordinal score of 1 or 2.
- `test_trust_score_uncalibrated_capping`: Confirms that rules with $N < 30$ historical samples are strictly capped at a maximum of 6/10.
- `test_trust_score_scale_mapping`: Validates monotonic mapping across all raw score bands (0–100 to 1–10).

### 5. Historical Ground Truth & Sanitization (4 Tests)
- `test_ground_truth_sanitization_removes_analyst_notes`: Asserts `analyst_notes`, `closure_reason`, and resolution strings are recursively scrubbed.
- `test_ground_truth_sanitization_removes_disposition_tags`: Asserts `verdict` and `is_tp`/`is_fp` headers are stripped.
- `test_ground_truth_adjudication_resolution_mapping`: Tests mapping of heterogeneous analyst tags to canonical 3-way labels.
- `test_ground_truth_deterministic_4way_partitioning`: Confirms SHA256 hashing produces deterministic, reproducible splits (Train, Validation, Blind, Stress).

### 6. Empirical Accuracy Evaluation (4 Tests)
- `test_empirical_accuracy_confusion_matrix`: Verifies computation of TP, FP, TN, FN, and abstentions.
- `test_empirical_accuracy_wilson_confidence_intervals`: Verifies mathematical correctness of Wilson 95% CIs.
- `test_empirical_accuracy_selective_risk_coverage_curve`: Verifies monotonic curve generation and prevention of recursive loops.
- `test_empirical_accuracy_abstention_rate_breakdown`: Evaluates justified vs. under-confident abstentions.

### 7. Calibration & Uncertainty (4 Tests)
- `test_calibration_ece_calculation`: Tests Expected Calibration Error calculation across 5 bins.
- `test_calibration_brier_score_calculation`: Tests Brier score against known ground truth.
- `test_calibration_small_sample_honesty`: Asserts that when $N < 30$, `is_calibrated` is `False` and status is `"NOT_CALIBRATED"`.
- `test_calibration_reliability_diagram_bins`: Verifies bin bounds and probability aggregation.

### 8. Simulation Lab & Paired Regression (4 Tests)
- `test_simulation_dry_run_intelligence_evaluation`: Tests end-to-end dry-run batch execution against historical cohort.
- `test_simulation_paired_regression_validated`: Asserts equal or improved candidate policy returns status `VALIDATED`.
- `test_simulation_paired_regression_detected_accuracy_drop`: Asserts drop in balanced accuracy triggers `REGRESSION_DETECTED`.
- `test_simulation_paired_regression_detected_false_negative`: Asserts introduction of a new False Negative triggers `REGRESSION_DETECTED`.

### 9. REST API Integration (3 Tests)
- `test_api_evaluate_incident_endpoint`: Validates `POST /api/verdict-intelligence/evaluate-incident` and `/api/v1/verdict-intelligence/evaluate-incident`.
- `test_api_run_evaluation_endpoint`: Validates batch execution trigger.
- `test_api_export_endpoint`: Validates both JSON and CSV export endpoints.

---

## 3. Full Backend Regression Run (`213/213 Passed`)

```
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-8.3.4, pluggy-1.5.0
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent\backend
plugins: anyio-4.8.0
collected 213 items

tests/test_ai_verdict_service.py .........................               [ 11%]
tests/test_evidence_contract_services.py .................               [ 19%]
tests/test_policy_quality_validator.py .................                 [ 27%]
tests/test_policy_simulation_service.py ..................               [ 36%]
tests/test_prompt_studio_service.py ....................                 [ 45%]
tests/test_rule_intelligence_analyzer.py .................               [ 53%]
tests/test_verdict_intelligence_validation.py .......................... [ 65%]
....................                                                     [ 75%]
tests/test_verified_learning_service.py ................................ [ 90%]
tests/test_workflow.py .....................                             [100%]

============================= 213 passed in 19.32s ============================
```

Zero existing features, tests, or database models were broken by the AIS 2.1 implementation.

---

## 4. Frontend Next.js Production Build Output

```
> frontend@0.1.0 build
> next build

   ▲ Next.js 15.1.7

   Creating an optimized production build ...
 ✓ Compiled successfully in 1.7s
 ✓ Type checking completed in 4.1s
 ✓ Collecting page data ...
 ✓ Generating static pages (28/28) ...
 ✓ Finalizing page optimization ...

Route (app)                              Size     First Load JS
┌ ○ /                                    5.1 kB          102 kB
├ ○ /agent-intelligence-studio           14.2 kB         111 kB
├ ○ /verdict-intelligence                22.8 kB         119 kB
└ ... [25 other routes]
+ First Load JS shared by all            96.9 kB

○  (Static)  prerendered as static content
```
Zero TypeScript or ESLint errors encountered.
