# 13 — Test Code & Documentation Audit

## 1. Test Execution Summary
- **Frontend Unit Tests (`frontend/tests/*.mjs`)**: 16 suites, **ALL PASS** (`node --experimental-strip-types --test`).
- **Backend Pytest Collection**: 665 tests collected across 101 non-browser test files; 5 files in `backend/tests/e2e_browser/` require `playwright` (not installed in `backend/venv`).
- **Backend Core & Infra Runs**: 124/125 core tests PASS; 14/15 infra tests PASS.

### Failing / Stale Test Assertions Discovered
1. `backend/tests/test_database_migrations.py:14` (`test_get_head_revision_matches_current`): Asserts Alembic head `== "008_soc_pilot"`, failing against actual head `"016_ground_truth_certification_and_cohort_isolation"`.
2. `backend/tests/test_phase1_security_controls.py:231` (`test_req03_unapproved_prompt_draft_abstained_in_live_triage`): Asserts `validation_status == "POLICY_NOT_APPROVED"`, failing because `PolicyEligibilityService` returns `"DRAFT_NOT_APPROVED"`.

## 2. Scripts, Scratch & Documentation Hygiene
- **`scratch/`**: 31 tracked files (3,062 lines) + 59 untracked local files despite `scratch/` being listed in `.gitignore`. Tracked scratch files are one-off debugging/manifest/probe scripts — candidate for archival (`ARCHIVE`) out of git tracking.
- **`scripts/`**: 39 operational & phase acceptance scripts (e.g., `run_v1_2*_validation.mjs`, `setup_v1_2_*_state.py`, `query_*.py`, `inspect_335.py`, `recover_v7_live.py`). Separate active CI/smoke tools (`validate_feature_registry.py`, `run_integration_suite.py`) from historical phase scripts (`ARCHIVE` in a future documentation/script cleanup pass).
- **`backend/app/scripts/cleanup_incidents.py` (114L)**: Destructive DB purge script with 0 references in code or docs -> `VERIFY_FIRST` (retain only behind explicit admin warning or move to `backend/scripts/`).
- **`docs/`**: 1,689 tracked files (154,003 lines) across historical phase evidence folders. **Preserve untouched** as historical audit trail.

## 3. Audit Commands & Results

| Command | Status | Notes |
|---|---|---|
| `git status --short && git rev-parse HEAD` | `PASS` | 0 modified tracked files, 80 untracked files in docs/AIS_2_7/ |
| `python docs/CCA_1_0/audit_scripts/build_inventory.py` | `PASS` | 2229 tracked files; 272 app source files (104,272 total lines) |
| `npx.cmd tsc --noEmit (in frontend/)` | `PASS` | Exit code 0, zero TypeScript compilation errors |
| `npx.cmd eslint src --format json (in frontend/)` | `PASS_WITH_FINDINGS` | Exit code 1: 362 errors (308 no-explicit-any, 34 set-state-in-effect, etc.), 258 warnings (232 no-unused-vars) |
| `npm.cmd test (in frontend/)` | `PASS` | All 16 Node test suites passed |
| `python docs/CCA_1_0/audit_scripts/analyze_frontend_and_api.py` | `PASS` | 31 frontend pages (13 shadowed), 187 API endpoints (20 without FE refs) |
| `python docs/CCA_1_0/audit_scripts/analyze_backend_and_db.py` | `PASS` | 38 DB models mapped, 309 unused imports, 19 modules with 0 prod importers (11 nomenclature shims) |
| `python docs/CCA_1_0/audit_scripts/deep_audit.py` | `PASS` | 20 unused service methods in prod (7 with 0 tests/scripts), 2 unused settings keys |
| `python docs/CCA_1_0/audit_scripts/audit_ais_and_deps.py` | `PASS` | 17 unused api.ts methods (excluding local helper), 22 Python deps, 15 Node deps |
| `pytest --collect-only -q tests/ (in backend/)` | `PARTIAL` | 665 tests collected; 5 e2e_browser tests errored on missing playwright package |
| `pytest -q --ignore=tests/e2e_browser tests/test_agentic_nomenclature.py tests/test_auth.py tests/test_database_migrations.py tests/test_celery_queues.py` | `PARTIAL` | 14 passed, 1 failed (test_database_migrations.py asserts stale head '008_soc_pilot' vs '016_ground_truth_certification_and_cohort_isolation') |
| `pytest -q tests/test_ais_evaluation_tracking.py ... (13 core suites, 125 tests)` | `PARTIAL` | 124 passed, 1 failed (test_phase1_security_controls.py asserts stale 'POLICY_NOT_APPROVED' vs 'DRAFT_NOT_APPROVED') |
