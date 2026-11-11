# Agent Intelligence Studio 2.2 — Remaining Gaps, Operational Notes & Verification Boundaries

---

## 1. Integration Validation Phase Prerequisites (`NOT VERIFIED` Locally)

Because local tests use async SQLite, dev `backend/ai_verdict.db`, and loopback HTTP mocks, the following items are **NOT VERIFIED** until executed in the staging/production integration environment:

1. **Production PostgreSQL Server 1 Corpus Audit (`AIS-F13`):**
   - Execute `python backend/scripts/audit_ground_truth_readiness.py` against read-only PostgreSQL Server 1 to obtain exact verified TP/FP, `HEURISTIC_OR_ML_LABEL`, `DISPUTED_LABEL`, and `false_positive_ml_candidates` counts for all 34 SIEM rules (specifically `PH_RULE_HEAVY_TCP_HOST_SCAN` `9839fa49-40ac-4676-abcc-4c5581ae9e09` vs `_ON_FIXED_PORT`).
   - Run an approved, `AuditLog`-backed backfill ONLY after reviewing `false_positive_ml_candidates` that carry independent verification (`RECLASSIFY_FALSE_SUBSTRING_HUMAN_VERIFIED`).
2. **Server 2 `LOCAL_LLM_CONTEXT_BUDGET` Sizing Observation:**
   - **Verified Local Finding:** Generating a full 9-section policy draft via `PolicyGenerationService` (`ENTERPRISE_SOC_BASELINE_V2`, ~`2,340` prompt tokens) pushes minimal network-scan prompt + telemetry payloads to ~`3,764` tokens, which trips `TokenBudgetService` fail-closed `CONTEXT_WINDOW_EXCEEDED` when `LOCAL_LLM_CONTEXT_BUDGET` remains at default `4096` (`available_prompt_budget = 3584`).
   - **Action Required in Integration/Production Validation:** Confirm Server 2 vLLM `max_model_len` and set `LOCAL_LLM_CONTEXT_BUDGET >= 8192` in deployment environment config before running real-LLM G8 certification across newly generated policies.
3. **Live Server 2 Real LLM Certification & Redis/Celery (`simulation_replay`):**
   - Trigger asynchronous `OPENAI_COMPATIBLE` G8 simulation on `PH_RULE_HEAVY_TCP_HOST_SCAN` once `>= 5` verified cases are confirmed, verifying Redis/Celery worker execution, GPU slot concurrency, and empirical metrics (`balanced_accuracy >= 0.80`, `critical_false_negatives == 0`).
4. **Live FortiSIEM Supervisor Rule Catalog Ingestion:**
   - Pull authoritative XML/REST rules for rules currently in `INCOMPLETE` state (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`, `PH_RULE_HEAVY_TCP_HOST_SCAN`) and confirm `/api/prompts/rule/{id}/intelligence` and G1 reflect true correlation thresholds cleanly.

---

## 2. Intentionally Deferred P3 Architectural Hygiene (`AIS-F11`, `AIS-F12`)

Per task constraints (*"Do not rewrite functioning components"* and *"No unrelated legacy-engine refactoring"*), two P3 architectural cleanup items from `AIS_REMEDIATION_PLAN.md` remain intentionally untouched outside AIS 2.2 scope:

| Finding ID | Priority | Current State | Recommended Timing |
| :--- | :-: | :--- | :--- |
| **`AIS-F11`** | **P3** | Legacy `DryRunService` (`dry_run_service.py`) and `RuleMaturityService` remain alongside the canonical AIS 2.1/2.2 `PolicySimulationService` + `policy_governance.py` path (which already serves `/api/prompts/.../evaluate-simulation` and `/api/verdict-intelligence/dry-run/evaluate`). | Deprecate legacy `/api/dry-run` routes once legacy callers migrate. |
| **`AIS-F12`** | **P3** | `backend/app/services/llm_config_service.py` in-place `.env` rewriting still appends comment blocks in local dev `.env`; local dev `.env` retains `FORTISIEM_MOCK_FALLBACK=true` / `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true` while `deployment/env.production.example` enforces `false`. Also `PolicyQualityAssessmentResponse` maintains backward-compatible `validation_status` + `empirical_validation_status` fields intentionally. | Clean up `llm_config_service.py` `.env` updater in P3 maintenance; verify production `.env` prior to go-live. |

---

## 3. Application Readiness Verdict

- **Codebase & Local Regression Readiness:** **READY FOR INTEGRATION VALIDATION** — All AIS 2.1 P0/P1 safeguards and AIS 2.2 P2 remediations (`AIS-F05`, `AIS-F06`, `AIS-F07`, G1/FortiSIEM integrity, read-only ground-truth readiness diagnostics) are implemented, verified locally (`320/320` backend tests, `16/16` frontend unit tests, `tsc --noEmit`, Next.js `32/32` build), and non-mutating.
- **Production Readiness Status:** **NOT CLAIMED / BLOCKED ON INTEGRATION VALIDATION** until Server 1 PostgreSQL readiness audit, Server 2 context budget (`>= 8192`) + live Qwen G8 certification, and live Redis/FortiSIEM checks complete cleanly remotely.
