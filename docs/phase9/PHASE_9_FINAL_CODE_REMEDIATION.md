# Phase 9 — Final Code Remediation & Defect Closure

This report summarizes code-level remediations applied during Phase 9 Stage 1 audit closure and Phase 9 development.

---

## 1. Metric Honesty & Trust Normalization Remediations

1. **`backend/app/schemas/verdict_intelligence.py`**
   - Added `historical_trust_score: Optional[int] = None`, `trust_cap_applied: bool = False`, and `trust_cap_reason: Optional[str] = None` to `VerdictTrustAssessmentResult`.
   - Made `automatic_decision_coverage` and `analyst_attention_rate` nullable (`Optional[float] = None`) on `EmpiricalAccuracyMetrics`.
   - Added `after_epoch: Optional[int] = None` and `before_epoch: Optional[int] = None` on `HistoricalEvaluationRunRequest` for time-aware historical replay.

2. **`backend/app/services/empirical_accuracy_evaluator.py`**
   - Updated `evaluate_performance()` so `verified_gt_count == 0` emits `None` (`N/A` in UI) for `automatic_decision_coverage` and `analyst_attention_rate`.

3. **`backend/app/services/verdict_trustworthiness_engine.py`**
   - Corrected `compute_trust_score()` calibration eligibility guard to require `acc_pct is not None and acc_pct >= 70.0`.
   - Added `cap_uncalibrated_trust_score(trust_score, is_calibrated)` and non-mutating `normalize_ai_verdict_dict(ai_verdict)` enforcing effective `<= 6/10` uncalibrated ordinal presentation while preserving `historical_trust_score`.

4. **`backend/app/services/incident_service.py` & `backend/app/api/verdict_intelligence.py`**
   - Applied `normalize_ai_verdict_dict()` in `list_incidents()` and `get_incident()`.
   - Updated `_sanitize_run_metrics()` in `verdict_intelligence.py` to enforce `None` when `verified_n == 0` or confusion keys are absent when `decisive == 0`, and applied sanitization inside `GET /api/verdict-intelligence/export`.
   - Normalized `average_trust_score` in `/metrics/summary` and `/metrics/rule-wise`, plus individual `trust_score` responses in `/incident/{id}/trust` and `/dry-run/runs/{id}`.

5. **`frontend/src/app/ai-triage-workbench/[id]/page.tsx` & `frontend/src/app/verdict-intelligence/page.tsx`**
   - Updated Workbench verdict header badge and Dashboard D gauge to cap uncalibrated ordinal scores at `6/10` and render `Historical stored: X/10 (pre-cap)` provenance.
   - Updated Dashboard B coverage cards to render `N/A` whenever confusion keys are missing or zero-decisive contradicts non-zero coverage.

---

## 2. Configurability & Provider Alignment

- **`backend/app/config.py`**: Added `LOCAL_LLM_CONTEXT_BUDGET: int = 4096` and `LOCAL_LLM_MAX_TOKENS: int = 512`.
- **`backend/app/services/model_provider/openai_compatible.py`**: Removed the 60s minimum timeout floor and 350-token ceiling clamp (`timeout_seconds >= 0.1`, `64 <= max_tokens <= 4096`).
- **`backend/app/services/model_provider/factory.py` & `backend/app/services/ai_verdict_service.py`**: Passed configured `LOCAL_LLM_TIMEOUT`, `LOCAL_LLM_MAX_TOKENS`, and `LOCAL_LLM_CONTEXT_BUDGET` through `VerdictTriageAgent` and `TokenBudgetService.budget_prompt()`.

---

## 3. Defects Caught & Fixed During Phase 9 Verification

| Defect ID | File & Location | Fix Applied |
|---|---|---|
| `P9-DEF-001` | `backend/app/api/pilot.py` | Changed `AuditLog.entity_type` filter to `AuditLog.resource_type` matching `AuditLog` ORM schema. |
| `P9-DEF-002` | `backend/app/services/pilot_service.py` | Snapshotted scalar fields (`pilot_id`, `pilot_version`, `inc_id`, etc.) before `try:` so `await self.db.rollback()` on offline LLM errors cannot trigger `MissingGreenlet` inside `_handle_pilot_failure`. |
| `P9-DEF-003` | `backend/app/services/historical_eligibility_service.py` & `evidence_contract_service.py` | Passed active `PromptVersion` to `EvidenceContractService.get_contract_for_rule(rule_obj, active_pv)`, defaulted `prompt_version = None`, and extracted `r.source_field` for `CanonicalEvidenceRecord`. |
| `P9-DEF-004` | `frontend/src/app/human-review-queue/page.tsx` | Changed `a.policy_version` -> `a.policy_version_number`; gated `api.getUsers()` on `user?.role === "Administrator"` to eliminate viewer/analyst 403s. |
| `P9-DEF-005` | `frontend/src/app/verdict-intelligence/page.tsx` & `AppContext.tsx` | Guarded Analyst-only fetches (`getVerdictTrustOverview`, `getRuleWiseTrustworthiness`, `listEvaluationRuns`) against `Read-Only Viewer` role and skipped unauthenticated `/api/auth/me` call on `/login` without token, achieving 0 console errors. |
| `P9-DEF-006` | `deployment/env.production.example` & `setup_server2_gpu.sh` | Removed hardcoded internal IP literals (`10.x.x.4`, `10.x.x.5`), replacing with explicit `REPLACE_WITH_*` placeholders. |
| `P9-DEF-007` | `backend/tests/e2e_browser/test_phase8_1_ui_e2e.py` & `test_phase8_2_ui_e2e.py` | Updated legacy uncalibrated trust assertions from `8/10` to capped `6/10` + historical provenance and verified `50%` coverage absence in zero-decisive Dashboard B view. |

