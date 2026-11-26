# 12 — Duplicate Code & Complexity Analysis

## 1. Confirmed Duplicate Implementations

| Area | Locations | Nature of Duplication | Action |
|---|---|---|---|
| Wilson 95% CI Math | `wilson_evaluator.py` (48L) vs `empirical_accuracy_evaluator.py:34-57` | Identical binomial proportion Wilson interval math | `CONSOLIDATE` (Batch 3) |
| Calibration Evaluation | `calibration_evaluation_service.py` (260L) vs `calibration_evaluator.py` (168L) | Two separate Brier Score & ECE engines | `CONSOLIDATE` (Batch 4) |
| Dry-Run vs Policy Simulation | `dry_run_service.py` (524L) + `evaluation_service.py` (427L) vs `policy_simulation_service.py` (1,492L) | Dual simulation models/tables (`LEGACY_DRY_RUN_ADAPTER` dual-writes) | `REFACTOR` after UI migration (Batch 4) |
| Frontend Badge/Date Helpers | `getSeverityBadge` (5 pages), `getVerdictBadge` (4 pages), `formatEpoch` (5 pages) | Copy-pasted formatting helpers across `frontend/src/app/` | `CONSOLIDATE` (Batch 3) |
| Health & Metrics Routes | `backend/app/api/health.py` + `backend/app/main.py:310-311` | Double-decorated paths + double router mounts -> `/api/api/health` | `CONSOLIDATE` (Batch 3) |

## 2. Architectural Complexity Hotspots (Non-Dead Code Refactoring Opportunities)
- `frontend/src/app/agent-intelligence-studio/page.tsx`: **5,162 lines** (embeds Compact UI + Legacy 7-tab view + 9 advanced settings + drift/simulation/version modals).
- `frontend/src/lib/api.ts`: **4,287 lines** (single monolithic API client + all TypeScript interfaces; 17 unused methods).
- `backend/app/services/empirical_benchmark_harness.py`: **2,442 lines** (harness + adapters + metrics + reporting).
- `backend/app/services/fortisiem_service.py`: **2,435 lines** (SIEM REST + fixture fallback + rule sync + pending processor).
- `backend/app/api/prompts.py`: **1,947 lines** (38 endpoints spanning drafts, quality gates, simulation, governance, drift, actual prompt inspector).
- `backend/app/services/policy_simulation_service.py`: **1,492 lines**.
