# 17 — Proposed Safe Cleanup Implementation Plan (CCA 1.1+)

> **IMPORTANT:** This is a planning roadmap only. **Zero batches are authorized or executed during CCA 1.0.**

## Batch Roadmap
### Batch 1 — Low-risk source cleanup
- **Candidates (191):** `CCA-0016, CCA-0017, CCA-0018, CCA-0019, CCA-0020, CCA-0021, CCA-0022, CCA-0023, CCA-0024, CCA-0025, CCA-0026, CCA-0027, CCA-0028, CCA-0029, CCA-0030 ... (+176 more)`
- **Estimated Scope:** 3,891 lines / 36 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).
### Batch 2 — Orphaned implementation cleanup
- **Candidates (34):** `CCA-0001, CCA-0002, CCA-0003, CCA-0004, CCA-0005, CCA-0006, CCA-0007, CCA-0008, CCA-0009, CCA-0010, CCA-0011, CCA-0012, CCA-0013, CCA-0014, CCA-0015 ... (+19 more)`
- **Estimated Scope:** 627 lines / 15 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).
### Batch 3 — Duplicate code consolidation
- **Candidates (3):** `CCA-0073, CCA-0219, CCA-0222`
- **Estimated Scope:** 172 lines / 1 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).
### Batch 4 — Legacy architecture cleanup
- **Candidates (31):** `CCA-0072, CCA-0182, CCA-0183, CCA-0185, CCA-0186, CCA-0187, CCA-0188, CCA-0191, CCA-0192, CCA-0194, CCA-0196, CCA-0197, CCA-0199, CCA-0200, CCA-0208 ... (+16 more)`
- **Estimated Scope:** 3,701 lines / 15 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).
### Batch 5 — Dependency optimization
- **Candidates (1):** `CCA-0261`
- **Estimated Scope:** 1 lines / 0 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).
### Batch 6 — Restricted database and infrastructure cleanup
- **Candidates (3):** `CCA-0226, CCA-0227, CCA-0228`
- **Estimated Scope:** 34 lines / 1 files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).

## Cleanup Approval Matrix (All Approvals = `PENDING`)
*(Full machine-readable matrix in `CLEANUP_APPROVAL_MATRIX.json` and `CLEANUP_CANDIDATES.csv`.)*

| Candidate ID | File / Module | Reason | Risk | Est. Reduction | Recommendation | Approval |
|---|---|---|---|---|---|---|
| `CCA-0001` | `frontend/src/app/admin/page.tsx (LegacyRoute(/admin))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0002` | `frontend/src/app/analyst-attention/page.tsx (LegacyRoute(/analyst-attention))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0003` | `frontend/src/app/dry-run/page.tsx (LegacyRoute(/dry-run))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0004` | `frontend/src/app/evaluation-reports/page.tsx (LegacyRoute(/evaluation-reports))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0005` | `frontend/src/app/imports/page.tsx (LegacyRoute(/imports))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0006` | `frontend/src/app/incidents/[id]/page.tsx (LegacyRoute(/incidents/[id]))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0007` | `frontend/src/app/incidents/page.tsx (LegacyRoute(/incidents))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0008` | `frontend/src/app/infrastructure/page.tsx (LegacyRoute(/infrastructure))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0009` | `frontend/src/app/learning-history/page.tsx (LegacyRoute(/learning-history))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0010` | `frontend/src/app/prompt-studio/page.tsx (LegacyRoute(/prompt-studio))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0011` | `frontend/src/app/rules/[id]/page.tsx (LegacyRoute(/rules/[id]))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0012` | `frontend/src/app/rules/page.tsx (LegacyRoute(/rules))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0013` | `frontend/src/app/settings/page.tsx (LegacyRoute(/settings))` | Next.js redirects() intercepts route before App Router renders page.tsx; 0 impor | `LOW` | 3 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0014` | `frontend/src/components/common/PhasePlaceholder.tsx (PhasePlaceholder)` | Zero imports in frontend/src and zero references in frontend/tests or scripts. | `LOW` | 105 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0015` | `frontend/src/components/compact/CompactGovernancePanels.tsx (ProductionEligibilityChecklist, ReviewDecisionPanel, ConfirmationDialog)` | Zero imports in frontend/src and zero references in frontend/tests. | `LOW` | 361 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0016` | `frontend/src/components/compact/CompactDesignSystem.tsx (RuleStatusSummaryProps / RuleStatusSummary)` | Zero references inside CompactDesignSystem.tsx, zero imports across frontend/src | `LOW` | 92 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0017` | `frontend/src/components/compact/CompactDesignSystem.tsx (EmptyState)` | Zero references inside CompactDesignSystem.tsx, zero imports across frontend/src | `LOW` | 29 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0018` | `frontend/src/components/compact/CompactDesignSystem.tsx (ErrorState)` | Zero references inside CompactDesignSystem.tsx, zero imports across frontend/src | `LOW` | 34 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0019` | `frontend/public/file.svg (file.svg)` | No references in frontend/src, CSS, metadata, or tests. | `LOW` | 0 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0020` | `frontend/public/globe.svg (globe.svg)` | No references in frontend/src, CSS, metadata, or tests. | `LOW` | 0 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0021` | `frontend/public/next.svg (next.svg)` | No references in frontend/src, CSS, metadata, or tests. | `LOW` | 0 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0022` | `frontend/public/vercel.svg (vercel.svg)` | No references in frontend/src, CSS, metadata, or tests. | `LOW` | 0 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0023` | `frontend/public/window.svg (window.svg)` | No references in frontend/src, CSS, metadata, or tests. | `LOW` | 0 lines / 1 files | `REMOVE` | **PENDING** |
| `CCA-0024` | `frontend/src/app/agent-configuration/page.tsx (ExternalLink, FortiSIEMConfigResponse, Globe, LLMConfigResponse, Radio, Shield, llmVerifiedModelLen)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 7 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0025` | `frontend/src/app/agent-intelligence-studio/page.tsx (Archive, Plus, Trash2, TrendingUp, handleOpenRevoke, loadingDrift, loadingIntelligence, missingBaselineCount ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 12 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0026` | `frontend/src/app/agent-memory/page.tsx (ArrowRight, Check, CheckCircle2, ChevronRight, Eye, Filter, Info, Layers ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 13 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0027` | `frontend/src/app/agent-simulation-lab/page.tsx (CheckCircle, ExternalLink, Eye, Layers, RotateCcw, ShieldAlert, XCircle, err ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 9 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0028` | `frontend/src/app/ai-triage-workbench/[id]/page.tsx (FileSearch, Layers, Network, Server, Tag)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 5 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0029` | `frontend/src/app/ai-triage-workbench/page.tsx (ArrowUpDown, Filter, Layers, Shield, combinesMultipleRules, router, setBlindReviewMode, setPageSize)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 8 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0030` | `frontend/src/app/detection-intelligence/[id]/page.tsx (Clock, ExternalLink, FileCode2, Layers, Shield)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 5 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0031` | `frontend/src/app/detection-intelligence/page.tsx (Layers, Shield, setPageSize)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 3 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0032` | `frontend/src/app/governance-access/page.tsx (AlertCircle, CheckCircle2, Lock, currentUser)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 4 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0033` | `frontend/src/app/human-review-queue/page.tsx (Check, Clock, FileText, Filter, Plus, Send, Tag, loadingDetail)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 8 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0034` | `frontend/src/app/page.tsx (Bot, Clock, FileCheck2, FileCode2, Layers, XCircle)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 6 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0035` | `frontend/src/app/soc-chatbot/page.tsx (Activity, Clock, Server, ShieldAlert)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 4 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0036` | `frontend/src/app/telemetry-hub/page.tsx (FileArchive, Server, setBatchMaxCount)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 3 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0037` | `frontend/src/app/verdict-intelligence/page.tsx (Activity, ArrowRight, Check, ChevronDown, ChevronRight, Download, ExternalLink, Filter ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 15 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0038` | `frontend/src/components/compact/AccuracyLearningSummary.tsx (Activity, Award, CheckCircle2, FileCheck2, HelpCircle, Shield, ShieldAlert, TrendingUp ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 12 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0039` | `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx (Activity, ChevronRight, ExternalLink, HelpCircle, Info, QualityGateResult, RotateCcw, StatusBadge ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 14 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0040` | `frontend/src/components/compact/AiTestWorkbench.tsx (AlertCircle, Info, Layers, RotateCcw, Sliders, onNavigateToAdvanced, onViewPrompt, ruleName)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 8 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0041` | `frontend/src/components/compact/CompactDesignSystem.tsx (Clock, Database, ExternalLink, Layers, Link, OperationalSummaryStatus, ShieldAlert, ShieldCheck ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 11 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0042` | `frontend/src/components/compact/IncidentVerdictMatrix.tsx (AlertCircle, AlertTriangle, ArrowRight, CheckCircle2, Clock, Cpu, Network, Server ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 10 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0043` | `frontend/src/components/compact/ManageVersionHistory.tsx (Clock, FileCode, Info, Shield, activeVersionId, err, ruleName)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 7 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0044` | `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx (AisEvaluationItem, AisEvaluationSummary, AlertTriangle, Clock, Cpu, ExternalLink, Eye, FileCheck2 ...)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 21 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0045` | `frontend/src/components/layout/Shell.tsx (useApp)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 1 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0046` | `frontend/src/components/learning/RuleLearningDashboard.tsx (Activity, Cpu, Radio, XCircle, loadingReviews)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 5 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0047` | `frontend/src/components/pilot/HistoricalEligibilityPanel.tsx (Download, ShieldCheck)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 2 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0048` | `frontend/src/components/pilot/PilotControlAndDashboard.tsx (AlertTriangle)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 1 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0049` | `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx (ChevronDown, ExternalLink, Eye, FileCode, Layers, loadingRuleCaptures, ruleName)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 7 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0050` | `frontend/src/components/system/ServerInfrastructureMonitor.tsx (CheckCircle2, ServerHistoryDataPoint, Sliders, compact)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 4 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0051` | `frontend/src/components/telemetry/HistoricalTelemetryTimeline.tsx (Cpu, Layers, ShieldCheck, Tag, Zap)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 5 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0052` | `frontend/src/components/telemetry/TokenBifurcationWidget.tsx (Activity, ArrowRight, TrendingUp, setSelectedProcess)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 4 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0053` | `frontend/src/lib/api.ts (_)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 1 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0054` | `frontend/src/lib/diagnostics.ts (empiricalAccuracy)` | ESLint static AST dataflow confirms symbols/imports are declared but never read. | `LOW` | 1 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0055` | `frontend/src/lib/api.ts (api.pullFortiSiemRule)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 10 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0056` | `frontend/src/lib/api.ts (api.batchEvaluateAIVerdicts)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 10 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0057` | `frontend/src/lib/api.ts (api.getInvestigationByIncident)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 5 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0058` | `frontend/src/lib/api.ts (api.generateTemplateDraft)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 7 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0059` | `frontend/src/lib/api.ts (api.activateApprovedPolicyVersion)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0060` | `frontend/src/lib/api.ts (api.getIncidentActualPromptExecutions)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 6 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0061` | `frontend/src/lib/api.ts (api.getLearningRecord)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 5 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0062` | `frontend/src/lib/api.ts (api.getDryRunConfig)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 5 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0063` | `frontend/src/lib/api.ts (api.getDryRunJob)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 5 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0064` | `frontend/src/lib/api.ts (api.getIncidentTrust)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 5 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0065` | `frontend/src/lib/api.ts (api.getRuleLearningProfiles)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0066` | `frontend/src/lib/api.ts (api.initializeAllRuleLearningProfiles)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0067` | `frontend/src/lib/api.ts (api.getRuleLearningHistory)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 7 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0068` | `frontend/src/lib/api.ts (api.getAutomationPolicy)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0069` | `frontend/src/lib/api.ts (api.resumeRuleAiExecution)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0070` | `frontend/src/lib/api.ts (api.ensureCohort)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 7 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0071` | `frontend/src/lib/api.ts (api.reopenReview)` | No UI component or test calls this method; backend endpoint may still exist for  | `LOW` | 8 lines / 0 files | `VERIFY_FIRST` | **PENDING** |
| `CCA-0072` | `frontend/src/app/agent-intelligence-studio/page.tsx (compactUi === false (Legacy 7-Tab View))` | Compact UI is default; Legacy View duplicates Overview, Learning, and Editor wor | `HIGH` | 1800 lines / 0 files | `REFACTOR` | **PENDING** |
| `CCA-0073` | `frontend/src/app/page.tsx (+4 pages) (getSeverityBadge, getVerdictBadge, formatEpoch)` | Consolidating into frontend/src/lib/formatters.ts eliminates drift. | `LOW` | 120 lines / 0 files | `CONSOLIDATE` | **PENDING** |
| `CCA-0074` | `backend/app/api/ais_evaluation.py (AsyncSessionLocal, require_analyst)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 2 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0075` | `backend/app/api/audit.py (List, or_)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 2 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0076` | `backend/app/api/dry_run.py (HistoricalGroundTruth, Optional, desc, require_admin)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 4 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0077` | `backend/app/api/evaluations.py (DryRunJob, Optional, PlainTextResponse, Query, require_analyst, status)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 5 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0078` | `backend/app/api/fortisiem.py (List, Optional, Query)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 2 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0079` | `backend/app/api/health.py (DryRunResult, func, is_postgres)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 3 lines / 0 files | `REMOVE` | **PENDING** |
| `CCA-0080` | `backend/app/api/imports.py (Optional)` | AST Name/Constant usage scan found 0 references to imported symbol(s) in module. | `LOW` | 1 lines / 0 files | `REMOVE` | **PENDING** |

*(Showing first 80 of 263 rows; see `CLEANUP_APPROVAL_MATRIX.json` for complete table.)*
