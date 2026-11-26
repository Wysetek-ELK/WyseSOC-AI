# AIS 2.7 — Workstream 21: Regression Testing & Security Validation Report

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [REGRESSION_TEST_RESULTS.json](REGRESSION_TEST_RESULTS.json), [SECURITY_VALIDATION_RESULTS.json](SECURITY_VALIDATION_RESULTS.json), [CHANGE_SCOPE_MANIFEST.json](CHANGE_SCOPE_MANIFEST.json)

## 1. Automated Regression Verification

- **Executed After Last Code Change (UPLA Deploy SHA `1e099d5b5954f6921e154ce124d04e604f466d9e`):**
  - `61 passed, 0 failed, 0 skipped` in `22.95s` across 9 test suites (`test_ais_2_7_benchmark_runner.py`, `test_ais_2_6f_certification_and_blind_review.py`, `test_ais_2_4a_tp_grounding.py`, `test_ais_2_4_regression.py`, `test_ais_2_3b_1_regression.py`, `test_ais_2_3a_integrity.py`, `test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`).
- Also verified remotely on Server 1 during UPLA deployment (`tests/test_ais_heavy_tcp_e2e.py`, `tests/test_rule_learning_platform.py`, `tests/test_api_422_remediation.py`).

## 2. Blind Review & Operational DB Isolation Verification

- **Label Leakage:** `0` GT-2 labels, `0` historical FortiSIEM verdicts, `0` operational `ai_verdict` values in any Mode A/B prompt.
- **Operational DB Diff Across All 20 UUIDs (Pre vs Post Stage 2):** `0` modified incidents, `0` GT queue changes, `[20, 20]` rules unchanged, `0` LearningRecord promotions.
