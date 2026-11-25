# 11 — Security & Regression Validation Report

- **Backend Test Run**: `47 passed in 33.15s` across 8 suites (`test_ais_2_6f_certification_and_blind_review.py`, `test_investigations.py`, `test_ais_2_6d_empirical_integrity.py`, `test_ais_2_6c_three_mode_and_bias_isolation.py`, `test_ground_truth_isolation.py`, `test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`).
- **Frontend Production Build**: Next.js 16.4.5 (`npm run build`) compiled cleanly (`0` TypeScript errors, `32` routes).
- **UPLA Governance (`upla-20261125-023922-feb3fd`)**: `profile=release`, `7/7` governance checks `PASS`, `0` new security findings, `blockingReasons: []`.
