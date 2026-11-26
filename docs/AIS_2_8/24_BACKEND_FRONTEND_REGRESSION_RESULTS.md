# 24 — Backend & Frontend Regression Test Results

| Suite | Scope | Exact Executed Result |
|---|---|---|
| Backend Pytest AIS 2.8 + 2.7 + Config + Monitor + Harness (10 files) | `backend\venv\Scripts\pytest.exe backend/tests/test_ais_2_8_intelligence.py ... -q` | **55 passed in 34.10s** |
| Frontend Unit & Governance Suite | `npm.cmd --prefix frontend test` (16 `.mjs` test files) | **Passed (exit 0)** |
| Frontend Production Build + TypeScript | `npm.cmd --prefix frontend run build` | **Passed (3.0s compile, 8.0s TS, 32 routes, exit 0)** |
| UPLA Static Security & Governance | `upla.ps1 run-governance` (`upla-20261126-040528-b67309`) | **security: PASS, governance: WARNING (ruff not installed; frontend eslint exited 1)** |
