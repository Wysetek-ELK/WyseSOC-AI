# 03 — Frontend Dead Code & Redundancy Audit

## 1. Compiler & Linter Baseline
- **`tsc --noEmit`**: **PASS** (0 TypeScript errors).
- **`eslint src`**: **362 errors** (`308` `@typescript-eslint/no-explicit-any`, `34` `react-hooks/set-state-in-effect`, `11` `react/no-unescaped-entities`, `6` `react-hooks/immutability`, `1` `refs`, `1` `purity`, `1` `prefer-const`) and **258 warnings** (`232` `@typescript-eslint/no-unused-vars`, `23` `react-hooks/exhaustive-deps`, `3` `@next/next/no-location-assign-relative-destination`).
- **`npm test`**: **16/16 test suites PASS**.

## 2. Shadowed & Unreachable Legacy Route Pages (13 Files)
`frontend/next.config.ts` defines `redirects()` for 15 legacy URL paths. 13 of those have corresponding `page.tsx` files (3 lines each) that are **never rendered at runtime** because Next.js issues the redirect prior to page rendering, and 0 imports/tests reference them:

| Route | Redirect Destination | Page File | Lines | Classification | Action |
|---|---|---|---:|---|---|
| `/admin` | `/governance-access` | `frontend/src/app/admin/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/analyst-attention` | `/human-review-queue` | `frontend/src/app/analyst-attention/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/dry-run` | `/agent-simulation-lab` | `frontend/src/app/dry-run/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/evaluation-reports` | `/verdict-intelligence` | `frontend/src/app/evaluation-reports/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/imports` | `/telemetry-hub` | `frontend/src/app/imports/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/incidents/[id]` | `/ai-triage-workbench/:id` | `frontend/src/app/incidents/[id]/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/incidents` | `/ai-triage-workbench` | `frontend/src/app/incidents/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/infrastructure` | `/inference-control` | `frontend/src/app/infrastructure/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/learning-history` | `/agent-memory` | `frontend/src/app/learning-history/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/prompt-studio` | `/agent-intelligence-studio` | `frontend/src/app/prompt-studio/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/rules/[id]` | `/detection-intelligence/:id` | `frontend/src/app/rules/[id]/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/rules` | `/detection-intelligence` | `frontend/src/app/rules/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |
| `/settings` | `/agent-configuration` | `frontend/src/app/settings/page.tsx` | 3 | `CONFIRMED_UNUSED` | `REMOVE` |

*(Note: `/agent-mission-control/page.tsx` is a 4-line active route wrapper for `/` referenced in `Sidebar.tsx`, so it is `ACTIVE`.)*

## 3. Orphaned Components & Unused Exports
1. `frontend/src/components/common/PhasePlaceholder.tsx` (L1–105, 105 lines): Phase 1 placeholder screen; 0 importers, 0 test refs. **Classification:** `CONFIRMED_UNUSED` -> `REMOVE`.
2. `frontend/src/components/compact/CompactGovernancePanels.tsx` (L1–361, 361 lines): Exports `ProductionEligibilityChecklist`, `ReviewDecisionPanel`, `ConfirmationDialog`; 0 importers, 0 test refs. **Classification:** `CONFIRMED_UNUSED` -> `REMOVE`.
3. `frontend/src/components/compact/CompactDesignSystem.tsx`: Exports `RuleStatusSummary` (L220–311), `EmptyState` (L807–835), and `ErrorState` (L837–870) with 0 internal/external/test refs -> `CONFIRMED_UNUSED` (`REMOVE`). `DiagnosticIssueCard` (L364) has 1 internal ref only (remove `export`).
4. **Unused Public SVG Assets** (5 files in `frontend/public/`): `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` (0 refs across `frontend/`) -> `CONFIRMED_UNUSED` (`REMOVE`).

## 4. Unused `api.ts` Client Methods (17 / 134)

| Symbol | Location | Classification | Action |
|---|---|---|---|
| `api.pullFortiSiemRule` | `frontend/src/lib/api.ts:1858` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.batchEvaluateAIVerdicts` | `frontend/src/lib/api.ts:1939` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getInvestigationByIncident` | `frontend/src/lib/api.ts:2039` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.generateTemplateDraft` | `frontend/src/lib/api.ts:2150` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.activateApprovedPolicyVersion` | `frontend/src/lib/api.ts:2203` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getIncidentActualPromptExecutions` | `frontend/src/lib/api.ts:2489` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getLearningRecord` | `frontend/src/lib/api.ts:2558` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getDryRunConfig` | `frontend/src/lib/api.ts:2617` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getDryRunJob` | `frontend/src/lib/api.ts:2642` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getIncidentTrust` | `frontend/src/lib/api.ts:2719` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getRuleLearningProfiles` | `frontend/src/lib/api.ts:3062` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.initializeAllRuleLearningProfiles` | `frontend/src/lib/api.ts:3116` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getRuleLearningHistory` | `frontend/src/lib/api.ts:3247` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.getAutomationPolicy` | `frontend/src/lib/api.ts:3269` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.resumeRuleAiExecution` | `frontend/src/lib/api.ts:3330` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.ensureCohort` | `frontend/src/lib/api.ts:4134` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |
| `api.reopenReview` | `frontend/src/lib/api.ts:4250` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |

## 5. Legacy UI Implementations & Duplicated Logic
- **AIS Legacy 7-Tab Toggle (`frontend/src/app/agent-intelligence-studio/page.tsx`, 5,162 lines)**: Maintains both Compact UI (`compactUi=true`, default) and Legacy 7-tab View (`VERDICTUM_COMPACT_UI_ENABLED="false"`). Marked `SUPERSEDED` (`REFACTOR` / `VERIFY_FIRST`) because `frontend/tests/phase3-compact-ui.test.mjs:182` asserts `VERDICTUM_COMPACT_UI_ENABLED`.
- **Duplicated UI Helpers**: `getSeverityBadge` (5 pages), `getVerdictBadge` (4 pages), `formatEpoch` (5 pages), and inline modal backdrops (`fixed inset-0`, 4 pages) -> `DUPLICATE` (`CONSOLIDATE` into `src/lib/formatters.ts` and shared `Modal`).

## 6. ESLint `@typescript-eslint/no-unused-vars` Summary (232 Warnings)

| File | Unused Var/Import Count |
|---|---:|
| `frontend/src/app/agent-configuration/page.tsx` | 7 |
| `frontend/src/app/agent-intelligence-studio/page.tsx` | 12 |
| `frontend/src/app/agent-memory/page.tsx` | 13 |
| `frontend/src/app/agent-simulation-lab/page.tsx` | 9 |
| `frontend/src/app/ai-triage-workbench/[id]/page.tsx` | 5 |
| `frontend/src/app/ai-triage-workbench/page.tsx` | 8 |
| `frontend/src/app/detection-intelligence/[id]/page.tsx` | 5 |
| `frontend/src/app/detection-intelligence/page.tsx` | 3 |
| `frontend/src/app/governance-access/page.tsx` | 4 |
| `frontend/src/app/human-review-queue/page.tsx` | 8 |
| `frontend/src/app/page.tsx` | 6 |
| `frontend/src/app/soc-chatbot/page.tsx` | 4 |
| `frontend/src/app/telemetry-hub/page.tsx` | 3 |
| `frontend/src/app/verdict-intelligence/page.tsx` | 15 |
| `frontend/src/components/common/PhasePlaceholder.tsx` | 3 |
| `frontend/src/components/compact/AccuracyLearningSummary.tsx` | 12 |
| `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` | 14 |
| `frontend/src/components/compact/AiTestWorkbench.tsx` | 8 |
| `frontend/src/components/compact/CompactDesignSystem.tsx` | 11 |
| `frontend/src/components/compact/CompactGovernancePanels.tsx` | 13 |
| `frontend/src/components/compact/IncidentVerdictMatrix.tsx` | 10 |
| `frontend/src/components/compact/ManageVersionHistory.tsx` | 7 |
| `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx` | 21 |
| `frontend/src/components/layout/Shell.tsx` | 1 |
| `frontend/src/components/learning/RuleLearningDashboard.tsx` | 5 |
| `frontend/src/components/pilot/HistoricalEligibilityPanel.tsx` | 2 |
| `frontend/src/components/pilot/PilotControlAndDashboard.tsx` | 1 |
| `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx` | 7 |
| `frontend/src/components/system/ServerInfrastructureMonitor.tsx` | 4 |
| `frontend/src/components/telemetry/HistoricalTelemetryTimeline.tsx` | 5 |
| `frontend/src/components/telemetry/TokenBifurcationWidget.tsx` | 4 |
| `frontend/src/lib/api.ts` | 1 |
| `frontend/src/lib/diagnostics.ts` | 1 |
