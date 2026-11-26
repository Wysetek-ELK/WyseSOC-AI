"""Generate all 20 CCA 1.0 Markdown audit reports directly from verified JSON evidence."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "CCA_1_0"
EVIDENCE_DIR = OUT_DIR / "evidence"


def load_all():
    return {
        "inv": json.loads((OUT_DIR / "CODEBASE_INVENTORY.json").read_text(encoding="utf-8")),
        "dep": json.loads((OUT_DIR / "DEPENDENCY_GRAPH.json").read_text(encoding="utf-8")),
        "api": json.loads((OUT_DIR / "API_USAGE_MATRIX.json").read_text(encoding="utf-8")),
        "dead": json.loads((OUT_DIR / "DEAD_CODE_REGISTRY.json").read_text(encoding="utf-8")),
        "prot": json.loads((OUT_DIR / "PROTECTED_COMPONENTS.json").read_text(encoding="utf-8")),
        "app_matrix": json.loads((OUT_DIR / "CLEANUP_APPROVAL_MATRIX.json").read_text(encoding="utf-8")),
        "cmds": json.loads((OUT_DIR / "AUDIT_COMMANDS_AND_RESULTS.json").read_text(encoding="utf-8")),
        "final": json.loads((OUT_DIR / "FINAL_EVIDENCE.json").read_text(encoding="utf-8")),
        "fe": json.loads((EVIDENCE_DIR / "frontend_analysis.json").read_text(encoding="utf-8")),
        "be": json.loads((EVIDENCE_DIR / "backend_analysis.json").read_text(encoding="utf-8")),
        "deep": json.loads((EVIDENCE_DIR / "deep_audit.json").read_text(encoding="utf-8")),
        "ais_deps": json.loads((EVIDENCE_DIR / "ais_api_deps_audit.json").read_text(encoding="utf-8")),
        "eslint": json.loads((EVIDENCE_DIR / "eslint_report.json").read_text(encoding="utf-8")),
    }


def write_md(name: str, content: str):
    (OUT_DIR / name).write_text(content.strip() + "\n", encoding="utf-8")


def gen_00_executive_summary(d: Dict[str, Any]):
    m = d["final"]["metrics"]
    inv = d["inv"]["summary"]
    gates = d["final"]["acceptance_gates"]
    pass_cnt = sum(1 for g in gates if g["status"] == "PASS")
    part_cnt = sum(1 for g in gates if g["status"] == "PARTIAL")

    md = f"""# Verdictum AI — CCA 1.0 Executive Summary

**Audit Phase:** CCA 1.0 (Complete Codebase Audit, Dead Code Detection, Redundancy Analysis & Safe Cleanup Planning)
**Repository Branch:** `{inv['git_branch']}`
**Baseline Commit:** `{inv['git_commit']}`
**Safety Posture:** Read-Only Audit (`0` application files modified, `0` deletions, `0` production changes)

---

## 1. Executive Metrics Summary

| Metric | Actual Result | Notes / Methodology |
|---|---|---|
| Total application source files | {m['total_application_source_files']} | `frontend/src/` (82 code files) + `backend/app/` (190 Python files), excluding tests, Alembic migrations, docs, scratch, and assets |
| Total application lines of code | {m['total_application_lines_of_code']:,} | Raw lines ({m['total_application_code_lines_excluding_blanks_comments']:,} non-blank, non-comment code lines) |
| Frontend source files | {m['frontend_source_files']} | `frontend/src/` TS/TSX/CSS ({inv['frontend_source_lines_total']:,} lines) |
| Backend source files | {m['backend_source_files']} | `backend/app/` Python ({inv['backend_source_lines_total']:,} lines) |
| Confirmed unused files | {m['confirmed_unused_files']} | 13 redirected legacy `page.tsx` wrappers + 2 orphaned components (`PhasePlaceholder.tsx`, `CompactGovernancePanels.tsx`); plus {m['confirmed_unused_public_assets']} unused default SVGs in `frontend/public/` |
| Possibly unused files | {m['possibly_unused_files']} | 1 deployment script/unit mismatch + 11 compatibility shims (`REQUIRED_COMPATIBILITY`) + `calibration_evaluation_service.py` (`DUPLICATE`) |
| Confirmed unused functions / methods / exports | {m['confirmed_unused_functions_and_methods']} | 7 backend service methods (0 prod/test/script refs) + 3 top-level backend symbols + 3 unused exported UI primitives in `CompactDesignSystem.tsx` |
| Unused frontend components | {m['unused_frontend_components']} | `PhasePlaceholder`, `CompactGovernancePanels` (3 components), plus `RuleStatusSummary`, `EmptyState`, `ErrorState` in `CompactDesignSystem.tsx` |
| Potentially unused API endpoints | {m['potentially_unused_api_endpoints']} | Out of {len(d['api']['endpoints'])} endpoint handlers (20 lack frontend refs; 8 are dev/health/metrics/AIS 2.7 admin) |
| Duplicate implementations | {m['duplicate_implementations']} | Frontend page badge/epoch helpers, `WilsonScoreEvaluator`, `CalibrationEvaluationService`, `DryRunService`/`EvaluationService`, `/api/health` + `/api/metrics` dual mounts |
| Legacy AIS implementations | {m['legacy_ais_implementations']} | AIS 7-tab Legacy View toggle (`VERDICTUM_COMPACT_UI_ENABLED`), `CalibrationEvaluationService`, `DryRunService` adapter, 11 nomenclature alias shims |
| Potentially unused dependencies | {m['potentially_unused_dependencies']} | `@tailwindcss/turbopack` (requires `next build` verification) |
| Confirmed removable lines (app source) | {m['confirmed_removable_lines_app_source']:,} | Non-overlapping lines across `CONFIRMED_UNUSED` app source findings (plus 3,062 lines in tracked `scratch/` = {m['confirmed_removable_lines_including_tracked_scratch']:,} total) |
| Conditional removable lines | {m['conditional_removable_lines']:,} | Requires consolidation/refactor/test updates (e.g., Legacy 7-tab AIS View ~1,800L, `DryRunService`+`EvaluationService` 951L, `api.ts` unused methods, shims) |
| Estimated safe code reduction percentage | {m['estimated_safe_code_reduction_percentage']}% | `{m['confirmed_removable_lines_app_source']} / {m['total_application_lines_of_code']}` (app source only, non-overlapping) |
| Low-risk cleanup candidates | {m['low_risk_cleanup_candidates']} | Imports, unused vars, dead helpers, shadowed 3-line pages, SVGs, tracked scratch |
| Medium-risk cleanup candidates | {m['medium_risk_cleanup_candidates']} | Unwired `api.ts` client methods (wait: grouped/individual), dual `/api/v1` mounts, `CalibrationEvaluationService`, DB column review |
| High-risk cleanup candidates | {m['high_risk_cleanup_candidates']} | AIS Legacy View refactor, `DryRunService`+`EvaluationService` adapter, `ai-verdict-scheduler.service` / Celery Beat mismatch |
| Critical-risk cleanup candidates | {m['critical_risk_cleanup_candidates']} | 2 DB schema columns (`TokenUsageRecord.estimated_cost_usd`, `GroundTruthValidationRecord.is_eligible_for_evaluation`) |
| Candidates requiring manual verification | {m['candidates_requiring_manual_verification']} | Items requiring verification notes, product sign-off, or runtime log checks before removal |
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

- **PASS:** {pass_cnt} / {len(gates)} gates (`G1`, `G2`, `G3`, `G5`, `G7`, `G8`, `G10`, `G11`, `G12`, `G13`)
- **PARTIAL:** {part_cnt} / {len(gates)} gates (`G4` live Server 1 access logs unavailable locally; `G6` live Server 1 PostgreSQL metadata unavailable locally; `G9` remote Server 1/2 parity unverified without SSH)
- **FAIL:** 0 / {len(gates)} gates

See [19_FINAL_AUDIT_ACCEPTANCE.md](./19_FINAL_AUDIT_ACCEPTANCE.md) and [17_PROPOSED_CLEANUP_IMPLEMENTATION_PLAN.md](./17_PROPOSED_CLEANUP_IMPLEMENTATION_PLAN.md) for next steps. **Wait for explicit approval before commencing CCA 1.1.**
"""
    write_md("00_EXECUTIVE_SUMMARY.md", md)


def gen_01_baseline_and_arch(d: Dict[str, Any]):
    inv = d["inv"]["summary"]
    md = f"""# 01 — Repository & Architecture Baseline

## 1. Repository & Git Baseline

| Attribute | Verified Value |
|---|---|
| Git Branch | `{inv['git_branch']}` |
| Commit SHA | `{inv['git_commit']}` |
| Tracked Repository Files | {inv['tracked_files_total']:,} |
| Untracked Files at Baseline | {inv['untracked_files_count']} (`docs/AIS_2_7/` untracked reports/evidence; plus gitignored `scratch/` local files) |
| Modified Tracked Files | {inv['modified_files_count']} |
| Frontend Source Files | {inv['frontend_source_files']} ({inv['frontend_source_lines_total']:,} raw lines / {inv['frontend_source_lines_code']:,} code lines) |
| Backend Source Files | {inv['backend_source_files']} ({inv['backend_source_lines_total']:,} raw lines / {inv['backend_source_lines_code']:,} code lines) |
| Alembic Migrations | {inv['migration_files']} (`001` through `016`) |
| Test Files | {inv['test_files']} (106 backend Python + 16 frontend `.mjs`) |
| Deployment Files | {inv['deployment_files']} (`deployment/`) |
| Scripts & Tracked Scratch | {inv['scripts_and_scratch_files']} (39 `scripts/`, 7 `backend/**/scripts/`, 31 tracked `scratch/`) |

### Counting Methodology
- **Application Source Code**: Tracked files under `frontend/src/` (excluding binary icon/image assets) and `backend/app/` (including `backend/app/scripts/`), excluding `backend/tests/`, `frontend/tests/`, `backend/alembic/`, `docs/`, `scratch/`, root `scripts/`, `deployment/`, `node_modules/`, `backend/venv/`, and `frontend/.next/`.
- **Code Lines**: Non-empty lines excluding single-line comments (`#` for Python/shell, `//` for TypeScript/CSS).

## 2. Discovered Technology Stack

- **Frontend**: Next.js `16.4.5` (App Router, `next.config.ts` rewrites `/api/:path*` -> `http://127.0.0.1:8000/api/:path*`), React `19.3.0`, TypeScript `5`, Tailwind CSS v4 (`@tailwindcss/postcss`), Lucide icons (`lucide-react`). Built with Node `v26.13.1`, tested with `node --experimental-strip-types --test`.
- **Backend**: FastAPI (`>=0.110.0`), Uvicorn (4 workers in systemd), Pydantic v2 + `pydantic-settings`, SQLAlchemy `2.0+` async (`asyncpg` for PostgreSQL in production, `aiosqlite` for dev/tests), Alembic (`001`–`016`).
- **Workers & Scheduling**: Celery (`celery_app.py` with Redis broker/backend; queues `live_triage`, `simulation_replay`, `maintenance`) + in-process asyncio `SentinelIngestWorker` (`fortisiem_scheduler.py`) with file-backed multi-worker leader election (`scheduler_state.json`).
- **LLM Inference (Server 2)**: OpenAI-compatible vLLM endpoint (`Qwen/Qwen2.5-7B-Instruct-AWQ` default) via `OpenAICompatibleProvider` protected by `GPUWorkloadManager` semaphore & circuit breaker (`gpu_manager.py`).
- **Deployment & Reverse Proxy**: Native Ubuntu systemd services (`ai-verdict-backend`, `ai-verdict-worker`, `ai-verdict-scheduler`, `ai-verdict-frontend`) behind Nginx (`deployment/nginx/ai-verdict.conf`) with TLS and 300s proxy timeouts.

---

## 3. Architecture & Workflow Diagrams (Actual Discovered Code)

### 3.1 Current Application Architecture
```mermaid
flowchart LR
    Browser["SOC Analyst Browser"] -->|HTTPS :443| Nginx["Nginx Reverse Proxy"]
    Nginx -->|"/ (300s timeout)"| NextJS["Next.js 16 Frontend (:3000)"]
    Nginx -->|"/api/*, /health, /metrics"| FastAPI["FastAPI Backend (:8000, 4 Uvicorn workers)"]
    NextJS -->|"/api/* rewrite (dev)"| FastAPI
    FastAPI --> PG[("PostgreSQL / SQLite")]
    FastAPI --> Redis[("Redis Broker")]
    FastAPI -->|"In-process Asyncio Leader"| Poller["SentinelIngestWorker (fortisiem_scheduler.py)"]
    Poller -->|"REST Pull"| FortiSIEM["FortiSIEM Supervisor"]
    FastAPI -->|"USE_ASYNC_CELERY=true"| CeleryW["Celery Worker (live_triage, simulation_replay)"]
    Redis --> CeleryW
    CeleryW --> PG
    FastAPI -->|"OpenAI-Compatible HTTP"| Server2["Verdictum Cortex / vLLM GPU (:8000/v1)"]
    CeleryW -->|"OpenAI-Compatible HTTP"| Server2
```

### 3.2 Frontend Component Dependency Graph
```mermaid
flowchart TD
    RootLayout["app/layout.tsx"] --> AppProvider["context/AppContext.tsx"]
    RootLayout --> Shell["components/layout/Shell.tsx"]
    Shell --> Sidebar["components/layout/Sidebar.tsx"]
    Shell --> Header["components/layout/Header.tsx"]
    Sidebar --> NavIcon["components/navigation/NavigationIcon.tsx"]
    Sidebar --> BrandLogo["components/common/BrandLogo.tsx"]
    Header --> HeaderBrand["components/layout/HeaderBranding.tsx"]

    Mission["app/page.tsx (/ & /agent-mission-control)"] --> InfraMon["components/system/ServerInfrastructureMonitor.tsx"]
    TriageDetail["app/ai-triage-workbench/[id]/page.tsx"] --> Matrix["components/compact/IncidentVerdictMatrix.tsx"]
    TriageDetail --> CDS["components/compact/CompactDesignSystem.tsx"]
    TriageDetail --> PromptModal["components/prompt-inspector/ActualPromptInspectorModal.tsx"]

    AIS["app/agent-intelligence-studio/page.tsx (5,162L)"] --> AISOverview["components/compact/AgentIntelligenceStudioOverview.tsx"]
    AIS --> AiTest["components/compact/AiTestWorkbench.tsx"]
    AIS --> AccSum["components/compact/AccuracyLearningSummary.tsx"]
    AIS --> RevWB["components/compact/ReviewIncidentsWorkbench.tsx"]
    AIS --> VerHist["components/compact/ManageVersionHistory.tsx"]
    AIS --> RuleLearn["components/learning/RuleLearningDashboard.tsx"]
    AIS --> PromptModal
    AIS --> CDS

    VerIntel["app/verdict-intelligence/page.tsx"] --> PilotDash["components/pilot/PilotControlAndDashboard.tsx"]
    VerIntel --> HistElig["components/pilot/HistoricalEligibilityPanel.tsx"]
    HumanRev["app/human-review-queue/page.tsx"] --> GTCert["components/review/GroundTruthCertificationPanel.tsx"]
    InfCtrl["app/inference-control/page.tsx"] --> InfraMon
    InfCtrl --> TokBif["components/telemetry/TokenBifurcationWidget.tsx"]
    AdminGuide["app/admin-guide/page.tsx"] --> GuideComp["components/admin-guide/* (9 components)"]

    Orphan1["ORPHAN: PhasePlaceholder.tsx"] -.->|"0 importers"| Nowh["Unreferenced"]
    Orphan2["ORPHAN: CompactGovernancePanels.tsx"] -.->|"0 importers"| Nowh
```

### 3.3 Backend Module Dependency Graph
```mermaid
flowchart TD
    Main["app/main.py"] --> Routers["25 API Routers (app/api/*.py)"]
    Main --> Scheduler["fortisiem_scheduler.py"]
    Routers --> Deps["app/api/deps.py (JWT/Cookie + RBAC)"]
    Routers --> Services["Core Services (app/services/*.py)"]
    Services --> VerdictSvc["ai_verdict_service.py"]
    VerdictSvc --> Pipeline["verdict_pipeline.py (Shared Safeguards)"]
    Pipeline --> Norm["evidence_normalization_service.py"]
    Pipeline --> Allowlist["model_payload_allowlist.py"]
    Pipeline --> PolicyElig["policy_eligibility_service.py"]
    Pipeline --> Compiler["policy_compiler_service.py"]
    Pipeline --> RAG["verified_semantic_retrieval_service.py"]
    Pipeline --> Budget["token_budget_service.py + evidence_compaction_service.py"]
    Pipeline --> Provider["model_provider/factory.py -> openai_compatible.py"]
    Pipeline --> Validators["independent_verdict_validator.py + verdict_trustworthiness_engine.py"]
    Services --> Models["25 SQLAlchemy Model Modules (app/models/*.py)"]
    Workers["app/workers/tasks.py"] --> VerdictSvc
    Workers --> SimSvc["policy_simulation_service.py"]
    Workers --> DryRunSvc["dry_run_service.py"]
```

### 3.4 Frontend-to-Backend API Mapping
```mermaid
flowchart LR
    ApiTS["frontend/src/lib/api.ts (134 methods, 117 used)"] -->|"/api/auth/*"| AuthAPI["api/auth.py"]
    ApiTS -->|"/api/dashboard/*"| DashAPI["api/dashboard.py"]
    ApiTS -->|"/api/incidents/*"| IncAPI["api/incidents.py"]
    ApiTS -->|"/api/rules/*"| RulesAPI["api/rules.py"]
    ApiTS -->|"/api/prompts/*"| PromptsAPI["api/prompts.py (38 routes)"]
    ApiTS -->|"/api/rule-learning/*"| RLAPI["api/rule_learning.py (19 routes)"]
    ApiTS -->|"/api/ais-evaluation/*"| AisEvalAPI["api/ais_evaluation.py (3 routes)"]
    ApiTS -->|"/api/ground-truth/*"| GTAPI["api/ground_truth.py (13 routes)"]
    ApiTS -->|"/api/verdict-intelligence/*"| VIAPI["api/verdict_intelligence.py (13 routes)"]
    ApiTS -->|"/api/pilot/*"| PilotAPI["api/pilot.py (16 routes)"]
    ApiTS -->|"/api/dry-run/* & /api/evaluations/*"| DryAPI["api/dry_run.py + api/evaluations.py"]
    ApiTS -->|"/api/chat/*"| ChatAPI["api/chat.py"]
    ApiTS -->|"/api/fortisiem/* & /api/imports/*"| FsiemAPI["api/fortisiem.py + api/imports.py"]
    ApiTS -->|"/api/system/*, /api/llm-config/*, /api/telemetry/*, /api/tokens/*"| OpsAPI["System/LLM/Telemetry APIs"]
```

### 3.5 Incident Ingestion and Processing Workflow
```mermaid
flowchart TD
    Source{"Ingestion Trigger"} -->|"ZIP / JSON Upload"| ImportsAPI["POST /api/imports/upload"]
    Source -->|"Manual / Continuous Poll"| Poller["FortiSIEMService + SentinelIngestWorker"]
    ImportsAPI --> ZipGuard["zip_guard.py (bomb/ratio protection)"]
    ZipGuard --> IngestSvc["IngestionService"]
    Poller --> IngestSvc
    IngestSvc --> RuleMap["resolve_canonical_rule + RuleParser"]
    IngestSvc --> DBWrite["Persist Incident + IncidentEvent + HistoricalGroundTruth (isolated)"]
    DBWrite -->|"auto_ai_verdict=true"| Dispatch["dispatch_incident_triage()"]
    Dispatch -->|"USE_ASYNC_CELERY & Redis"| CeleryQ["Celery live_triage queue"]
    Dispatch -->|"Fallback / Dev"| InProc["_execute_incident_triage_core()"]
    CeleryQ --> Triage["AIVerdictService.evaluate_incident()"]
    InProc --> Triage
```

### 3.6 AI Verdict Generation Workflow
```mermaid
flowchart TD
    Entry["AIVerdictService.evaluate_incident()"] --> Lock["Intra-process Lock + DistributedLockManager"]
    Lock --> Pipe["run_shared_verdict_pipeline()"]
    Pipe --> S1["1. Normalize & Sanitize Payload (strip GT keys)"]
    S1 --> S2{"2. PolicyEligibilityService"}
    S2 -->|"Draft/Revoked/Suspended"| Abstain1["Early Exit: REQUIRES_ATTENTION"]
    S2 -->|"Eligible"| S3["3. EvidencePreflightValidator + PolicyCompilerService (9 sections)"]
    S3 --> S4["4. VerifiedSemanticRetrievalService (Rule-scoped RAG)"]
    S4 --> S5["5. TokenBudgetService + EvidenceCompactionService"]
    S5 -->|"Exceeds Context"| Abstain2["Early Exit: CONTEXT_WINDOW_EXCEEDED"]
    S5 -->|"Within Budget"| S6["6. GPUWorkloadManager + OpenAICompatibleProvider (vLLM)"]
    S6 --> S7["7. ModelClaimExtractor + IndependentVerdictValidator + ReasoningIntegrityEngine"]
    S7 --> S8["8. VerdictTrustworthinessEngine (VerdictClaimValidator + EvidenceSufficiency + VerdictGuardrailsEngine)"]
    S8 --> Persist["Persist Incident.ai_verdict, TrustAssessment, ActualLLMPromptCapture, TokenUsage, Timeline, AuditLog"]
```

### 3.7 Agent Intelligence Studio Evaluation Workflow
```mermaid
flowchart TD
    AISUI["/agent-intelligence-studio UI"] --> Draft["Generate Intelligent Draft / Manual Draft"]
    Draft --> Quality["PolicyQualityValidator (Gates G1-G8 Structural Checks)"]
    Quality --> SimDispatch["dispatch_policy_simulation()"]
    SimDispatch -->|"Sync / Async Celery"| SimSvc["PolicySimulationService.evaluate_candidate_policy()"]
    SimSvc --> SharedPipe["run_shared_verdict_pipeline(is_simulation=True)"]
    SharedPipe --> GTAdj["HistoricalGroundTruthValidator.adjudicate_incident_ground_truth()"]
    GTAdj --> Metrics["EmpiricalAccuracyEvaluator + CalibrationEvaluator"]
    Metrics --> RunDB[("HistoricalEvaluationRunRecord & ResultRecord")]
    RunDB --> Readiness["ProductionReadinessService + RuleLearningService"]
    Readiness --> Gov["PolicyVersionGovernanceService (Approve / Activate / Revoke / Rollback)"]
```

### 3.8 Background Task Execution Workflow
```mermaid
flowchart TD
    AppBoot["FastAPI lifespan()"] --> Sup["fortisiem_scheduler.start_supervisor()"]
    Sup -->|"Leader Lease in scheduler_state.json"| PollLoop["_worker_loop() -> pull_all / pull_incremental"]
    Sup -->|"Backlog Lease (every ~30s)"| Backlog["run_pending_reconciliation_until_drained()"]
    APICall["API Trigger (Triage / Simulation / Dry-Run)"] --> Dispatch{"USE_ASYNC_CELERY && Redis?"}
    Dispatch -->|"True"| CeleryBroker[("Redis Broker")]
    CeleryBroker -->|"live_triage"| T1["triage_incident_task"]
    CeleryBroker -->|"simulation_replay"| T2["run_policy_simulation_task / run_dry_run_job_task"]
    CeleryBroker -.->|"maintenance (0 routed tasks)"| T3["Unused Queue"]
    Dispatch -->|"False"| Direct["In-process async execution"]
    BeatUnit["systemd: ai-verdict-scheduler (celery beat)"] -.->|"0 beat_schedule entries"| CeleryApp["celery_app.py"]
```
"""
    write_md("01_REPOSITORY_AND_ARCHITECTURE_BASELINE.md", md)


def gen_02_inventory(d: Dict[str, Any]):
    inv = d["inv"]
    cats = inv["summary"]["category_counts"]
    lines = inv["summary"]["category_lines"]
    rows = []
    for k in sorted(cats.keys()):
        lc = lines[k]
        rows.append(f"| `{k}` | {cats[k]} | {lc['total']:,} | {lc['non_empty']:,} | {lc['code']:,} |")

    large_files = []
    for f in sorted(inv["files"], key=lambda x: -x["lines"]["total"]):
        if f["category"] not in {"docs", "frontend_build_config", "backend_test", "frontend_test", "scratch", "root_script", "backend_migration"} and f["lines"]["total"] >= 500:
            large_files.append(f"| `{f['path']}` | `{f['category']}` | {f['lines']['total']:,} | {f['lines']['code']:,} |")

    md = f"""# 02 — Complete Codebase Inventory

## 1. Category Breakdown (2,229 Tracked Files)

| Category | File Count | Total Lines | Non-Empty Lines | Code Lines |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

## 2. Largest Application Source Files (>= 500 Lines)

| File Path | Category | Total Lines | Code Lines |
|---|---|---:|---:|
{chr(10).join(large_files)}
"""
    write_md("02_COMPLETE_CODEBASE_INVENTORY.md", md)


def gen_03_frontend(d: Dict[str, Any]):
    fe = d["fe"]
    es = d["eslint"]
    unused_vars_files = []
    for ef in es:
        cnt = sum(1 for m in ef["messages"] if m.get("ruleId") == "@typescript-eslint/no-unused-vars")
        if cnt:
            rel = Path(ef["filePath"]).relative_to(REPO_ROOT).as_posix()
            unused_vars_files.append(f"| `{rel}` | {cnt} |")

    shadow_rows = [
        f"| `{p['route']}` | `{p['shadowed_by_redirect_to']}` | `{p['file']}` | {p['lines']} | `CONFIRMED_UNUSED` | `REMOVE` |"
        for p in fe["pages"] if p["shadowed_by_redirect_to"]
    ]
    api_unused = [m for m in d["ais_deps"]["frontend_api"]["unused_in_src"] if m["method"] != "processLine"]
    api_rows = [f"| `api.{m['method']}` | `frontend/src/lib/api.ts:{m['line']}` | `POSSIBLY_UNUSED` | `VERIFY_FIRST` |" for m in api_unused]

    md = f"""# 03 — Frontend Dead Code & Redundancy Audit

## 1. Compiler & Linter Baseline
- **`tsc --noEmit`**: **PASS** (0 TypeScript errors).
- **`eslint src`**: **362 errors** (`308` `@typescript-eslint/no-explicit-any`, `34` `react-hooks/set-state-in-effect`, `11` `react/no-unescaped-entities`, `6` `react-hooks/immutability`, `1` `refs`, `1` `purity`, `1` `prefer-const`) and **258 warnings** (`232` `@typescript-eslint/no-unused-vars`, `23` `react-hooks/exhaustive-deps`, `3` `@next/next/no-location-assign-relative-destination`).
- **`npm test`**: **16/16 test suites PASS**.

## 2. Shadowed & Unreachable Legacy Route Pages (13 Files)
`frontend/next.config.ts` defines `redirects()` for 15 legacy URL paths. 13 of those have corresponding `page.tsx` files (3 lines each) that are **never rendered at runtime** because Next.js issues the redirect prior to page rendering, and 0 imports/tests reference them:

| Route | Redirect Destination | Page File | Lines | Classification | Action |
|---|---|---|---:|---|---|
{chr(10).join(shadow_rows)}

*(Note: `/agent-mission-control/page.tsx` is a 4-line active route wrapper for `/` referenced in `Sidebar.tsx`, so it is `ACTIVE`.)*

## 3. Orphaned Components & Unused Exports
1. `frontend/src/components/common/PhasePlaceholder.tsx` (L1–105, 105 lines): Phase 1 placeholder screen; 0 importers, 0 test refs. **Classification:** `CONFIRMED_UNUSED` -> `REMOVE`.
2. `frontend/src/components/compact/CompactGovernancePanels.tsx` (L1–361, 361 lines): Exports `ProductionEligibilityChecklist`, `ReviewDecisionPanel`, `ConfirmationDialog`; 0 importers, 0 test refs. **Classification:** `CONFIRMED_UNUSED` -> `REMOVE`.
3. `frontend/src/components/compact/CompactDesignSystem.tsx`: Exports `RuleStatusSummary` (L220–311), `EmptyState` (L807–835), and `ErrorState` (L837–870) with 0 internal/external/test refs -> `CONFIRMED_UNUSED` (`REMOVE`). `DiagnosticIssueCard` (L364) has 1 internal ref only (remove `export`).
4. **Unused Public SVG Assets** (5 files in `frontend/public/`): `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` (0 refs across `frontend/`) -> `CONFIRMED_UNUSED` (`REMOVE`).

## 4. Unused `api.ts` Client Methods ({len(api_unused)} / {d['ais_deps']['frontend_api']['total_api_methods']})

| Symbol | Location | Classification | Action |
|---|---|---|---|
{chr(10).join(api_rows)}

## 5. Legacy UI Implementations & Duplicated Logic
- **AIS Legacy 7-Tab Toggle (`frontend/src/app/agent-intelligence-studio/page.tsx`, 5,162 lines)**: Maintains both Compact UI (`compactUi=true`, default) and Legacy 7-tab View (`VERDICTUM_COMPACT_UI_ENABLED="false"`). Marked `SUPERSEDED` (`REFACTOR` / `VERIFY_FIRST`) because `frontend/tests/phase3-compact-ui.test.mjs:182` asserts `VERDICTUM_COMPACT_UI_ENABLED`.
- **Duplicated UI Helpers**: `getSeverityBadge` (5 pages), `getVerdictBadge` (4 pages), `formatEpoch` (5 pages), and inline modal backdrops (`fixed inset-0`, 4 pages) -> `DUPLICATE` (`CONSOLIDATE` into `src/lib/formatters.ts` and shared `Modal`).

## 6. ESLint `@typescript-eslint/no-unused-vars` Summary (232 Warnings)

| File | Unused Var/Import Count |
|---|---:|
{chr(10).join(unused_vars_files)}
"""
    write_md("03_FRONTEND_DEAD_CODE_AUDIT.md", md)


def gen_04_backend(d: Dict[str, Any]):
    be = d["be"]
    da = d["deep"]["backend"]
    unused_imp_counts = Counter(u["file"] for u in be["unused_imports"] if not u["file"].endswith("__init__.py"))
    imp_rows = [f"| `{f}` | {cnt} |" for f, cnt in unused_imp_counts.most_common()]

    meth_rows = []
    for m in da["unused_service_methods"]:
        cls_cat = "CONFIRMED_UNUSED" if (m["test_hits"] == 0 and m["script_hits"] == 0) else "TEST_ONLY"
        act = "REMOVE" if cls_cat == "CONFIRMED_UNUSED" else "RETAIN"
        meth_rows.append(f"| `{m['file']}:{m['lineno']}` | `{m['class']}.{m['method']}` | {m['lines']} | {m['test_hits']} | {m['script_hits']} | `{cls_cat}` | `{act}` |")

    shim_rows = []
    for m in be["modules"]:
        if not m["prod_importers"] and m["file"] not in {"backend/app/main.py", "backend/app/cli.py", "backend/app/__init__.py", "backend/app/core/__init__.py", "backend/app/schemas/__init__.py", "backend/app/workers/__init__.py", "backend/app/services/model_provider/__init__.py"} and not m["file"].startswith("backend/app/scripts/"):
            shim_rows.append(f"| `{m['file']}` | {m['lines']} | {len(m['test_importers'])} | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |")

    md = f"""# 04 — Backend Dead Code & Architecture Audit

## 1. Compatibility Alias Shims (0 Production Importers)
11 thin re-export modules (11–18 lines each, 143 lines total) exist solely to alias legacy service names to "Agentic SOC" names. They have **0 production callers** and are imported exclusively by `backend/tests/test_agentic_nomenclature.py`:

| File | Lines | Test Importers | Classification | Recommended Action |
|---|---:|---:|---|---|
{chr(10).join(shim_rows)}

## 2. Unused Service Methods in Production (20 Total: 7 Confirmed Dead, 13 Test-Only)

| Location | Method | Lines | Test Hits | Script Hits | Classification | Action |
|---|---|---:|---:|---:|---|---|
{chr(10).join(meth_rows)}

## 3. Unused Top-Level Symbols & Pydantic Schemas
- `backend/app/schemas/canonical_evidence.py:7` — `EvidenceLifecycleStage` (13L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- `backend/app/schemas/dashboard.py:18` — `StatusCount` (3L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- `backend/app/services/blind_review_guard.py:519` — `get_blind_mask_response_marker` (2L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- Unused schema classes (0 prod refs outside `schemas/__init__.py`, 0 test refs): `TokenPayload` (`auth.py`), `LearningRecordCreate` (`learning.py`), `PromptDraftGenerateRequest` (`prompt.py`), `RuleCreate` (`rule.py`).

## 4. Unused Imports Across `backend/app/` ({sum(unused_imp_counts.values())} Total)

| File | Unused Imports |
|---|---:|
{chr(10).join(imp_rows[:40])}

*(Full per-line list stored in `evidence/backend_analysis.json`.)*

## 5. Large Multi-Responsibility Modules (Simplification Candidates, Not Dead Code)
- `empirical_benchmark_harness.py` (2,442 lines)
- `fortisiem_service.py` (2,435 lines)
- `policy_simulation_service.py` (1,492 lines)
- `ground_truth_certification_service.py` (1,430 lines)
- `verdict_pipeline.py` (1,381 lines)
- `rule_learning_service.py` (1,366 lines)
- `ais_evaluation_service.py` (1,268 lines)
- `prompts.py` API router (1,947 lines, 38 endpoints)
"""
    write_md("04_BACKEND_DEAD_CODE_AUDIT.md", md)


def gen_05_api(d: Dict[str, Any]):
    eps = d["api"]["endpoints"]
    status_cnt = Counter(e["status"] for e in eps)
    no_fe_rows = []
    for e in eps:
        if not e["fe_refs"]:
            no_fe_rows.append(f"| `{e['method']}` | `{e['full_paths'][0]}` | `{e['file']}:{e['lineno']}` | `{e['auth_summary']}` | {len(e['test_refs'])} | {len(e['script_refs'])} | `{e['status']}` | `{e['recommended_action']}` |")

    all_ep_rows = []
    for e in eps:
        all_ep_rows.append(f"| `{e['method']}` | `{', '.join(e['full_paths'])}` | `{e['file']}:{e['lineno']}` | `{e['auth_summary']}` | {len(e['fe_refs'])} | {len(e['test_refs'])} | `{e['status']}` |")

    md = f"""# 05 — API Endpoint Usage Audit

## 1. Endpoint Inventory Summary
- **Total Registered Handler Definitions:** {len(eps)} across 25 API router modules.
- **Status Breakdown:** {dict(status_cnt)}
- **Duplicate Route Anomalies:**
  1. `backend/app/api/health.py` defines `@router.get("/health")` & `@router.get("/api/health")` (and `/metrics` & `/api/metrics`), while `main.py:310-311` mounts `health.router` at both `""` and `"/api"`. This creates duplicate `/api/health` and `/api/metrics` registrations and unintended `/api/api/health` and `/api/api/metrics` routes.
  2. `backend/app/main.py` mounts 5 routers (`prompts`, `verdict_intelligence`, `rule_learning`, `ais_evaluation`, `ground_truth`) under both `/api` and `/api/v1`. Zero frontend files call `/api/v1`; only 4 backend test suites call `/api/v1`.

## 2. Endpoints Without Frontend Consumers ({len(no_fe_rows)} Handlers)

| Method | Path | Handler | Auth | Tests | Scripts | Status | Recommended Action |
|---|---|---|---|---:|---:|---|---|
{chr(10).join(no_fe_rows)}

## 3. Complete Endpoint Matrix ({len(all_ep_rows)} Handlers)

| Method | Full Path(s) | Handler | Auth | FE Refs | Test Refs | Status |
|---|---|---|---|---:|---:|---|
{chr(10).join(all_ep_rows)}
"""
    write_md("05_API_ENDPOINT_USAGE_AUDIT.md", md)


def gen_06_ais_llm(d: Dict[str, Any]):
    ais = d["ais_deps"]["ais_services"]
    rows = [f"| `{Path(s['file']).name}` | {s['lines']:,} | {len(s['prod_callers'])} | {s['test_callers_count']} | {', '.join(Path(c).name for c in s['prod_callers'][:5])} |" for s in ais]

    md = f"""# 06 — Agent Intelligence Studio & AI Engine Legacy Code Audit

## 1. Authoritative Live AI Verdict Execution Map
Every live AI verdict (`AIVerdictService.evaluate_incident` in `ai_verdict_service.py`) and policy simulation (`PolicySimulationService` / `DryRunService`) executes through the unified pipeline `run_shared_verdict_pipeline` (`backend/app/services/verdict_pipeline.py`):

1. **Evidence Collection & Sanitization**: `EvidenceNormalizationService` + `model_payload_allowlist.build_model_facing_payload` + `HistoricalGroundTruthValidator.sanitize_incident_for_inference` (strips resolution/ground truth keys).
2. **Policy Selection & Eligibility**: `PromptStudioService.get_or_create_rule_prompt` + `PolicyEligibilityService.evaluate_eligibility` (blocks `DRAFT`, `REVOKED`, `ARCHIVED`, `SEMANTIC_MISMATCH`, `RULE_SUSPENDED` in live mode) + `assess_policy_runtime_certification`.
3. **Rule Semantics & Preflight**: `get_rule_semantics_and_contract` (`RuleIntelligenceSnapshot` + `EvidenceContractService`) -> `EvidencePreflightValidator.validate`.
4. **Prompt Compilation & RAG**: `PolicyCompilerService.compile` (9-section unified policy) + `VerifiedSemanticRetrievalService.retrieve_verified_precedents` (rule-scoped, temporal/self-exclusion safe).
5. **Token Budget & Compaction**: `LLMConfigService.get_model_profile` + `TokenBudgetService.budget_prompt` + `EvidenceCompactionService` + `ModelTokenizerService`.
6. **LLM Inference & Capture**: `GPUWorkloadManager` (semaphore + circuit breaker) -> `OpenAICompatibleProvider` (`model_provider/openai_compatible.py`) + `ActualPromptCaptureService`.
7. **Post-Inference Validation & Trust**:
   - `ModelClaimExtractor.extract_and_ground_claims` -> `IndependentVerdictValidator.validate_verdict` (calls `ReasoningIntegrityEngine`).
   - `VerdictTrustworthinessEngine.evaluate_verdict_trust` (calls `VerdictClaimValidator.verify_claims`, `EvidenceSufficiencyEngine`, `VerdictGuardrailsEngine.apply_guardrails`).

## 2. Classification of AIS & AI Services

| Service Module | Lines | Prod Callers | Test Callers | Primary Callers |
|---|---:|---:|---:|---|
{chr(10).join(rows)}

## 3. Identified Overlaps, Legacy Layers & Classifications

| Implementation | Classification | Role & Recommendation |
|---|---|---|
| `verdict_pipeline.py` + `ai_verdict_service.py` | `ACTIVE` | Authoritative live & simulation execution engine. **RETAIN**. |
| `ModelClaimExtractor` + `IndependentVerdictValidator` + `ReasoningIntegrityEngine` | `ACTIVE` | Primary claim grounding & reasoning integrity layer. **RETAIN (Protected)**. |
| `VerdictClaimValidator` + `VerdictGuardrailsEngine` + `VerdictTrustworthinessEngine` | `ACTIVE` | Defense-in-depth trust & safety guardrails invoked by `verdict_pipeline.py`. **RETAIN (Protected — do not remove validators)**. |
| `PolicySimulationService` (`policy_simulation_service.py`) | `ACTIVE` | Primary AIS 2.1 empirical evaluation engine. Contains internal `_simulate_model_output` passed as `simulated_output_fn` when `SIMULATED`. |
| `EmpiricalBenchmarkHarness` (`empirical_benchmark_harness.py`, 2,442L) & `AIS27BenchmarkRunner` (`ais27_benchmark_runner.py`, 804L) | `ACTIVE` (Eval) | Offline/3-mode GPU benchmark runners for AIS 2.5–2.7 empirical certification. **RETAIN** (`REQUIRED_HISTORICAL`). |
| `DryRunService` (`dry_run_service.py`, 524L) + `EvaluationService` (`evaluation_service.py`, 427L) | `DUPLICATE` (`ACTIVE`) | Phase 3 Dry-Run engine adapted (`LEGACY_DRY_RUN_ADAPTER`) onto `run_shared_verdict_pipeline`. Still actively called by `/agent-simulation-lab`. **REFACTOR** only after migrating UI to `/api/verdict-intelligence/*`. |
| `CalibrationEvaluationService` (`calibration_evaluation_service.py`, 260L) vs `CalibrationEvaluator` (`calibration_evaluator.py`, 168L) | `DUPLICATE` / `SUPERSEDED` | `CalibrationEvaluator` is active in `pilot_service.py` & `policy_simulation_service.py`. `CalibrationEvaluationService` only serves `GET /api/rules/{{id}}/calibration-report` (0 FE consumers). **CONSOLIDATE / VERIFY_FIRST**. |
| `WilsonScoreEvaluator` (`wilson_evaluator.py`, 48L) vs `EmpiricalAccuracyEvaluator.calculate_wilson_ci` | `DUPLICATE` | Identical Wilson 95% CI math. **CONSOLIDATE** (`RuleLearningService` can call shared helper). |
| `ais_evaluation_service.py:1096` `get_missing_inference_candidates` (22L) | `CONFIRMED_UNUSED` | 0 prod, 0 test, 0 script callers. **REMOVE** (Batch 1). |
"""
    write_md("06_AIS_AND_LLM_LEGACY_CODE_AUDIT.md", md)


def gen_07_database(d: Dict[str, Any]):
    models = d["be"]["models"]
    m_rows = [f"| `{m['model']}` | `{m['tablename']}` | `{m['file']}:{m['lineno']}` | {len(m['columns'])} | {len(m['app_refs'])} | {len(m['test_refs'])} | `ACTIVE` |" for m in models]

    md = f"""# 07 — Database & Persistence Audit

## 1. Schema & Migration Overview
- **ORM Framework:** SQLAlchemy 2.0 Async (`DeclarativeBase` in `backend/app/database.py`), supporting PostgreSQL (`asyncpg`) in production and SQLite (`aiosqlite`) in dev/testing.
- **Migration Framework:** Alembic (`backend/alembic/versions/001_initial_schema.py` through `016_ground_truth_certification_and_cohort_isolation.py`, 16 migrations).
- **Startup Guard & Self-Healing:** `backend/app/core/db_guard.py` enforces DB safety; `main.py` runs `verify_schema_on_startup` (`is_production=True` blocks runtime DDL), plus legacy self-healing backfills in `lifespan()` (lines 84–227).
- **Limitation:** Read-only local audit did not query live Server 1 PostgreSQL row counts or index bloat.

## 2. ORM Model Inventory ({len(models)} Models Across 25 Model Files)
Every registered SQLAlchemy model in `backend/app/models/__init__.py` has active production consumers (`app_refs > 0`):

| Model Class | Table Name | Definition | Columns | App Refs | Test Refs | Status |
|---|---|---|---:|---:|---:|---|
{chr(10).join(m_rows)}

## 3. Potentially Unused Columns (Batch 6 Restricted — Requires Explicit Approval)

| Model | Column | File & Line | App Refs | Test Refs | Classification | Action |
|---|---|---|---:|---:|---|---|
| `TokenUsageRecord` | `estimated_cost_usd` | `backend/app/models/token_usage.py:41` | 0 | 0 | `POSSIBLY_UNUSED` | `VERIFY_FIRST` (Batch 6) |
| `GroundTruthValidationRecord` | `is_eligible_for_evaluation` | `backend/app/models/verdict_intelligence.py:94` | 0 | 0 | `POSSIBLY_UNUSED` | `VERIFY_FIRST` (Batch 6) |

## 4. Redundant Persistence Notice
- `DryRunConfig`, `DryRunJob`, and `DryRunResult` persist Phase 3 simulation runs alongside `HistoricalEvaluationRunRecord` and `HistoricalEvaluationResultRecord` (`DryRunService` dual-writes both via `LEGACY_DRY_RUN_ADAPTER`). Treated as **protected historical evidence**; do NOT drop tables without explicit migration/archival plan.
"""
    write_md("07_DATABASE_AND_PERSISTENCE_AUDIT.md", md)


def gen_08_workers(d: Dict[str, Any]):
    md = """# 08 — Background Worker & Schedule Audit

## 1. Discovered Background Infrastructure
1. **Celery + Redis (`backend/app/workers/celery_app.py`, `tasks.py`)**:
   - Configured queues: `live_triage`, `simulation_replay`, `maintenance`.
   - Registered tasks (`tasks.py`):
     - `triage_incident_task` -> routed to `live_triage`, dispatched by `dispatch_incident_triage()`.
     - `run_policy_simulation_task` -> routed to `simulation_replay`, dispatched by `dispatch_policy_simulation()`.
     - `run_dry_run_job_task` -> routed to `simulation_replay`, dispatched by `DryRunService`.
   - In-process fallback: When `USE_ASYNC_CELERY=false` or Redis is unavailable, `dispatch_*` runs tasks in-process asynchronously.
2. **In-Process Continuous Poller (`backend/app/services/fortisiem_scheduler.py` — `SentinelIngestWorker`)**:
   - Started in `FastAPI` `lifespan()` (`main.py:250-255`).
   - Uses `scheduler_state.json` atomic file locking for multi-worker leader election across 4 Uvicorn processes (`_try_claim_or_renew_leadership`, `_claim_or_renew_backlog_lease`).
   - Polls FortiSIEM and drains pending incident AI verdicts (`run_pending_reconciliation_until_drained`).

## 2. Findings & Anomalies

| Component | Location | Finding | Classification | Risk | Recommended Action |
|---|---|---|---|---|---|
| `ai-verdict-scheduler.service` (Celery Beat) | `deployment/systemd/ai-verdict-scheduler.service` & `celery_app.py` | Systemd runs `celery beat`, but `celery_app.py` defines **0 `beat_schedule` jobs**. Actual periodic polling runs in `SentinelIngestWorker` inside Uvicorn. | `POSSIBLY_UNUSED` | `HIGH` | `VERIFY_FIRST` (Confirm `verify_server1.sh` dependency before disabling unit or migrating poller to Beat) |
| `maintenance` Celery Queue | `backend/app/workers/celery_app.py:40-43` | Queue `maintenance` is declared and consumed by `ai-verdict-worker.service`, yet **0 tasks** are routed to it. | `POSSIBLY_UNUSED` | `LOW` | `VERIFY_FIRST` (Retain if reserved for retention cleanup job) |
"""
    write_md("08_BACKGROUND_WORKER_AND_SCHEDULE_AUDIT.md", md)


def gen_09_deps(d: Dict[str, Any]):
    deps = d["ais_deps"]["dependencies"]
    py_rows = []
    for p in deps["python"]:
        notes = "Active"
        if p["pkg"] in {"email-validator", "greenlet", "python-multipart"}:
            notes = "Runtime plugin/driver dependency (Pydantic EmailStr / SQLAlchemy async / FastAPI UploadFile)"
        elif p["pkg"] == "pyjwt":
            notes = "Imported as `import jwt` in `app/utils/security.py`"
        elif p["pkg"] in {"pytest", "pytest-asyncio", "httpx"}:
            notes = "Test & HTTP client dependency"
        py_rows.append(f"| `{p['raw']}` | {p['code_refs']} | `{notes}` |")

    node_rows = []
    for n in deps["node"]:
        note = "Active"
        if n["pkg"] == "@tailwindcss/turbopack":
            note = "POTENTIALLY UNUSED — `postcss.config.mjs` uses `@tailwindcss/postcss` only; verify with `next build`"
        node_rows.append(f"| `{n['section']}` | `{n['pkg']}` | `{n['version']}` | {n['refs']} | {note} |")

    md = f"""# 09 — Dependency & Package Audit

## 1. Backend Python Dependencies (`backend/requirements.txt` — {len(deps['python'])} Direct Packages)

| Declaration | Static Code Refs | Verification Status |
|---|---:|---|
{chr(10).join(py_rows)}

*(Note: `pytest` and `pytest-asyncio` are declared in `requirements.txt` alongside production dependencies because there is no separate `requirements-dev.txt`. Moving test-only deps to `requirements-dev.txt` is an optional packaging improvement, not a removal.)*

## 2. Frontend Node Dependencies (`frontend/package.json` — {len(deps['node'])} Direct Packages)

| Section | Package | Version | Static Refs | Verification Status |
|---|---|---|---:|---|
{chr(10).join(node_rows)}
"""
    write_md("09_DEPENDENCY_AND_PACKAGE_AUDIT.md", md)


def gen_10_deployment(d: Dict[str, Any]):
    dep_files = [f for f in d["inv"]["files"] if f["category"] == "deployment"]
    rows = [f"| `{f['path']}` | {f['lines']['total']} | `ACTIVE` / `VERIFY` |" for f in dep_files]
    md = f"""# 10 — Deployment & Infrastructure Audit

## 1. Deployment Artifacts Inventory ({len(dep_files)} Files)

| File | Lines | Status |
|---|---:|---|
{chr(10).join(rows)}

## 2. Key Infrastructure Findings
1. **Superseded LLM Installer**: `deployment/scripts/install_ollama_llm.sh` (58 lines, port 11434, Ollama `qwen2.5:7b`) is `SUPERSEDED` by `deployment/scripts/install_llm_server.sh` (vLLM AWQ on port 8000, called by `setup_server2_gpu.sh`). **Action:** `ARCHIVE`.
2. **Celery Beat Systemd Unit**: `deployment/systemd/ai-verdict-scheduler.service` runs Celery Beat without any `beat_schedule` in `celery_app.py`. Referenced by `install_ubuntu.sh`, `rollback_server1.sh`, `start_services.sh`, `stop_services.sh`, `verify_server1.sh` -> requires coordinated infrastructure decision (`VERIFY_FIRST`, Batch 6).
3. **Nginx Reverse Proxy (`deployment/nginx/ai-verdict.conf`)**: Proxies `/api/`, `/health`, `/metrics`, and `/` with `proxy_read_timeout 300s`. Matches `health.py` root routes.
4. **Disaster Recovery Scripts**: `backup_db.sh`, `rollback_server1.sh`, `verify_server1.sh`, `backend/app/scripts/backup.py`, `restore.py` are **REQUIRED** operational/DR utilities — retain strictly.
5. **Remote Parity Limitation**: Live Server 1 and Server 2 SSH inspection was not performed in this read-only local audit.
"""
    write_md("10_DEPLOYMENT_AND_INFRASTRUCTURE_AUDIT.md", md)


def gen_11_config(d: Dict[str, Any]):
    keys = d["deep"]["backend"]["settings_keys"]
    rows = []
    for k in keys:
        status = "ACTIVE" if k["prod_refs"] else "CONFIRMED_UNUSED"
        rows.append(f"| `Settings.{k['key']}` | L{k['line']} | {len(k['prod_refs'])} | {k['test_refs_count']} | {len(k['deploy_refs'])} | `{status}` |")
    md = f"""# 11 — Configuration & Environment Audit

*(No secrets or credential values are exposed; only configuration key names and code references are reported.)*

## 1. `backend/app/config.py` Settings Keys ({len(keys)} Keys)

| Setting Key | Line | Prod Refs | Test Refs | Deploy Refs | Status |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

## 2. Unused Configuration Findings
1. `Settings.APP_NAME` (`backend/app/config.py:40`): 0 references in Python code or tests (`PROJECT_NAME` is used everywhere). `install_ubuntu.sh` only writes `NEXT_PUBLIC_APP_NAME` for Next.js. -> `CONFIRMED_UNUSED` (`REMOVE`).
2. `Settings.PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED` (`backend/app/config.py:136`): 0 references across codebase, tests, and deployment templates. -> `CONFIRMED_UNUSED` (`REMOVE` after confirming no upcoming cron job expects it).
"""
    write_md("11_CONFIGURATION_AND_ENVIRONMENT_AUDIT.md", md)


def gen_12_duplicates_complexity(d: Dict[str, Any]):
    md = """# 12 — Duplicate Code & Complexity Analysis

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
"""
    write_md("12_DUPLICATE_CODE_AND_COMPLEXITY_ANALYSIS.md", md)


def gen_13_tests_docs(d: Dict[str, Any]):
    inv = d["inv"]["summary"]
    cmds = d["cmds"]["commands_executed"]
    cmd_rows = [f"| `{c['command']}` | `{c['status']}` | {c['notes']} |" for c in cmds]
    md = f"""# 13 — Test Code & Documentation Audit

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
- **`docs/`**: {inv['category_counts']['docs']:,} tracked files ({inv['category_lines']['docs']['total']:,} lines) across historical phase evidence folders. **Preserve untouched** as historical audit trail.

## 3. Audit Commands & Results

| Command | Status | Notes |
|---|---|---|
{chr(10).join(cmd_rows)}
"""
    write_md("13_TEST_AND_DOCUMENTATION_AUDIT.md", md)


def gen_14_protected(d: Dict[str, Any]):
    prot = d["prot"]
    rows = [f"| {p['domain']} | `{p['protection_level']}` | {', '.join('`'+f+'`' for f in p['files'][:4])} | {', '.join('`'+t+'`' for t in p['tests'])} |" for p in prot]
    md = f"""# 14 — Protected Functionality & Risk Matrix

The following subsystems are designated **Protected** per CCA 1.0 Section 17. No code inside these modules may be deleted or modified without explicit evidence, zero behavioral regression, and full targeted regression test passes.

| Protected Domain | Protection Level | Key Modules | Required Regression Tests |
|---|---|---|---|
{chr(10).join(rows)}

**Special Guardrail Note:** Both `IndependentVerdictValidator` (`ModelClaimExtractor` + `ReasoningIntegrityEngine`) AND `VerdictTrustworthinessEngine` (`VerdictClaimValidator` + `EvidenceSufficiencyEngine` + `VerdictGuardrailsEngine`) execute inside `verdict_pipeline.py`. Neither safety validator stack is marked for removal.
"""
    write_md("14_PROTECTED_FUNCTIONALITY_AND_RISK_MATRIX.md", md)


def gen_15_safe_candidates(d: Dict[str, Any]):
    confirmed = [c for c in d["dead"] if c["classification"] == "CONFIRMED_UNUSED"]
    rows = [f"| `{c['candidate_id']}` | `{c['file_path']}:{c['start_line']}-{c['end_line']}` | `{c['symbol_name']}` | {c['estimated_removable_lines']} | {c['estimated_removable_files']} | `{c['cleanup_batch']}` |" for c in confirmed]
    md = f"""# 15 — Safe Code Removal Candidates (`CONFIRMED_UNUSED`)

Total `CONFIRMED_UNUSED` candidates: **{len(confirmed)}** (representing **{d['final']['metrics']['confirmed_removable_lines_app_source']:,}** non-overlapping lines in application source, **{d['final']['metrics']['confirmed_unused_files']}** source files, and **{d['final']['metrics']['confirmed_unused_public_assets']}** SVG assets).

| Candidate ID | Location | Symbol | Est. Lines | Est. Files | Cleanup Batch |
|---|---|---|---:|---:|---|
{chr(10).join(rows)}
"""
    write_md("15_SAFE_CODE_REMOVAL_CANDIDATES.md", md)


def gen_16_manual_verification(d: Dict[str, Any]):
    mv = [c for c in d["dead"] if c["classification"] != "CONFIRMED_UNUSED"]
    rows = [f"| `{c['candidate_id']}` | `{c['classification']}` | `{c['risk_level']}` | `{c['file_path']}` | `{c['symbol_name']}` | {c['manual_verification_requirements']} |" for c in mv]
    md = f"""# 16 — Items Requiring Manual Verification

Total non-`CONFIRMED_UNUSED` candidates requiring human verification, consolidation design, or explicit approval: **{len(mv)}**.

| Candidate ID | Classification | Risk | File / Module | Symbol | Verification Requirement |
|---|---|---|---|---|---|
{chr(10).join(rows)}
"""
    write_md("16_MANUAL_VERIFICATION_REQUIRED.md", md)


def gen_17_cleanup_plan(d: Dict[str, Any]):
    by_batch = defaultdict(list)
    for c in d["dead"]:
        by_batch[c["cleanup_batch"]].append(c)

    sections = []
    for bname in sorted(by_batch.keys()):
        items = by_batch[bname]
        lines_sum = sum(x["estimated_removable_lines"] for x in items)
        files_sum = sum(x["estimated_removable_files"] for x in items)
        cids = ", ".join(x["candidate_id"] for x in items[:15]) + (f" ... (+{len(items)-15} more)" if len(items) > 15 else "")
        sections.append(f"""### {bname}
- **Candidates ({len(items)}):** `{cids}`
- **Estimated Scope:** {lines_sum:,} lines / {files_sum} files
- **Acceptance Criteria:** Zero `tsc --noEmit` errors, zero regressions in `frontend` (16/16) & `backend` core pytest suites, `git diff` limited strictly to target batch.
- **Rollback Strategy:** Single atomic Git revert (`git revert <batch_commit_sha>`).""")

    md = f"""# 17 — Proposed Safe Cleanup Implementation Plan (CCA 1.1+)

> **IMPORTANT:** This is a planning roadmap only. **Zero batches are authorized or executed during CCA 1.0.**

## Batch Roadmap
{chr(10).join(sections)}

## Cleanup Approval Matrix (All Approvals = `PENDING`)
*(Full machine-readable matrix in `CLEANUP_APPROVAL_MATRIX.json` and `CLEANUP_CANDIDATES.csv`.)*

| Candidate ID | File / Module | Reason | Risk | Est. Reduction | Recommendation | Approval |
|---|---|---|---|---|---|---|
""" + "\n".join(
        f"| `{r['candidate_id']}` | `{r['file_or_module']}` | {r['reason'][:80]} | `{r['risk']}` | {r['estimated_reduction']} | `{r['recommendation']}` | **{r['approval']}** |"
        for r in d["app_matrix"][:80]
    ) + (f"\n\n*(Showing first 80 of {len(d['app_matrix'])} rows; see `CLEANUP_APPROVAL_MATRIX.json` for complete table.)*" if len(d["app_matrix"]) > 80 else "")
    write_md("17_PROPOSED_CLEANUP_IMPLEMENTATION_PLAN.md", md)


def gen_18_regression_rollback(d: Dict[str, Any]):
    md = """# 18 — Regression Validation & Rollback Plan

## 1. Mandatory Pre-Batch Gate
1. Confirm clean Git working tree and create a dedicated cleanup branch per batch (e.g., `chore/cca-1.1-batch-1`).
2. Record pre-batch test baseline:
   - Frontend: `cd frontend && npx tsc --noEmit && npm.cmd test && npm.cmd run build`
   - Backend: `cd backend && .\\venv\\Scripts\\pytest.exe --ignore=tests/e2e_browser`
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
"""
    write_md("18_REGRESSION_AND_ROLLBACK_PLAN.md", md)


def gen_19_final_acceptance(d: Dict[str, Any]):
    gates = d["final"]["acceptance_gates"]
    rows = [f"| `{g['gate']}` | {g['name']} | **{g['status']}** | {g['evidence']} |" for g in gates]
    md = f"""# 19 — Final Audit Acceptance & Integrity Sign-Off

## 1. Acceptance Gates Evaluation (G1–G13)

| Gate | Requirement | Status | Supporting Evidence |
|---|---|---|---|
{chr(10).join(rows)}

## 2. Final Git Working Tree & Non-Mutation Verification
- `git_integrity_verified`: `{d['final']['git_integrity_verified']}`
- `unexpected_git_changes`: `{d['final']['unexpected_git_changes']}`
- Application source files deleted: **0**
- Application source files modified: **0**
- Database schemas or dependencies modified: **0**

## 3. Sign-Off Status
CCA 1.0 is **COMPLETE**. All 20 audit reports and 9 machine-readable registries have been generated inside `/docs/CCA_1_0/`. **STOPPED — awaiting explicit approval before commencing CCA 1.1.**
"""
    write_md("19_FINAL_AUDIT_ACCEPTANCE.md", md)


def main():
    d = load_all()
    gen_00_executive_summary(d)
    gen_01_baseline_and_arch(d)
    gen_02_inventory(d)
    gen_03_frontend(d)
    gen_04_backend(d)
    gen_05_api(d)
    gen_06_ais_llm(d)
    gen_07_database(d)
    gen_08_workers(d)
    gen_09_deps(d)
    gen_10_deployment(d)
    gen_11_config(d)
    gen_12_duplicates_complexity(d)
    gen_13_tests_docs(d)
    gen_14_protected(d)
    gen_15_safe_candidates(d)
    gen_16_manual_verification(d)
    gen_17_cleanup_plan(d)
    gen_18_regression_rollback(d)
    gen_19_final_acceptance(d)
    print("Generated all 20 CCA 1.0 markdown reports successfully.")


if __name__ == "__main__":
    main()
