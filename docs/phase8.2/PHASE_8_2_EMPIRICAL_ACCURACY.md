# Phase 8.2 — Stage F Empirical Accuracy & Calibration Certification

**Evidence Sources:**
- `docs/phase8.2/evidence/metrics/stage_f_empirical_accuracy_and_calibration.json`
- `backend/tests/test_phase8_2_validation.py` (`test_p8_2_def_003_004_zero_denominator_and_class_balance_metrics`)

## 1. Per-Rule Simulation Results (Post `P8.2-DEF-001`–`P8.2-DEF-004` Fixes)

| Rule Code | Candidate Policy | Matched | Eligible Independent Groups | Simulation Status | Decision Coverage | Balanced Accuracy / Precision / Recall / Specificity | Calibration Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `v1 (APPROVED)` | 10 | 3 | `INSUFFICIENT_DATA` | `0.0` | `null` (never `100%`) | `NOT_CALIBRATED` |
| `PH_RULE_DEBUG_FUNNEL` | `v1 (DRAFT)` | 6 | 0 | `INSUFFICIENT_DATA` | `0.0` | `null` (never `100%`) | `NOT_CALIBRATED` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `v2 (DRAFT)` | 0 | 0 | `INSUFFICIENT_DATA` | `0.0` | `null` (never `100%`) | `NOT_CALIBRATED` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `v1 (APPROVED)` | 10 | 3 | `INSUFFICIENT_DATA` | `0.0` | `null` (never `100%`) | `NOT_CALIBRATED` |

## 2. Empirical Metric Integrity Fixes (`P8.2-DEF-003` & `P8.2-DEF-004`)

- **Zero-Denominator Protection (`N=0`, `decisive=0`, All-Abstained):**
  - `EmpiricalAccuracyEvaluator` sets `metric_status = "NOT_CALCULABLE"` and `balanced_accuracy = None` with explicit `balanced_accuracy_reason` (never returning `1.0` / `100%`).
  - `_sanitize_run_metrics` in `backend/app/api/verdict_intelligence.py` retroactively sanitizes legacy `HistoricalEvaluationRunRecord` rows (`get_evaluation_run_details`, `list_evaluation_runs`) and sets `average_trust_score = None` when `sample_count == 0` in `get_rule_wise_trustworthiness`.
- **Single-Class Balanced Accuracy Integrity:**
  - When verified TP or FP support is missing in decisive verdicts (`recall_denominator == 0` or `specificity_denominator == 0`), `balanced_accuracy = None` and `metric_status = "INSUFFICIENT_CLASS_BALANCE"` rather than halving with an artificial `0.0` or `1.0` component.
- **Uncalibrated Ordinal Trust Parity (`P8.2-DEF-006`):**
  - `VerdictTrustworthinessEngine.compute_trust_score` respects explicit `is_calibrated=False` even when `historical_sample_size >= 30`, keeping `calibrated_probability = None` and UI displaying `Uncalibrated Ordinal`.
- **Overall Empirical Certification:** `NOT_ESTABLISHED` (`server2_live_replay_status = "BLOCKED"`, insufficient independent ground truth `< 5` groups per rule).

