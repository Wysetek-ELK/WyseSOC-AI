# Verdictum AI — CCA 1.0 Executive Summary

**Audit Phase:** CCA 1.0 (Complete Codebase Audit, Dead Code Detection, Redundancy Analysis & Safe Cleanup Planning)
**Repository Branch:** `feature/phase3-compact-ui`
**Baseline Commit:** `1e099d5b5954f6921e154ce124d04e604f466d9e`
**Safety Posture:** Read-Only Audit (`0` application files modified, `0` deletions, `0` production changes)

---

## 1. Executive Metrics Summary

| Metric | Actual Result | Notes / Methodology |
|---|---|---|
| Total application source files | 272 | `frontend/src/` (82 code files) + `backend/app/` (190 Python files), excluding tests, Alembic migrations, docs, scratch, and assets |
| Total application lines of code | 104,272 | Raw lines (93,853 non-blank, non-comment code lines) |
| Frontend source files | 82 | `frontend/src/` TS/TSX/CSS (45,559 lines) |
| Backend source files | 190 | `backend/app/` Python (58,713 lines) |
| Confirmed unused files | 15 | 13 redirected legacy `page.tsx` wrappers + 2 orphaned components (`PhasePlaceholder.tsx`, `CompactGovernancePanels.tsx`); plus 5 unused default SVGs in `frontend/public/` |
| Possibly unused files | 1 | 1 deployment script/unit mismatch + 11 compatibility shims (`REQUIRED_COMPATIBILITY`) + `calibration_evaluation_service.py` (`DUPLICATE`) |
| Confirmed unused functions / methods / exports | 13 | 7 backend service methods (0 prod/test/script refs) + 3 top-level backend symbols + 3 unused exported UI primitives in `CompactDesignSystem.tsx` |
| Unused frontend components | 5 | `PhasePlaceholder`, `CompactGovernancePanels` (3 components), plus `RuleStatusSummary`, `EmptyState`, `ErrorState` in `CompactDesignSystem.tsx` |
| Potentially unused API endpoints | 12 | Out of 187 endpoint handlers (20 lack frontend refs; 8 are dev/health/metrics/AIS 2.7 admin) |
| Duplicate implementations | 5 | Frontend page badge/epoch helpers, `WilsonScoreEvaluator`, `CalibrationEvaluationService`, `DryRunService`/`EvaluationService`, `/api/health` + `/api/metrics` dual mounts |
| Legacy AIS implementations | 4 | AIS 7-tab Legacy View toggle (`VERDICTUM_COMPACT_UI_ENABLED`), `CalibrationEvaluationService`, `DryRunService` adapter, 11 nomenclature alias shims |
| Potentially unused dependencies | 1 | `@tailwindcss/turbopack` (requires `next build` verification) |
| Confirmed removable lines (app source) | 1,336 | Non-overlapping lines across `CONFIRMED_UNUSED` app source findings (plus 3,062 lines in tracked `scratch/` = 4,398 total) |
| Conditional removable lines | 3,487 | Requires consolidation/refactor/test updates (e.g., Legacy 7-tab AIS View ~1,800L, `DryRunService`+`EvaluationService` 951L, `api.ts` unused methods, shims) |
| Estimated safe code reduction percentage | 1.28% | `1336 / 104272` (app source only, non-overlapping) |
| Low-risk cleanup candidates | 243 | Imports, unused vars, dead helpers, shadowed 3-line pages, SVGs, tracked scratch |
| Medium-risk cleanup candidates | 15 | Unwired `api.ts` client methods (wait: grouped/individual), dual `/api/v1` mounts, `CalibrationEvaluationService`, DB column review |
| High-risk cleanup candidates | 3 | AIS Legacy View refactor, `DryRunService`+`EvaluationService` adapter, `ai-verdict-scheduler.service` / Celery Beat mismatch |
| Critical-risk cleanup candidates | 2 | 2 DB schema columns (`TokenUsageRecord.estimated_cost_usd`, `GroundTruthValidationRecord.is_eligible_for_evaluation`) |
| Candidates requiring manual verification | 240 | Items requiring verification notes, product sign-off, or runtime log checks before removal |
| Actual application files deleted | 0 | Verified by `git status` |
| Actual production changes | 0 | Verified by `git status` |

---

## 2. Key Architectural Findings

1. **Frontend Dead & Duplicate Surface**:
   - **13 legacy route pages** (`admin`, `analyst-attention`, `dry-run`, `evaluation-reports`, `imports`, `incidents`, `incidents/[id]`, `infrastructure`, `learning-history`, `prompt-studio`, `rules`, `rules/[id]`, `settings`) are 3-line re-exports completely shadowed by `frontend/next.config.ts` `redirects()`.
   - **2 orphaned component files** (`PhasePlaceholder.tsx`, `CompactGovernancePanels.tsx`), **3 unused exported primitives** in `CompactDesignSystem.tsx` (`RuleStatusSummary`, `EmptyState`, `ErrorState`), **5 default Next.js SVG assets**, **232 ESLint unused variable/import warnings**, and **17 unused methods** in `frontend/src/lib/api.ts`.
   - `agent-intelligence-studio/page.tsx` has grown to **5,162 lines** because it preserves both the default Compact UI and the full Legacy 7-tab view behind `VERDICTUM_COMPACT_UI_ENABLED`.
2. **Backend Dead Code & Compatibility Layers**:
   - **309 unused imports** across `backend/app/`.
   - **11 agentic nomenclature compatibility shim files** (11–18 lines each, 143 lines total) with **0 production callers** — imported exclusively by `backend/tests/test_agentic_nomenclature.py`.
   - **7 confirmed unused service methods** (0 prod, 0 test, 0 script refs), including `FortiSIEMService.pull_incidents_for_rule` (70 lines), `TokenBudgetService.get_token_accounting` (24 lines), and `AisEvaluationService.get_missing_inference_candidates` (22 lines).
   - **2 unused config keys** (`Settings.APP_NAME`, `Settings.PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED`) and **6 unused Pydantic schemas**.
3. **AIS & Evaluation Pipeline Status**:
   - Live AI verdict generation and policy simulation converge cleanly onto `run_shared_verdict_pipeline` (`backend/app/services/verdict_pipeline.py`).
   - Redundancies exist in evaluation/calibration layers: `WilsonScoreEvaluator` duplicates `EmpiricalAccuracyEvaluator.calculate_wilson_ci`; `CalibrationEvaluationService` overlaps `CalibrationEvaluator`; `DryRunService` (`LEGACY_DRY_RUN_ADAPTER`) + `EvaluationService` run in parallel with `PolicySimulationService` because `/agent-simulation-lab` still uses `/api/dry-run/*`.
4. **Routing & Background Worker Anomalies**:
   - `health.py` + `main.py` double-register `/api/health` & `/api/metrics` and accidentally expose `/api/api/health` & `/api/api/metrics`.
   - `deployment/systemd/ai-verdict-scheduler.service` runs `celery beat`, yet `celery_app.py` defines zero `beat_schedule` entries and zero tasks on the `maintenance` queue (FortiSIEM polling runs in-process via `asyncio` `SentinelIngestWorker`).
5. **Test Suite Findings**:
   - Frontend: **16/16 Node test suites PASS**, `tsc --noEmit` **PASS** (0 errors).
   - Backend: 124/125 core targeted tests pass, 14/15 infra targeted tests pass; **2 stale test assertions** fail against current code (`test_database_migrations.py` expects `008_soc_pilot` vs actual `016_ground_truth_certification_and_cohort_isolation`; `test_phase1_security_controls.py` expects `POLICY_NOT_APPROVED` vs actual `DRAFT_NOT_APPROVED`).

---

## 3. Acceptance Gate Overview

- **PASS:** 10 / 13 gates (`G1`, `G2`, `G3`, `G5`, `G7`, `G8`, `G10`, `G11`, `G12`, `G13`)
- **PARTIAL:** 3 / 13 gates (`G4` live Server 1 access logs unavailable locally; `G6` live Server 1 PostgreSQL metadata unavailable locally; `G9` remote Server 1/2 parity unverified without SSH)
- **FAIL:** 0 / 13 gates

See [19_FINAL_AUDIT_ACCEPTANCE.md](./19_FINAL_AUDIT_ACCEPTANCE.md) and [17_PROPOSED_CLEANUP_IMPLEMENTATION_PLAN.md](./17_PROPOSED_CLEANUP_IMPLEMENTATION_PLAN.md) for next steps. **Wait for explicit approval before commencing CCA 1.1.**
