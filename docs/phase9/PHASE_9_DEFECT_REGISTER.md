# Phase 9 — Defect Register

This register tracks all defects discovered during Phase 9 Stage 1 final audit and Phase 9 SOC Pilot development/testing, together with verification status.

---

## Defect Table

| Defect ID | Severity | Component / Path | Summary & Root Cause | Remediation | Status |
|---|---|---|---|---|---|
| `P9-DEF-001` (Issue 1) | High | `backend/app/api/verdict_intelligence.py`, `empirical_accuracy_evaluator.py`, `frontend/src/app/verdict-intelligence/page.tsx` | Legacy/partial historical evaluation runs lacking confusion matrix keys displayed `50%` automatic decision coverage alongside `Decisive = 0`; `/export` bypassed sanitization; `evaluate_performance([])` emitted `0.0` instead of `None`. | Extended `_sanitize_run_metrics()`, applied inside `/export`, returned `None` when `verified_gt_count == 0`, added UI `hasConfusion` / zero-decisive guard in Dashboard B. | **REMEDIATED & VERIFIED** (`test_issue1_*` + `test_phase9_ui_e2e.py` + `test_phase8_2_ui_e2e.py`) |
| `P9-DEF-002` (Issue 2) | High | `backend/app/services/verdict_trustworthiness_engine.py`, `incident_service.py`, `api/verdict_intelligence.py`, `ai-triage-workbench/[id]/page.tsx`, `verdict-intelligence/page.tsx` | Uncalibrated historical verdicts displayed `Trust: 8/10`; `compute_trust_score` treated `historical_accuracy=None` as calibrated when `sample_size >= 30`; summary/rule averages used uncapped raw scores. | Fixed `acc_pct is not None and acc_pct >= 70.0` guard; added non-mutating `cap_uncalibrated_trust_score()` and `normalize_ai_verdict_dict()` preserving `historical_trust_score`; normalized API & UI displays to `<= 6/10`. | **REMEDIATED & VERIFIED** (`test_issue2_*` + `test_phase9_ui_e2e.py` + `test_phase8_1_ui_e2e.py` + `test_phase8_2_ui_e2e.py`) |
| `P9-DEF-003` | Medium | `backend/app/services/model_provider/openai_compatible.py`, `factory.py`, `ai_verdict_service.py` | Timeout was clamped `>= 60.0s` and `max_tokens` was clamped `<= 350`, ignoring operator configuration and prompt budget settings. | Removed hardcoded clamps (`timeout >= 0.1s`, `64 <= max_tokens <= 4096`) and wired `LOCAL_LLM_CONTEXT_BUDGET` & `LOCAL_LLM_MAX_TOKENS` from `config.py`. | **REMEDIATED & VERIFIED** (`test_openai_compatible_provider_honors_configurable_timeout_and_max_tokens`) |
| `P9-DEF-004` | High | `backend/app/api/pilot.py` | Pilot audit query referenced `AuditLog.entity_type`, whereas ORM column is `AuditLog.resource_type`. | Fixed query filter to `AuditLog.resource_type.in_(...)`. | **REMEDIATED & VERIFIED** (`test_pilot_shadow_isolation_idempotency_budgets_and_rollback`) |
| `P9-DEF-005` | High | `backend/app/services/pilot_service.py` | Accessing `cfg.id` / `inc.incident_id` after `await self.db.rollback()` inside `_handle_pilot_failure` caused SQLAlchemy `MissingGreenlet` lazy-load failure when Server 2 went offline during `LIVE` triage. | Snapshotted scalar fields before entering `try:` and passed primitives directly to `_handle_pilot_failure`. | **REMEDIATED & VERIFIED** (`test_live_source_blocks_mock_fallback_and_auto_pauses`) |
| `P9-DEF-006` | Medium | `backend/app/services/historical_eligibility_service.py`, `evidence_contract_service.py` | Missing second `prompt_version` argument on `get_contract_for_rule()`, and referenced `.field` instead of `CanonicalEvidenceRecord.source_field`. | Passed resolved `PromptVersion`, added default `None`, and used `r.source_field` filtered by `availability == "AVAILABLE"`. | **REMEDIATED & VERIFIED** (`test_historical_eligibility_report_and_chronological_replay`) |
| `P9-DEF-007` | Low | `frontend/src/app/human-review-queue/page.tsx`, `verdict-intelligence/page.tsx`, `AppContext.tsx` | Spurious Chromium console errors during Viewer/Analyst sessions (`401` on `/login` `/api/auth/me`, `403` on Admin `/api/users` and Analyst `/verdict-intelligence/metrics/*`) plus TypeScript property mismatch `a.policy_version`. | Fixed `a.policy_version_number`, gated role-specific client fetches on `user?.role`, and skipped unauthenticated `/me` check on `/login` when no token stored. | **REMEDIATED & VERIFIED** (`test_phase9_ui_e2e.py`: `0` console errors) |
| `P9-DEF-008` | Medium | `deployment/env.production.example`, `deployment/scripts/setup_server2_gpu.sh` | Hardcoded internal RFC1918 IP examples (`10.x.x.4`, `10.x.x.5`). | Replaced with explicit environment variables / `REPLACE_WITH_*` placeholders. | **REMEDIATED & VERIFIED** (`deployment_static_validation.json` & `phase9_security_scan.json`) |

---

## Known Open Constraints (External / Operational)

No open code defects remain in offline scope. Six historical criteria and three new Phase 9 external-infrastructure criteria remain `NOT_TESTED` / `BLOCKED` pending real Server 1/Server 2/FortiSIEM provisioning (see [PHASE_9_REMAINING_WORK.md](./PHASE_9_REMAINING_WORK.md)).

