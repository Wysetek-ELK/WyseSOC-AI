# Verdictum AI — Master Phase Progress Tracker

## Phase Status Summary

| Phase | Title | Status | Approval Gate |
|---|---|---|---|
| **Phase 1** | **Application Foundation** | **COMPLETED & APPROVED** | User Sign-Off Confirmed |
| **Phase 2** | **SOC Investigation & Learning Management** | **COMPLETED & APPROVED** | User Sign-Off Confirmed |
| **Phase 3** | **Dry-Run Engine & Evaluation Framework** | **COMPLETED & VERIFIED** | **Ready for Review (Gate 1)** |

---

## Phase 3 Deliverables Checklist (Dry-Run Engine & Evaluation Framework)

### 1. Provider-Independent Inference Abstraction Layer
- [x] Abstract base provider `BaseModelProvider` (`get_health`, `list_models`, `analyze_incident`, `validate_response`)
- [x] Provider implementations:
  - `DisabledModelProvider`: Safe default preventing unintended network traffic or errors.
  - `SimulatedModelProvider`: Deterministic heuristic simulator for safe offline testing; all outputs strictly stamped `is_simulated = True`.
  - `OpenAICompatibleProvider`: Client prepared for private local inference server (AWS `g4dn.2xlarge` / Server 2 vLLM/Ollama); safely disconnected during Phase 3.
- [x] Strict schema validation for structured model output (`StructuredModelVerdict`):
  - Mandatory fields: `verdict` (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`), `confidence` (0.0–100.0), `reason`, `supporting_evidence`, `missing_evidence`, `analyst_questions`, `latency_ms`, `validation_status`.
  - Defensive fallback: Malformed model responses are NEVER defaulted to `FALSE_POSITIVE`; classified as `REQUIRES_ATTENTION` with `validation_status = "INVALID_SCHEMA"`.
- [x] Zero external LLM calls or managed AI services.

### 2. Dry-Run Incident Replay Pipeline
- [x] Replay configuration management (`DryRunConfig`, `POST /api/dry-run/configs`, `GET /api/dry-run/configs`)
- [x] Dataset splitting strategies to prevent evaluation leakage:
  - `ALL`: 100% of matching ingested rule incidents.
  - `CHRONOLOGICAL_70_30`: Orders by created timestamp, reserves most recent 30% for holdout dry-run evaluation.
  - `GROUP_AWARE_HOST`: Groups incidents by reporting device/host to prevent co-occurring telemetry contamination.
- [x] Ground-truth isolation guard: Model payloads strictly constructed from allowlist (`ModelFacingIncidentPayload`); historical resolution, comments, and closure metadata are completely omitted.
- [x] Asynchronous execution queue & job tracking (`DryRunJob`, `DryRunResult`, `POST /api/dry-run/trigger`, `GET /api/dry-run/jobs`, `GET /api/dry-run/jobs/{id}/results`).
- [x] Simulation status watermark & audit trail (`is_simulated = True` persisted across all results).

### 3. Model Evaluation & Statistical Accuracy Measurement
- [x] Comprehensive mathematical metric evaluation (`GET /api/evaluations/job/{id}/metrics`):
  - **Verdict Accuracy**: $\frac{TP_{agree} + FP_{agree}}{Resolved\ Predictions} \times 100\%$
  - **TP Precision**: $\frac{TP_{agree}}{Predicted\ TP} \times 100\%$
  - **TP Recall**: $\frac{TP_{agree}}{Actual\ TP} \times 100\%$
  - **FP Precision**: $\frac{FP_{agree}}{Predicted\ FP} \times 100\%$
  - **FP Recall**: $\frac{FP_{agree}}{Actual\ FP} \times 100\%$
  - **F1 Score**: $2 \times \frac{Precision \times Recall}{Precision + Recall}$
  - **Abstention Coverage**: $\frac{Resolved\ Predictions}{Total\ Evaluated} \times 100\%$
  - **Zero-denominator resilience**: Robust `_safe_divide` helper prevents divide-by-zero crashes.
- [x] 2x3 Confusion matrix breakdown:
  - Actual TP vs Pred TP, Pred FP (severe false negative), Pred Abstain (triage queue).
  - Actual FP vs Pred FP, Pred TP (false alarm), Pred Abstain (triage queue).
- [x] Prompt version performance comparison (`GET /api/evaluations/prompt-comparison/{rule_id}`).
- [x] Benchmark report exports:
  - Direct CSV download (`GET /api/evaluations/job/{id}/export/csv`).
  - Direct JSON download (`GET /api/evaluations/job/{id}/export/json`).

### 4. Rule Automation Readiness Maturity Dashboard
- [x] 5-Tier conservative maturity lifecycle (`RuleMaturityEvaluation` table):
  1. `NOT_TESTED`: Initial state for newly ingested detection rules.
  2. `LEARNING`: Knowledge base and prompt versions under development.
  3. `UNDER_EVALUATION`: Initial dry-run replay results below automation thresholds.
  4. `CANDIDATE_FOR_AUTOMATION`: Automatically qualified when dry-run replay achieves:
     - Precision $\ge 95\%$
     - Recall $\ge 90\%$
     - Coverage $\ge 80\%$
     - Sample Size $N \ge 5$
  5. `APPROVED_FOR_AUTOMATION`: **MANDATORY HUMAN GATEWAY**. Rules NEVER auto-promote to production automation. Requires explicit sign-off by a SOC Administrator with documented audit justification (`POST /api/evaluations/rule-maturity/{rule_id}/approve`).
- [x] Automatic downgrade safety: If subsequent dry-run precision drops below 90%, automation approval is automatically revoked back to `UNDER_EVALUATION`.
- [x] RBAC enforcement: Analysts and Read-Only Viewers are strictly blocked (HTTP 403) from approving rules.

### 5. UI/UX Implementation
- [x] `/dry-run`: Interactive Dry-Run Replay Console:
  - Configuration panel with rule selector, provider type, split strategy, sample limits.
  - Prominent amber simulation warning banner with `is_simulated = True` indicators.
  - Real-time job launcher and execution progress.
  - Job history table and per-incident result inspector (ground truth comparison, agreement status, latency, reasoning).
- [x] `/evaluation-reports`: Comprehensive Statistical Evaluation Dashboard:
  - Top KPI cards (Accuracy, TP Precision/Recall, FP Precision/Recall, F1 Score, Coverage).
  - Interactive 2x3 Confusion Matrix grid with color-coded decision classifications.
  - Rule Automation Readiness table with 5-tier maturity badges.
  - Administrator Sign-Off Modal with mandatory audit notes and requirement checklist.
  - Rule Prompt version comparison matrix.
  - CSV and JSON export buttons.
- [x] Updated `Sidebar.tsx`: Promoted Dry-Run Testing and Evaluation Reports to live top-level navigation items.

### 6. Database Persistence & Migrations
- [x] Alembic migration `003_phase3_dryrun_and_evaluation.py` applied cleanly.
- [x] Tables created with relational constraints and indexes:
  - `dry_run_configs`
  - `dry_run_jobs`
  - `dry_run_results`
  - `rule_maturity_evaluations`

### 7. Automated Test Verification
- [x] Pytest suite: **33/33 tests passing (100% green)**:
  - `test_model_provider.py`: Disabled provider, simulated provider heuristic, schema validation.
  - `test_dry_run_replay.py`: Dataset splitting, batch execution, result persistence, ground-truth isolation.
  - `test_evaluation_metrics.py`: Mathematical accuracy, confusion matrix, zero-denominator safety, CSV/JSON export.
  - `test_rule_maturity.py`: State transitions, candidate qualification, RBAC admin approval gate.
- [x] Next.js 16 production build: **15/15 routes compiled with ZERO TypeScript or linting errors**.

---

## Phase 2 Deliverables (Approved Baseline)
- [x] Analyst Attention Queue & Investigation Console (`/analyst-attention`)
- [x] Investigation Q&A threads & evidence attachment
- [x] Dual-verdict recording with ground-truth isolation
- [x] Rule Prompt Studio with deterministic template prompt synthesizer (`/prompt-studio`)
- [x] Learning History & Knowledge Base with deterministic similar case matcher (`/learning-history`)
- [x] Alembic migration `002_phase2_investigation_and_learning.py`

---

## Phase 1 Deliverables (Approved Baseline)
- [x] Enterprise SOC UI with Dark Mode, Collapsible Sidebar, Global Search
- [x] RBAC Authentication with HttpOnly cookies & JWT fallback
- [x] Telemetry ingestion engine (ZIP/JSON, path traversal guard, decompression bomb limits)
- [x] Ingested 20 historical incident JSONs & 2 SIEM rules from real fixtures
- [x] Incident Explorer with Raw JSON viewer, normalized evidence, and blind-review mode
- [x] Ground-truth isolation layer with strict model-facing allowlist
