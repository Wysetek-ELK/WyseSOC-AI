# 15 — Safe Code Removal Candidates (`CONFIRMED_UNUSED`)

Total `CONFIRMED_UNUSED` candidates: **177** (representing **1,336** non-overlapping lines in application source, **15** source files, and **5** SVG assets).

| Candidate ID | Location | Symbol | Est. Lines | Est. Files | Cleanup Batch |
|---|---|---|---:|---:|---|
| `CCA-0001` | `frontend/src/app/admin/page.tsx:1-3` | `LegacyRoute(/admin)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0002` | `frontend/src/app/analyst-attention/page.tsx:1-3` | `LegacyRoute(/analyst-attention)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0003` | `frontend/src/app/dry-run/page.tsx:1-3` | `LegacyRoute(/dry-run)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0004` | `frontend/src/app/evaluation-reports/page.tsx:1-3` | `LegacyRoute(/evaluation-reports)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0005` | `frontend/src/app/imports/page.tsx:1-3` | `LegacyRoute(/imports)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0006` | `frontend/src/app/incidents/[id]/page.tsx:1-3` | `LegacyRoute(/incidents/[id])` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0007` | `frontend/src/app/incidents/page.tsx:1-3` | `LegacyRoute(/incidents)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0008` | `frontend/src/app/infrastructure/page.tsx:1-3` | `LegacyRoute(/infrastructure)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0009` | `frontend/src/app/learning-history/page.tsx:1-3` | `LegacyRoute(/learning-history)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0010` | `frontend/src/app/prompt-studio/page.tsx:1-3` | `LegacyRoute(/prompt-studio)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0011` | `frontend/src/app/rules/[id]/page.tsx:1-3` | `LegacyRoute(/rules/[id])` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0012` | `frontend/src/app/rules/page.tsx:1-3` | `LegacyRoute(/rules)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0013` | `frontend/src/app/settings/page.tsx:1-3` | `LegacyRoute(/settings)` | 3 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0014` | `frontend/src/components/common/PhasePlaceholder.tsx:1-105` | `PhasePlaceholder` | 105 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0015` | `frontend/src/components/compact/CompactGovernancePanels.tsx:1-361` | `ProductionEligibilityChecklist, ReviewDecisionPanel, ConfirmationDialog` | 361 | 1 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0016` | `frontend/src/components/compact/CompactDesignSystem.tsx:220-311` | `RuleStatusSummaryProps / RuleStatusSummary` | 92 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0017` | `frontend/src/components/compact/CompactDesignSystem.tsx:807-835` | `EmptyState` | 29 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0018` | `frontend/src/components/compact/CompactDesignSystem.tsx:837-870` | `ErrorState` | 34 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0019` | `frontend/public/file.svg:1-1` | `file.svg` | 0 | 1 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0020` | `frontend/public/globe.svg:1-1` | `globe.svg` | 0 | 1 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0021` | `frontend/public/next.svg:1-1` | `next.svg` | 0 | 1 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0022` | `frontend/public/vercel.svg:1-1` | `vercel.svg` | 0 | 1 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0023` | `frontend/public/window.svg:1-1` | `window.svg` | 0 | 1 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0024` | `frontend/src/app/agent-configuration/page.tsx:6-65` | `ExternalLink, FortiSIEMConfigResponse, Globe, LLMConfigResponse, Radio, Shield, llmVerifiedModelLen` | 7 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0025` | `frontend/src/app/agent-intelligence-studio/page.tsx:25-1209` | `Archive, Plus, Trash2, TrendingUp, handleOpenRevoke, loadingDrift, loadingIntelligence, missingBaselineCount ...` | 12 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0026` | `frontend/src/app/agent-memory/page.tsx:4-43` | `ArrowRight, Check, CheckCircle2, ChevronRight, Eye, Filter, Info, Layers ...` | 13 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0027` | `frontend/src/app/agent-simulation-lab/page.tsx:6-133` | `CheckCircle, ExternalLink, Eye, Layers, RotateCcw, ShieldAlert, XCircle, err ...` | 9 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0028` | `frontend/src/app/ai-triage-workbench/[id]/page.tsx:13-30` | `FileSearch, Layers, Network, Server, Tag` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0029` | `frontend/src/app/ai-triage-workbench/page.tsx:9-58` | `ArrowUpDown, Filter, Layers, Shield, combinesMultipleRules, router, setBlindReviewMode, setPageSize` | 8 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0030` | `frontend/src/app/detection-intelligence/[id]/page.tsx:6-14` | `Clock, ExternalLink, FileCode2, Layers, Shield` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0031` | `frontend/src/app/detection-intelligence/page.tsx:9-26` | `Layers, Shield, setPageSize` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0032` | `frontend/src/app/governance-access/page.tsx:9-18` | `AlertCircle, CheckCircle2, Lock, currentUser` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0033` | `frontend/src/app/human-review-queue/page.tsx:8-54` | `Check, Clock, FileText, Filter, Plus, Send, Tag, loadingDetail` | 8 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0034` | `frontend/src/app/page.tsx:8-20` | `Bot, Clock, FileCheck2, FileCode2, Layers, XCircle` | 6 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0035` | `frontend/src/app/soc-chatbot/page.tsx:10-23` | `Activity, Clock, Server, ShieldAlert` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0036` | `frontend/src/app/telemetry-hub/page.tsx:7-55` | `FileArchive, Server, setBatchMaxCount` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0037` | `frontend/src/app/verdict-intelligence/page.tsx:13-130` | `Activity, ArrowRight, Check, ChevronDown, ChevronRight, Download, ExternalLink, Filter ...` | 15 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0038` | `frontend/src/components/compact/AccuracyLearningSummary.tsx:5-159` | `Activity, Award, CheckCircle2, FileCheck2, HelpCircle, Shield, ShieldAlert, TrendingUp ...` | 12 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0039` | `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:9-990` | `Activity, ChevronRight, ExternalLink, HelpCircle, Info, QualityGateResult, RotateCcw, StatusBadge ...` | 14 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0040` | `frontend/src/components/compact/AiTestWorkbench.tsx:7-70` | `AlertCircle, Info, Layers, RotateCcw, Sliders, onNavigateToAdvanced, onViewPrompt, ruleName` | 8 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0041` | `frontend/src/components/compact/CompactDesignSystem.tsx:4-758` | `Clock, Database, ExternalLink, Layers, Link, OperationalSummaryStatus, ShieldAlert, ShieldCheck ...` | 11 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0042` | `frontend/src/components/compact/IncidentVerdictMatrix.tsx:7-43` | `AlertCircle, AlertTriangle, ArrowRight, CheckCircle2, Clock, Cpu, Network, Server ...` | 10 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0043` | `frontend/src/components/compact/ManageVersionHistory.tsx:13-227` | `Clock, FileCode, Info, Shield, activeVersionId, err, ruleName` | 7 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0044` | `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx:7-248` | `AisEvaluationItem, AisEvaluationSummary, AlertTriangle, Clock, Cpu, ExternalLink, Eye, FileCheck2 ...` | 21 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0045` | `frontend/src/components/layout/Shell.tsx:7-7` | `useApp` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0046` | `frontend/src/components/learning/RuleLearningDashboard.tsx:7-50` | `Activity, Cpu, Radio, XCircle, loadingReviews` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0047` | `frontend/src/components/pilot/HistoricalEligibilityPanel.tsx:7-13` | `Download, ShieldCheck` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0048` | `frontend/src/components/pilot/PilotControlAndDashboard.tsx:6-6` | `AlertTriangle` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0049` | `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx:18-65` | `ChevronDown, ExternalLink, Eye, FileCode, Layers, loadingRuleCaptures, ruleName` | 7 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0050` | `frontend/src/components/system/ServerInfrastructureMonitor.tsx:12-32` | `CheckCircle2, ServerHistoryDataPoint, Sliders, compact` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0051` | `frontend/src/components/telemetry/HistoricalTelemetryTimeline.tsx:12-19` | `Cpu, Layers, ShieldCheck, Tag, Zap` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0052` | `frontend/src/components/telemetry/TokenBifurcationWidget.tsx:8-26` | `Activity, ArrowRight, TrendingUp, setSelectedProcess` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0053` | `frontend/src/lib/api.ts:2440-2440` | `_` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0054` | `frontend/src/lib/diagnostics.ts:247-247` | `empiricalAccuracy` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0074` | `backend/app/api/ais_evaluation.py:15-16` | `AsyncSessionLocal, require_analyst` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0075` | `backend/app/api/audit.py:1-4` | `List, or_` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0076` | `backend/app/api/dry_run.py:1-11` | `HistoricalGroundTruth, Optional, desc, require_admin` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0077` | `backend/app/api/evaluations.py:2-12` | `DryRunJob, Optional, PlainTextResponse, Query, require_analyst, status` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0078` | `backend/app/api/fortisiem.py:1-2` | `List, Optional, Query` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0079` | `backend/app/api/health.py:6-16` | `DryRunResult, func, is_postgres` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0080` | `backend/app/api/imports.py:2-2` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0081` | `backend/app/api/incidents.py:2-24` | `COMMON_SOC_BASELINE, LearningRecord, PromptStudioService, Rule, RulePrompt, datetime, desc, get_model_provider ...` | 7 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0082` | `backend/app/api/investigations.py:1-11` | `InvestigationListItem, List, require_admin` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0083` | `backend/app/api/learning.py:7-7` | `require_analyst` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0084` | `backend/app/api/prompts.py:5-74` | `ArchetypeClassificationResult, DetectionSemantics, EvidenceRequirementMapper, PolicyLifecycleMonitor, PolicySimulationService, PromptRollbackRequest, VersionDeleteRequest, assess_policy_runtime_certification ...` | 7 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0085` | `backend/app/api/rule_learning.py:5-13` | `AnalystVerdictReview, RulePromotionRequest, and_, or_` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0086` | `backend/app/api/rules.py:1-18` | `Any, PromptVersion, RuleParser` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0087` | `backend/app/api/system_monitor.py:3-3` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0088` | `backend/app/api/verdict_intelligence.py:16-48` | `CalibrationReport, EmpiricalAccuracyMetrics, EvidenceSufficiencyAssessmentResult, EvidenceSufficiencyEngine, GroundTruthValidationRecord, HistoricalGroundTruth, PlainTextResponse, and_ ...` | 8 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0089` | `backend/app/cli.py:3-10` | `Incident, Rule, sys` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0090` | `backend/app/database.py:11-11` | `NullPool, QueuePool` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0091` | `backend/app/main.py:1-7` | `BASE_DIR, JSONResponse, Request, os` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0092` | `backend/app/models/analyst_feedback.py:4-4` | `Float` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0093` | `backend/app/models/audit.py:5-5` | `Text` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0094` | `backend/app/models/bulk_audit.py:6-6` | `relationship` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0095` | `backend/app/models/import_job.py:5-5` | `ForeignKey` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0096` | `backend/app/models/investigation.py:4-5` | `Any, Dict, Integer` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0097` | `backend/app/models/learning.py:4-4` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0098` | `backend/app/models/maturity.py:4-4` | `Any, Dict` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0099` | `backend/app/models/policy_quality.py:1-5` | `Text, uuid` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0100` | `backend/app/models/production_governance.py:4-4` | `UniqueConstraint` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0101` | `backend/app/models/prompt.py:4-4` | `Any, Dict` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0102` | `backend/app/models/rule.py:4-4` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0103` | `backend/app/models/rule_intelligence.py:5-5` | `Integer, Text` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0104` | `backend/app/models/rule_learning.py:3-4` | `Boolean, List` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0105` | `backend/app/schemas/calibration.py:2-2` | `Any, List` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0106` | `backend/app/schemas/chat.py:1-1` | `Any, Dict` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0107` | `backend/app/schemas/evidence_preflight.py:1-1` | `Any, Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0108` | `backend/app/schemas/investigation.py:2-2` | `Any` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0109` | `backend/app/schemas/llm_config.py:1-1` | `Any` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0110` | `backend/app/schemas/policy_quality.py:2-2` | `Any` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0111` | `backend/app/schemas/production_readiness.py:5-5` | `utc_now` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0112` | `backend/app/schemas/semantic_rag.py:1-1` | `Any, Dict` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0113` | `backend/app/schemas/token_budget.py:1-2` | `Field, List` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0114` | `backend/app/scripts/backup.py:9-15` | `datetime, shutil, sys` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0115` | `backend/app/scripts/migrate_sqlite_to_postgres.py:16-24` | `List, Optional, datetime, sys` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0116` | `backend/app/scripts/restore.py:9-9` | `sys` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0117` | `backend/app/scripts/run_empirical_benchmark.py:13-13` | `datetime, timezone` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0118` | `backend/app/services/actual_prompt_capture_service.py:6-19` | `CompilationExecutionMode, Incident, datetime` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0119` | `backend/app/services/ai_verdict_service.py:3-24` | `COMMON_SOC_BASELINE, LearningRecord, build_model_facing_payload, classify_execution_provenance, datetime, desc, or_` | 6 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0120` | `backend/app/services/ais_evaluation_service.py:17-37` | `HistoricalGroundTruthValidator, Tuple, and_, datetime, exists, not_, uuid` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0121` | `backend/app/services/analyst_review_service.py:11-11` | `utc_now` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0122` | `backend/app/services/audit_service.py:6-6` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0123` | `backend/app/services/automation_governor.py:4-4` | `desc` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0124` | `backend/app/services/blind_review_guard.py:18-18` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0125` | `backend/app/services/bulk_quality_audit_service.py:3-14` | `Any, Dict, GateStatus, List, PolicyQualityAssessmentRecord, PromptVersion, datetime` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0126` | `backend/app/services/calibration_evaluation_service.py:1-8` | `HistoricalGroundTruth, Tuple, math` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0127` | `backend/app/services/calibration_evaluator.py:12-14` | `Optional, math` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0128` | `backend/app/services/confidence_normalizer.py:8-8` | `Dict` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0129` | `backend/app/services/dashboard_service.py:1-1` | `Any, Dict, List` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0130` | `backend/app/services/detection_archetype_registry.py:2-2` | `Any, Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0131` | `backend/app/services/distributed_lock.py:13-20` | `Connection, datetime` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0132` | `backend/app/services/dry_run_service.py:1-13` | `HistoricalGroundTruth, Rule, Tuple, asyncio, datetime, func` | 6 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0133` | `backend/app/services/empirical_accuracy_evaluator.py:14-14` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0134` | `backend/app/services/empirical_benchmark_harness.py:32-58` | `Callable, CanonicalEvidenceRecord, ClaimGroundingResult, EmpiricalAccuracyEvaluator, GroundTruthLabel, PreflightValidationResult, VerdictGuardrailsEngine, VerdictValidationResult ...` | 9 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0135` | `backend/app/services/evaluation_service.py:3-14` | `HistoricalGroundTruth, Optional, RulePerformanceSummary, Tuple, datetime, desc` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0136` | `backend/app/services/evidence_compaction_service.py:12-13` | `hashlib, json` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0137` | `backend/app/services/evidence_contract_service.py:2-9` | `ArchetypeId, Dict, List` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0138` | `backend/app/services/evidence_normalization_service.py:3-3` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0139` | `backend/app/services/evidence_preflight_validator.py:2-4` | `Any, CanonicalEvidenceRecord, Optional` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0140` | `backend/app/services/evidence_requirement_mapper.py:2-12` | `Any, DetectionArchetypeRegistry, Dict` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0141` | `backend/app/services/evidence_sufficiency_engine.py:20-24` | `EvidenceFieldAudit, Tuple, datetime` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0142` | `backend/app/services/fortisiem_service.py:10-10` | `datetime` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0143` | `backend/app/services/gpu_manager.py:5-5` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0144` | `backend/app/services/ground_truth_certification_service.py:21-35` | `HistoricalGroundTruth, IncidentEvent, RulePrompt, and_` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0145` | `backend/app/services/historical_eligibility_service.py:3-4` | `datetime, json` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0146` | `backend/app/services/historical_ground_truth_validator.py:22-23` | `GroundTruthItem, GroundTruthProvenance, List` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0147` | `backend/app/services/incident_service.py:17-17` | `ModelFacingEvent, ModelFacingIncidentPayload` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0148` | `backend/app/services/independent_verdict_validator.py:6-6` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0149` | `backend/app/services/investigation_service.py:2-24` | `InvestigationDetailResponse, InvestigationEvidenceResponse, InvestigationQuestionResponse, User, datetime, strip_ai_notes_from_handover` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0150` | `backend/app/services/learning_service.py:1-9` | `Any, Dict, HistoricalGroundTruth, IncidentEvent, datetime` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0151` | `backend/app/services/maturity_service.py:1-21` | `Any, DryRunJob, HistoricalGroundTruth, HistoricalGroundTruthValidator, datetime` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0152` | `backend/app/services/migration_service.py:2-2` | `sys` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0153` | `backend/app/services/model_claim_extractor.py:3-3` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0154` | `backend/app/services/model_payload_allowlist.py:2-2` | `ModelFacingEvent, ModelFacingIncidentPayload` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0155` | `backend/app/services/model_provider/disabled.py:1-1` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0156` | `backend/app/services/model_provider/simulated.py:2-2` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0157` | `backend/app/services/pilot_service.py:1-21` | `Investigation, PromptVersion, asyncio, datetime, or_, time` | 6 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0158` | `backend/app/services/policy_compiler_service.py:3-3` | `datetime` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0159` | `backend/app/services/policy_eligibility_service.py:12-22` | `List, datetime, re, utc_now` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0160` | `backend/app/services/policy_generation_service.py:2-7` | `SourceProvenance, Tuple, datetime` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0161` | `backend/app/services/policy_lifecycle_monitor.py:2-11` | `DetectionSemantics, RuleIntelligenceAnalyzer, Tuple, and_, datetime` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0162` | `backend/app/services/policy_quality_validator.py:3-27` | `CANONICAL_FIELD_CATALOG, datetime, json` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0163` | `backend/app/services/policy_simulation_service.py:12-62` | `EmpiricalAccuracyMetrics, EvidenceContractService, EvidenceSufficiencyAssessmentRecord, EvidenceSufficiencyEngine, Rule, RulePrompt, VerdictClaimValidator, VerdictGuardrailsEngine ...` | 13 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0164` | `backend/app/services/policy_version_governance_service.py:2-3` | `Optional, Tuple, and_, or_` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0165` | `backend/app/services/production_readiness_service.py:4-23` | `RuleLearningProfile, SimulationStatus, SourceProvenance, and_, or_, utc_now` | 5 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0166` | `backend/app/services/promotion_service.py:2-2` | `Tuple` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0167` | `backend/app/services/prompt_studio_service.py:4-16` | `PromptVersionResponse, RulePromptResponse, User, datetime, or_` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0168` | `backend/app/services/reasoning_integrity_engine.py:13-13` | `CanonicalEvidenceRecord` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0169` | `backend/app/services/system_monitor_service.py:9-528` | `app, delete` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0170` | `backend/app/services/telemetry_timeline_service.py:8-11` | `HistoricalGroundTruth, IncidentEvent, Investigation` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0171` | `backend/app/services/token_analytics_service.py:1-2` | `List, datetime` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0172` | `backend/app/services/tokenizer_service.py:15-15` | `Tuple, Union` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0173` | `backend/app/services/verdict_guardrails_engine.py:17-18` | `ClaimType, Tuple` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0174` | `backend/app/services/verdict_pipeline.py:23-23` | `select` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0175` | `backend/app/services/verdict_trustworthiness_engine.py:24-28` | `ClaimVerificationResult, EvidenceSufficiencyAssessmentResult, List, datetime` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0176` | `backend/app/services/verified_semantic_retrieval_service.py:2-2` | `datetime` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0177` | `backend/app/services/wilson_evaluator.py:2-2` | `Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0178` | `backend/app/utils/zip_guard.py:1-1` | `io` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0179` | `backend/app/workers/celery_app.py:2-2` | `Any, Dict, Optional` | 1 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0180` | `backend/app/workers/tasks.py:4-13` | `Investigation, datetime, time, update` | 4 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0181` | `backend/app/services/ais_evaluation_service.py:1096-1117` | `AisEvaluationService.get_missing_inference_candidates` | 22 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0184` | `backend/app/services/detection_archetype_registry.py:649-651` | `DetectionArchetypeRegistry.list_archetypes` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0189` | `backend/app/services/fortisiem_service.py:596-665` | `FortiSIEMService.pull_incidents_for_rule` | 70 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0190` | `backend/app/services/gpu_manager.py:140-142` | `GPUWorkloadManager.check_backpressure` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0193` | `backend/app/services/policy_governance.py:87-104` | `PolicyRuntimeCertification.to_dict` | 18 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0195` | `backend/app/services/rule_intelligence_analyzer.py:408-409` | `RuleIntelligenceAnalyzer._extract_window_from_conditions` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0198` | `backend/app/services/token_budget_service.py:88-111` | `TokenBudgetService.get_token_accounting` | 24 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0201` | `backend/app/schemas/canonical_evidence.py:7-19` | `EvidenceLifecycleStage` | 13 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0202` | `backend/app/schemas/dashboard.py:18-20` | `StatusCount` | 3 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0203` | `backend/app/services/blind_review_guard.py:519-520` | `get_blind_mask_response_marker` | 2 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0204` | `backend/app/schemas/auth.py:1-1` | `TokenPayload` | 10 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0205` | `backend/app/schemas/learning.py:1-1` | `LearningRecordCreate` | 10 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0206` | `backend/app/schemas/prompt.py:1-1` | `PromptDraftGenerateRequest` | 10 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0207` | `backend/app/schemas/rule.py:1-1` | `RuleCreate` | 10 | 0 | `Batch 1 — Low-risk source cleanup` |
| `CCA-0224` | `backend/app/config.py:40-40` | `Settings.APP_NAME` | 1 | 0 | `Batch 2 — Orphaned implementation cleanup` |
| `CCA-0225` | `backend/app/config.py:136-136` | `Settings.PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED` | 1 | 0 | `Batch 2 — Orphaned implementation cleanup` |
