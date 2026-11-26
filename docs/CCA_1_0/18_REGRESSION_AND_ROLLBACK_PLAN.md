# 18 — Regression Validation & Rollback Plan

## 1. Mandatory Pre-Batch Gate
1. Confirm clean Git working tree and create a dedicated cleanup branch per batch (e.g., `chore/cca-1.1-batch-1`).
2. Record pre-batch test baseline:
   - Frontend: `cd frontend && npx tsc --noEmit && npm.cmd test && npm.cmd run build`
   - Backend: `cd backend && .\venv\Scripts\pytest.exe --ignore=tests/e2e_browser`
3. Verify `APP_ENV=testing` and in-memory SQLite (`conftest.py`) — **never** run cleanup tests against production PostgreSQL.

## 2. Per-Batch Regression Suite Requirements
- **Batch 1 (Low-risk imports/vars/dead methods/assets/scratch):** `tsc --noEmit`, `eslint`, `npm test`, full non-browser `pytest` suite.
- **Batch 2 (Orphaned FE pages/components, unused config):** `next build` (verify `redirects()` in `next.config.ts` still return 307 to new pages), `npm test`, `pytest`.
- **Batch 3 (Duplicate consolidation — Wilson, helpers, health routes):** Targeted unit tests (`test_rule_learning_platform.py`, `test_ais_2_6a_empirical_validation.py`, `test_system_health_observability.py`) + OpenAPI schema diff check.
- **Batch 4 (Legacy AIS view, CalibrationEvaluationService, DryRun adapter, shims, stale tests):** Full AIS, Pilot, Verdict Intelligence, and Simulation regression suites + Playwright UI smoke checks.
- **Batch 5 (`@tailwindcss/turbopack`):** Full production `npm run build` and CSS bundle diff.
- **Batch 6 (Restricted DB & Systemd Beat):** Explicit DB backup (`deployment/scripts/backup_db.sh`), Alembic revision verification, staging dry-run, and explicit operator approval.

## 3. Rollback Strategy
- Each batch is committed atomically (`1 batch = 1 PR/commit`).
- Immediate rollback: `git revert <commit_sha>` (for source/config) or `deployment/scripts/rollback_server1.sh <APPROVED_COMMIT_SHA>` (for Server 1).
- Database rollback (Batch 6 only): Restore via `backend/app/scripts/restore.py` / `pg_restore` prior to any Alembic downgrade.
