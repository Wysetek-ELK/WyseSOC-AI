# AIS 3.2 — 19: Backend & Frontend Regression Results

- `backend/tests/test_ais_3_2_universal_intelligence.py`: **7 passed, 0 failed**.
- Regression sweep across 17 suites (`AIS 2.3a–3.2`, `agent-intelligence-studio-v2`, validator, harness, learning, Phase 1): **141 passed, 1 pre-existing Phase 1 failure** (`DRAFT_NOT_APPROVED` vs `POLICY_NOT_APPROVED`). Legacy `test_database_migrations.py` also contains pre-existing `assert head == '008_soc_pilot'`.
- Server 1 remote pytest smoke tests (`test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`): **PASS**.
- Frontend tests (`18` test suites including `ais-3-2-ui-integrity.test.mjs`) & `next build`: **PASS**. Pre-existing ~369 ESLint issues remain documented debt.
