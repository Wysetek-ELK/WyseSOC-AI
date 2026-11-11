# Phase 9 — Backend Unit, Integration & API Verification Report

**Full Backend Suite Log:** `docs/phase9/evidence/backend/pytest_backend_full_report.txt`  
**Structured Summary:** `docs/phase9/evidence/test-results/phase9_backend_test_summary.json`

---

## 1. Phase 9 Dedicated Backend Test Suite (`backend/tests/test_phase9_audit_and_pilot.py`)

| Test Case | Requirement / Check Covered | Status |
|---|---|---|
| `test_issue1_decision_coverage_legacy_and_zero_denominator_sanitized` | `EmpiricalAccuracyEvaluator` (`N=0` -> `None`), legacy 50% run sanitization on `/dry-run/runs`, `/dry-run/runs/{id}`, and `/export`, plus zero-decisive `0.0` enforcement | **PASSED** |
| `test_issue2_uncalibrated_trust_capped_with_historical_provenance` | `acc=None` non-calibrated boundary guard, non-mutating cap `8 -> 6` preserving `historical_trust_score=8` on `/incidents/{id}`, `/incident/{id}/trust`, `/metrics/summary`, `/metrics/rule-wise`, `/dry-run/runs/{id}` | **PASSED** |
| `test_pilot_default_disabled_safety_blocks_and_rbac` | Default `DISABLED` mode, `422` block on `allow_external_writeback` / `allow_auto_incident_closure`, 3-role RBAC (`403` viewer/analyst vs `200` admin), `DISABLED` batch skip | **PASSED** |
| `test_pilot_shadow_isolation_idempotency_budgets_and_rollback` | Rule/severity scope filters, hourly budget cap, `SHADOW` isolation (`Incident.ai_verdict` untouched), `IDEMPOTENT_SKIP`, config rollback, bifurcated tokens & `NOT_CALCULABLE` empirical state | **PASSED** |
| `test_live_source_blocks_mock_fallback_and_auto_pauses` | `source_type=LIVE` ignores `allow_simulated=true`, fails closed (`SERVER2_OFFLINE`) on unreachable Server 2, auto-pauses at consecutive error threshold | **PASSED** |
| `test_analyst_assisted_assurance_override_and_supervisor_gate` | Human Review Queue `ai_assurance`, non-destructive analyst override (`OVERRIDDEN`), `SELF_VERIFICATION_PROHIBITED` (`400`) on self-verify, independent supervisor `200` approval | **PASSED** |
| `test_historical_eligibility_report_and_chronological_replay` | `GET /eligibility-report` (JSON & CSV), `INSUFFICIENT_DATA` honesty, chronological `after_epoch` replay filter | **PASSED** |
| `test_openai_compatible_provider_honors_configurable_timeout_and_max_tokens` | Verifies custom `timeout_seconds=12.5` and `max_tokens=1024` without old 60s/350 clamps | **PASSED** |
| `test_smoke_test_server2_live_mock_and_unreachable_honesty` | Executes `smoke_test_server2.py` against local HTTP OpenAI mock (`exit 0`, `PASSED`) and unreachable endpoint (`exit 2`, `NOT_EXECUTED`) | **PASSED** |
| `test_alembic_008_soc_pilot_upgrade_and_downgrade` | Verifies `alembic upgrade 008_soc_pilot` creates `pilot_configurations`, `pilot_config_history`, `pilot_evaluations` and `downgrade 007_distributed_locks` removes them cleanly | **PASSED** |

---

## 2. Full Non-Browser Backend Regression Suite (`54` Test Files)

- **Command:** `cd backend && pytest -v --ignore=tests/e2e_browser --tb=short`
- **Result Summary:** `293 passed, 6072 warnings in 310.19s (0:05:10)` — **0 failed, 0 skipped**.
- Covers AIS 2.0/2.1 (`11` tests), Verdict Intelligence validation (`43` + `11` tests), Audit Remediations (`11` tests), FortiSIEM pull/sync (`22` tests), Evidence contracts/grounding/normalization/preflight (`36` tests), Security/Auth/ZIP/RBAC (`23` tests), Migrations & Postgres pooling (`6` tests), Model provider/LLM config/token budgeting (`22` tests), Feature Registry (`1` test), and Phase 9 Audit & Pilot (`10` tests).

