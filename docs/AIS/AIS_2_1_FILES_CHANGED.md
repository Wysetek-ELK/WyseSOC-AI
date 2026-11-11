# Agent Intelligence Studio 2.1 — Files Changed Inventory

**Verification Status:** Exact file list captured directly from `git diff --stat` and workspace filesystem after all final edits (`21` modified tracked files + `3` new code/test files + `6` AIS 2.1 reports = `30` files total; binary Playwright screenshot diffs under `docs/phase8*` / `docs/phase9*` from test runs were restored cleanly via `git checkout` so only intended remediation changes remain).

---

## 1. New Backend Modules & Regression Suites (`3` Code/Test Files)

| File Path | Lines | Purpose & Key Symbols |
| :--- | --: | :--- |
| `backend/app/services/policy_governance.py` | 526 | Canonical rule resolution (`resolve_canonical_rule`, `build_rule_incident_context`, `build_rule_incident_sql_filter`, `verify_incident_matches_rule`), shared snapshot-aware contract resolution (`get_rule_semantics_and_contract`), and three-tier policy certification assessment (`assess_policy_runtime_certification`, `PolicyRuntimeCertification`, `MIN_EMPIRICAL_SAMPLES`). |
| `backend/app/services/verdict_pipeline.py` | 1,001 | Shared single-incident evaluation pipeline (`run_shared_verdict_pipeline`, `VerdictPipelineResult`, `build_sanitized_model_payload`, `_invoke_provider_with_guards`, `_governance_fields`) unifying Live Triage and Simulation across fail-closed governance, preflight, RAG, token budgeting, claim validation, and trustworthiness scoring. |
| `backend/tests/test_ais_2_1_remediation.py` | 1,148 | Dedicated regression test suite covering all 11 backend acceptance criteria (AC #1–#11) across rule-scoped pagination, sibling isolation, ambiguous event-type separation, ML word-boundary preservation, dispute exclusion, real vs simulated G8 gating, live/sim pipeline parity, non-mutation, and governance enforcement. |

---

## 2. Modified Backend Application Files (`18` Files)

| File Path | Net Delta (`+`/`-`) | Summary of AIS 2.1 Changes |
| :--- | :--: | :--- |
| `backend/app/services/ai_verdict_service.py` | `744` lines changed (`+` / `-` consolidation) | Added `execution_context` & `require_autonomous_certification` parameters on `evaluate_incident` / `_evaluate_incident_locked`; replaced unsafe sibling auto-creation on ambiguous `event_type`; delegated core evaluation to `run_shared_verdict_pipeline`. |
| `backend/app/services/policy_simulation_service.py` | `1,109` lines changed | Replaced global top-50 `scanned_q` sweep with `_fetch_scoped_incidents_paginated`; wired `verify_incident_matches_rule`, `Investigation` dispute/verification join, and `adjudicate_incident_ground_truth`; skipped all excluded rows before inference; isolated optional `include_unlabeled_replay` results; routed simulated/real inference through `run_shared_verdict_pipeline`; persisted `TokenUsageRecord(process_type="POLICY_SIMULATION")`; blocked `SIMULATED` runs from `get_rule_calibration_stats` and `EVALUATED_PASSED`. |
| `backend/app/services/historical_ground_truth_validator.py` | `226` lines changed | Added `detect_automated_or_ml_text` with word-boundary `(?<![a-z0-9])ml(?![a-z0-9])` regex and `AUTOMATED_ACTOR_USERS`; removed `cleared_user` bypass on containment-only FP notes; added `adjudicate_incident_ground_truth` enforcing `Investigation.is_disputed` and distinguishing `Investigation.is_independently_verified` from automated closures. |
| `backend/app/workers/tasks.py` | `144` additions | Added `_execute_policy_simulation_core`, Celery task `run_policy_simulation_task` (`queue="simulation_replay"`), and `dispatch_policy_simulation` helper with `CELERY_ASYNC` / `IN_PROCESS_ASYNC` dispatch. |
| `backend/app/api/prompts.py` | `79` lines changed | Resolved rules canonically; added `provider_type`, `sample_limit`, `include_unlabeled_replay`, and `async_execution` parameters to `/rule/{rule_id}/evaluate-simulation`; passed `for_quality_validation=True` for G1–G8 preview; filtered simulation run history to `COMPLETED`/`FAILED` and propagated `is_simulated`/`provider_type` into G8 assessment. |
| `backend/app/services/evidence_contract_service.py` | `41` lines changed | Extended `get_contract_for_rule(..., semantics=None)` and `get_active_contract_for_rule` to honor populated `RuleIntelligenceSnapshot.semantics_payload` without breaking empty-snapshot legacy contracts. |
| `backend/app/services/evidence_normalization_service.py` | `40` lines changed | Added FortiSIEM port/protocol field mappings (`destination port`, `destinationport`, `dstport`, `dst_port`, `source port`, etc.), nested `attributes`/`event`/`events`/`rawEvents` traversal alongside top-level scalars, and `"port"` fallback heuristic. |
| `backend/app/services/prompt_studio_service.py` | `40` lines changed | Resolved rules canonically via `resolve_canonical_rule`; propagated `provider_type`, `is_simulated`, and `execution_provenance` into `approve_version` G8 `sim_results`; used `get_rule_semantics_and_contract(..., for_quality_validation=True)` in `rollback_version`. |
| `backend/app/api/verdict_intelligence.py` | `27` lines changed | Exposed `provider_type`, `is_simulated`, `sample_limit`, `include_unlabeled_replay`, and `async_execution` on `/dry-run/evaluate` and propagated simulation provenance fields cleanly. |
| `backend/app/services/pilot_service.py` | `19` lines changed | Switched unlinked incident rule resolution to `resolve_canonical_rule`, enforced `require_autonomous_certification=True` when `allow_auto_incident_closure` / `allow_external_writeback` / autonomous mode is enabled, and returned runtime governance metadata. |
| `backend/app/services/policy_quality_validator.py` | `19` additions | Added explicit hard block in `_evaluate_gate_8_simulation` rejecting `is_simulated=True` and `SIMULATED`/`MOCK`/`HEURISTIC` providers (`G8_SIMULATED_PROVIDER_NOT_CERTIFYING`) from empirical G8 points or `EVALUATED_PASSED`. |
| `backend/app/services/ingestion_service.py` | `14` lines changed | Replaced substring `"ml"` comment check with `HistoricalGroundTruthValidator.detect_automated_or_ml_text`. |
| `backend/app/services/fortisiem_service.py` | `13` lines changed | Replaced substring `"ml"`/`"ML"` check in `extract_ground_truth_data` with `HistoricalGroundTruthValidator.detect_automated_or_ml_text`. |
| `backend/app/services/evidence_sufficiency_engine.py` | `11` additions | Populated `detection.threshold` when `authoritative_threshold is not None` and added destination/source port and `security.event.type` field aliases. |
| `backend/app/schemas/verdict_intelligence.py` | `9` additions | Extended `IncidentEligibilityFunnel` (`available`, `retrieved`, `labeled`, `verified`, `inferred`, `scored`, `exploratory_replay_count`) and `HistoricalEvaluationRunRequest` (`include_unlabeled_replay`, `async_execution`). |
| `backend/app/services/detection_archetype_registry.py` | `3` lines changed | Fixed pattern `"PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT"` so fixed-port TCP host scan classifies as `NETWORK_SCAN`. |
| `backend/app/services/rule_parser.py` | `2` additions | Mapped `"pattern conditions"` section into `parsed_metadata["pattern_logic"]`. |
| `backend/app/workers/celery_app.py` | `1` addition | Added `"app.workers.tasks.run_policy_simulation_task": {"queue": "simulation_replay"}` task route. |

---

## 3. Modified Backend Tests & Frontend Files (`3` Files)

| File Path | Net Delta | Summary of Changes |
| :--- | :--: | :--- |
| `backend/tests/test_policy_remediation_and_ground_truth.py` | `13` lines changed | Updated two legacy assertions superseded by AIS 2.1 requirements: (1) strict rule-scoped simulation now excludes mismatched rows rather than pulling unrelated global incidents, and (2) ML-automated closures without `is_independently_verified` cannot rely on `cleared_user` alone. |
| `frontend/src/lib/api.ts` | `52` lines changed | Updated `PolicySimulationResult` & `IncidentEligibilityFunnel` interfaces (`available`, `retrieved`, `labeled`, `verified`, `inferred`, `scored`, `exploratory_replay_count`, `provider_type`, `is_simulated`, `execution_provenance`, `SIMULATED_ONLY_NOT_CERTIFYING`, `token_usage`) and parameterized `api.evaluatePolicySimulation(ruleId, versionId, options)`. |
| `frontend/src/app/agent-intelligence-studio/page.tsx` | `261` lines changed | Added `simulationProvider` (`OPENAI_COMPATIBLE` vs `SIMULATED`) selector in Simulation Lab, displayed all 8 eligibility funnel counts plus excluded count, rendered amber non-certifying banner for `SIMULATED_ONLY` / `is_simulated` runs, and surfaced provider/model/provenance tags without redesigning unrelated UI flows. |

---

## 4. AIS 2.1 Report Deliverables Added (`docs/AIS/`, `6` Files)

1. `docs/AIS/AIS_2_1_IMPLEMENTATION_REPORT.md`
2. `docs/AIS/AIS_2_1_FILES_CHANGED.md`
3. `docs/AIS/AIS_2_1_TEST_RESULTS.md`
4. `docs/AIS/AIS_2_1_SIMULATION_PARITY.md`
5. `docs/AIS/AIS_2_1_REMAINING_GAPS.md`
6. `docs/AIS/AIS_2_1_IMPLEMENTATION_EVIDENCE.json`
