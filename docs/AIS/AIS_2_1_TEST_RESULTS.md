# Agent Intelligence Studio 2.1 — Test & Build Verification Results

**Verification Integrity Guarantee:** Every command output, test count, and pass status recorded below was executed directly **after the final application and test code edit** (zero code edits occurred afterwards). External live infrastructure tests remain explicitly categorized as **`NOT VERIFIED`**.

---

## 1. Post-Final-Edit Executed Verification Matrix

| Suite / Check | Exact Command | Outcome | Observed Result | Test Environment |
| :--- | :--- | :-: | :--- | :--- |
| **Full Backend Regression Suite** | `cd backend; python -m pytest -q` | **PASSED** | **`314 passed` in `431.38s` (`0:07:11`)**, `0` failed, `0` skipped | Async SQLite `:memory:` / temp DB, loopback OpenAI `ThreadingHTTPServer` mocks, Playwright Chromium |
| **Targeted AIS 2.1 + Wire/E2E Suite** | `cd backend; python -m pytest tests/test_phase8_2_validation.py::test_stage_e_controlled_wire_scenarios tests/test_phase9_audit_and_pilot.py::test_pilot_shadow_isolation_idempotency_budgets_and_rollback tests/e2e_browser/test_phase9_ui_e2e.py tests/e2e_browser/test_phase9_1_ui_e2e.py tests/test_ais_2_1_remediation.py tests/test_policy_remediation_and_ground_truth.py -v` | **PASSED** | **`23 passed` in `99.78s` (`0:01:39`)** | Async SQLite + loopback OpenAI mock + Chromium Next.js E2E |
| **Frontend Unit Tests** | `cd frontend; node --experimental-strip-types --test tests/quality-export.test.mjs tests/admin-guide.test.mjs` | **PASSED** | **`15 passed`, `0 failed`** (`249.26ms`) | Node built-in test runner |
| **Frontend TypeScript Check** | `cd frontend; npx tsc --noEmit` | **PASSED** | Exit code `0` (`0` TypeScript errors) | Local `tsc` |
| **Frontend Production Build** | `cd frontend; npm run build` | **PASSED** | Exit code `0`, `✓ Compiled successfully in 5.6s`, `32/32` static/dynamic app routes built | Next.js `16.4.5` (Turbopack) |
| **Feature Registry Verification** | `python scripts/validate_feature_registry.py` | **PASSED** | `OK: Registry verified (44 features, 19 modules, Impl=100.0%, Verif=88.5%)` | Local script |
| **Security & IP Diff Hygiene Scan** | Custom Python regex scan across `git diff` + 3 new code/test files | **PASSED** | `Non-test IPs: []`, `Secret hits: []` | Local git workspace |

---

## 2. Acceptance Criteria Proof Mapping (`backend/tests/test_ais_2_1_remediation.py`)

All 12 acceptance criteria specified for AIS 2.1 are backed by observed passing tests (1–11 in `backend/tests/test_ais_2_1_remediation.py`, 12 across the full backend + frontend regression suites):

| AC # | Acceptance Requirement | Test Case / Suite | Observed Verified Result |
| :-: | :--- | :--- | :--- |
| **1** | Rule with 2 matching incidents returns exact `2` (`RULE_MISMATCH = 0`), not `52` | `test_1_rule_scoped_retrieval_returns_exact_two_not_52` | **PASSED** (with `60+` unrelated DB incidents present) |
| **2** | Similar rule names (`PH_RULE_HEAVY_TCP_HOST_SCAN` vs `_ON_FIXED_PORT`) never cross-contaminate | `test_2_similar_rule_names_never_cause_cross_rule_contamination` | **PASSED** (also verifies `DetectionArchetypeRegistry` classifies `_ON_FIXED_PORT` as `NETWORK_SCAN`) |
| **3** | Unlinked incidents matching an unambiguous `event_type` are included; ambiguous multi-rule `event_type` stays excluded | `test_3_unlinked_unambiguous_event_type_included_ambiguous_isolated` | **PASSED** |
| **4** | `>50` matching incidents retrieved cleanly via pagination | `test_4_paginated_retrieval_over_50_incidents` | **PASSED** (`65` matching incidents paginated without 50-row cap) |
| **5** | Valid human-reviewed labels containing `"normal"`, `"html"`, `"xml"`, `"yaml"`, `"similar"`, `"email"` are not lost to `"ml"` substring matching; bare `cleared_user` does not override automated closure | `test_5_ml_word_boundary_and_human_provenance_safeguards` | **PASSED** (covers validator, `IngestionService`, and `FortiSIEMService`) |
| **6** | Disputed, ambiguous, synthetic, or unverified labels cannot inflate G8 accuracy; optional unlabeled replay is isolated | `test_6_disputed_ambiguous_synthetic_excluded_from_g8_and_unlabeled_isolated` | **PASSED** |
| **7** | Real-provider (`OPENAI_COMPATIBLE`) simulation executes HTTP endpoint, records provider/model/policy digest/tokens/evidence trace | `test_7_and_8_real_llm_simulation_provenance_vs_simulated_blocked_from_g8` | **PASSED** (via loopback OpenAI-compatible `ThreadingHTTPServer`) |
| **8** | `SIMULATED` / mock execution cannot pass empirical G8 or calibration | `test_7_and_8_real_llm_simulation_provenance_vs_simulated_blocked_from_g8` | **PASSED** (`G8_SIMULATED_PROVIDER_NOT_CERTIFYING`, `SIMULATED_ONLY`) |
| **9** | Simulation and live triage share equivalent preflight, claim, validator, trustworthiness, and port normalization safeguards | `test_9_simulation_and_live_share_verdict_safeguards_and_port_normalization` | **PASSED** |
| **10** | Historical replay does not mutate live `Incident`, `Investigation`, or `HistoricalGroundTruth` state | `test_10_historical_replay_does_not_mutate_live_incident_state` | **PASSED** |
| **11** | Empirically unvalidated policy cannot execute autonomous actions (`BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION`), while advisory review remains available | `test_11_uncertified_policy_blocked_from_autonomous_actions_advisory_allowed` | **PASSED** |
| **12** | Existing relevant frontend & backend regression suites continue to pass | Full `pytest -q` (`314 passed`), Node frontend tests (`15 passed`), `tsc --noEmit`, `npm run build` | **PASSED** (no skipped or relaxed assertions across the 314 backend + 15 frontend tests; two superseded assertions in `test_policy_remediation_and_ground_truth.py` were updated to match the AIS 2.1 requirements) |

---

## 3. Remotely Unverified Integration Checks (`NOT VERIFIED`)

| Target Environment / Component | Status | Reason NOT VERIFIED |
| :--- | :-: | :--- |
| Live PostgreSQL Server 1 (2,900+ historical incidents, `PH_RULE_HEAVY_TCP_HOST_SCAN` production row distribution) | **`NOT VERIFIED`** | Remote DB unreachable from local Windows dev workspace (`backend/ai_verdict.db` has 26 dev incidents, 4 rules, 0 rows matching `PH_RULE_HEAVY_TCP_HOST_SCAN`). |
| Live Server 2 vLLM / Qwen3 GPU Inference Endpoint (`OPENAI_COMPATIBLE`) | **`NOT VERIFIED`** | Real HTTP client code (`OpenAICompatibleProvider`) was exercised locally against loopback `ThreadingHTTPServer` mocks, not against Server 2 GPU weights or latency characteristics. |
| Live Redis + Celery Worker (`simulation_replay` queue) | **`NOT VERIFIED`** | Celery task definition, queue route, and `dispatch_policy_simulation` in-process fallback exist and were inspected/unit-dispatched locally, but end-to-end Redis broker + separate systemd worker process execution requires staging/production Server 1. |
| Live FortiSIEM Supervisor Rule Catalog & Alert Sync | **`NOT VERIFIED`** | Network access to FortiSIEM Supervisor appliance unavailable in local test environment. |
