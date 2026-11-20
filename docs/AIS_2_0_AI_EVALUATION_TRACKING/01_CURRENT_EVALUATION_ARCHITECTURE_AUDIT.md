# Phase 1: Current Evaluation Architecture Audit & Findings

## 1. Executive Summary
Agent Intelligence Studio 2.0 (AIS 2.0) requires deterministic, incident-level tracking of AI evaluation status. Prior to this implementation, the system lacked a unified status resolver: the UI relied on fragmented heuristic queries across `analyst_verdict_reviews`, `investigations`, `pilot_verdicts`, and `dry_run_results`. 

This audit analyzes the underlying database schema, inference pipelines, and validator services to establish an authoritative single source of truth for AI evaluations.

---

## 2. Component Inventory & Audit

### 2.1 Services & Engines
1. **`AisEvaluationService` (New Canonical Status Resolver):**
   - Path: `backend/app/services/ais_evaluation_service.py`
   - Purpose: Centralized determination of incident evaluation status, status history, batch evaluation management, and empirical accuracy summary.
2. **`VerdictPipeline` & `AIVerdictService`:**
   - Path: `backend/app/services/ai_verdict_service.py`
   - Purpose: Executes inference against the Local LLM, manages deterministic evidence validation, and records verdict outcomes in `pilot_verdicts` and `investigations`.
   - Update: Added `target_version_id` and `target_version_number` parameters to enforce strict policy version pinning.
3. **`IndependentVerdictValidator` & `ReasoningIntegrityEngine`:**
   - Purpose: Deterministic validation of raw LLM outputs (format, grounding, evidence references). If validation fails, safely converts effective verdict to `REQUIRES_ATTENTION`.
4. **`AnalystVerdictReview` & `AnalystReviewService`:**
   - Purpose: Stores independent analyst ground-truth reviews (`is_fp`, `is_tp`, `notes`, `rule_uuid`, `incident_id`).
5. **Prompt Capture Engine (`ActualLLMPromptCapture`):**
   - Purpose: Full raw input and output capture (compiled prompt, system prompt, raw response, tokens, sha256).

### 2.2 Database Table Schema Mapping

| Table Name | Role in Evaluation Tracking | Authoritative Source For |
|---|---|---|
| `incidents` | Primary incident identity | `incident_id`, `rule_id`, `tenant_id`, `first_seen_time` |
| `pilot_verdicts` | Live & retrospective inference records | `verdict`, `status`, `is_simulated`, `policy_version_id`, `policy_version_number`, `evidence_grounding_score`, `raw_response` |
| `investigations` | Dispatch and lifecycle tracking | `dispatch_status` (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`), error messages |
| `actual_llm_prompt_captures` | Forensic audit log | Exact compiled prompt text, raw LLM token outputs, timestamps |
| `analyst_verdict_reviews` | Ground-truth benchmark | Analyst verdict (`FP`, `TP`), analyst identity, review timestamp |
| `dry_run_results` | Batch simulation storage | Rule optimization runs (non-authoritative for live incident inference) |

---

## 3. Authoritative Source of Truth Formulation

A qualifying real AI evaluation requires:
1. An execution record in `pilot_verdicts` or `investigations`.
2. `is_simulated == False` (simulations/mocks are excluded from decisive production stats).
3. `dispatch_status == 'COMPLETED'`.
4. Stored `response_raw` or validated `verdict`.
5. Exact match with the target `policy_version_number` (or `policy_version_id`).

### Relationship Definition:
`Incident` $\rightarrow$ `Inference Execution` $\rightarrow$ `Raw Model Output` $\rightarrow$ `Validator Result` $\rightarrow$ `Effective Verdict` $\rightarrow$ `Policy Version` $\rightarrow$ `Ground-Truth Comparison`

---

## 4. Schema Gaps & Resolutions
- **Gap:** Pre-existing records often left `policy_version_number` NULL when created through legacy triage.
- **Resolution:** Centralized resolver joins with `prompt_versions` via `prompt_version_id` or `policy_version_id` to reliably resolve version numbers.
- **Gap:** Inability to run retrospective inference on older incidents with explicit policy pinning.
- **Resolution:** Added `evaluate_missing_batch` API supporting `RETROSPECTIVE_EVALUATION` execution provenance, scoped concurrency, and background execution.
