# 04 — Backend Dead Code & Architecture Audit

## 1. Compatibility Alias Shims (0 Production Importers)
11 thin re-export modules (11–18 lines each, 143 lines total) exist solely to alias legacy service names to "Agentic SOC" names. They have **0 production callers** and are imported exclusively by `backend/tests/test_agentic_nomenclature.py`:

| File | Lines | Test Importers | Classification | Recommended Action |
|---|---:|---:|---|---|
| `backend/app/services/agent_memory_engine.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/agent_policy_engine.py` | 12 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/detection_context_engine.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/evidence_integrity_guardrail.py` | 18 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/inference_health_monitor.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/review_orchestrator.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/sentinel_ingest_worker.py` | 18 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/validation_engine.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/verdict_evaluation_engine.py` | 11 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/services/verdict_triage_agent.py` | 12 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |
| `backend/app/utils/payload_sanitization_guard.py` | 18 | 1 | `REQUIRED_COMPATIBILITY` | `VERIFY_FIRST` |

## 2. Unused Service Methods in Production (20 Total: 7 Confirmed Dead, 13 Test-Only)

| Location | Method | Lines | Test Hits | Script Hits | Classification | Action |
|---|---|---:|---:|---:|---|---|
| `backend/app/services/ais_evaluation_service.py:1096` | `AisEvaluationService.get_missing_inference_candidates` | 22 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/audit_service.py:94` | `AuditService.verify_audit_integrity` | 31 | 2 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/calibration_evaluation_service.py:31` | `CalibrationEvaluationService.assign_dataset_partition` | 21 | 3 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/detection_archetype_registry.py:649` | `DetectionArchetypeRegistry.list_archetypes` | 3 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/empirical_benchmark_harness.py:785` | `EmpiricalBenchmarkHarness.load_certified_ground_truth_cohort` | 132 | 2 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/empirical_benchmark_harness.py:2193` | `EmpiricalBenchmarkHarness.run_three_mode_benchmark` | 100 | 2 | 1 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/evidence_compaction_service.py:523` | `EvidenceCompactionService.chunk_oversized_evidence` | 18 | 1 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/evidence_sufficiency_engine.py:324` | `EvidenceSufficiencyEngine.evaluate_sufficiency` | 17 | 6 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/fortisiem_service.py:596` | `FortiSIEMService.pull_incidents_for_rule` | 70 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/gpu_manager.py:140` | `GPUWorkloadManager.check_backpressure` | 3 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/incident_service.py:529` | `IncidentService.get_model_facing_payload` | 11 | 1 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/independent_verdict_validator.py:1068` | `IndependentVerdictValidator.replay_validation` | 48 | 4 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/policy_governance.py:87` | `PolicyRuntimeCertification.to_dict` | 18 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/policy_lifecycle_monitor.py:152` | `PolicyLifecycleMonitor.acknowledge_drift` | 20 | 1 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/rule_intelligence_analyzer.py:408` | `RuleIntelligenceAnalyzer._extract_window_from_conditions` | 2 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/runtime_config_service.py:286` | `RuntimeConfigValidator.enforce_fail_closed` | 10 | 1 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/token_analytics_service.py:23` | `TokenAnalyticsService.record_token_usage` | 36 | 3 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/token_budget_service.py:88` | `TokenBudgetService.get_token_accounting` | 24 | 0 | 0 | `CONFIRMED_UNUSED` | `REMOVE` |
| `backend/app/services/verdict_claim_validator.py:354` | `VerdictClaimValidator.validate_claims` | 16 | 4 | 0 | `TEST_ONLY` | `RETAIN` |
| `backend/app/services/verdict_guardrails_engine.py:265` | `VerdictGuardrailsEngine.evaluate_guardrails` | 23 | 5 | 0 | `TEST_ONLY` | `RETAIN` |

## 3. Unused Top-Level Symbols & Pydantic Schemas
- `backend/app/schemas/canonical_evidence.py:7` — `EvidenceLifecycleStage` (13L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- `backend/app/schemas/dashboard.py:18` — `StatusCount` (3L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- `backend/app/services/blind_review_guard.py:519` — `get_blind_mask_response_marker` (2L, 0 prod/test refs) -> `CONFIRMED_UNUSED`
- Unused schema classes (0 prod refs outside `schemas/__init__.py`, 0 test refs): `TokenPayload` (`auth.py`), `LearningRecordCreate` (`learning.py`), `PromptDraftGenerateRequest` (`prompt.py`), `RuleCreate` (`rule.py`).

## 4. Unused Imports Across `backend/app/` (309 Total)

| File | Unused Imports |
|---|---:|
| `backend/app/services/policy_simulation_service.py` | 14 |
| `backend/app/api/verdict_intelligence.py` | 10 |
| `backend/app/services/empirical_benchmark_harness.py` | 10 |
| `backend/app/api/incidents.py` | 9 |
| `backend/app/api/prompts.py` | 9 |
| `backend/app/services/ai_verdict_service.py` | 7 |
| `backend/app/services/ais_evaluation_service.py` | 7 |
| `backend/app/services/bulk_quality_audit_service.py` | 7 |
| `backend/app/api/evaluations.py` | 6 |
| `backend/app/services/dry_run_service.py` | 6 |
| `backend/app/services/evaluation_service.py` | 6 |
| `backend/app/services/investigation_service.py` | 6 |
| `backend/app/services/pilot_service.py` | 6 |
| `backend/app/services/production_readiness_service.py` | 6 |
| `backend/app/services/learning_service.py` | 5 |
| `backend/app/services/maturity_service.py` | 5 |
| `backend/app/services/policy_lifecycle_monitor.py` | 5 |
| `backend/app/services/prompt_studio_service.py` | 5 |
| `backend/app/api/dry_run.py` | 4 |
| `backend/app/api/rule_learning.py` | 4 |
| `backend/app/main.py` | 4 |
| `backend/app/scripts/migrate_sqlite_to_postgres.py` | 4 |
| `backend/app/services/ground_truth_certification_service.py` | 4 |
| `backend/app/services/policy_eligibility_service.py` | 4 |
| `backend/app/services/policy_version_governance_service.py` | 4 |
| `backend/app/services/verdict_trustworthiness_engine.py` | 4 |
| `backend/app/workers/tasks.py` | 4 |
| `backend/app/api/fortisiem.py` | 3 |
| `backend/app/api/health.py` | 3 |
| `backend/app/api/investigations.py` | 3 |
| `backend/app/api/rules.py` | 3 |
| `backend/app/cli.py` | 3 |
| `backend/app/models/investigation.py` | 3 |
| `backend/app/scripts/backup.py` | 3 |
| `backend/app/services/actual_prompt_capture_service.py` | 3 |
| `backend/app/services/calibration_evaluation_service.py` | 3 |
| `backend/app/services/dashboard_service.py` | 3 |
| `backend/app/services/evidence_contract_service.py` | 3 |
| `backend/app/services/evidence_preflight_validator.py` | 3 |
| `backend/app/services/evidence_requirement_mapper.py` | 3 |

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
