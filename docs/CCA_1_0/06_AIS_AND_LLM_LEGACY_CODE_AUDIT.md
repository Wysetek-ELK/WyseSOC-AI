# 06 — Agent Intelligence Studio & AI Engine Legacy Code Audit

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
| `ai_verdict_service.py` | 730 | 14 | 16 | ais_evaluation.py, fortisiem.py, health.py, incidents.py, prompts.py |
| `verdict_pipeline.py` | 1,381 | 3 | 6 | ai_verdict_service.py, dry_run_service.py, policy_simulation_service.py |
| `prompt_studio_service.py` | 984 | 9 | 6 | incidents.py, prompts.py, rules.py, agent_policy_engine.py, ai_verdict_service.py |
| `policy_compiler_service.py` | 432 | 6 | 12 | prompts.py, actual_prompt_capture_service.py, ais27_benchmark_runner.py, empirical_benchmark_harness.py, prompt_studio_service.py |
| `policy_generation_service.py` | 370 | 1 | 5 | prompt_studio_service.py |
| `policy_simulation_service.py` | 1,492 | 6 | 9 | prompts.py, verdict_intelligence.py, ai_verdict_service.py, dry_run_service.py, integration_diagnostic_service.py |
| `policy_quality_validator.py` | 885 | 10 | 8 | prompts.py, bulk_quality_audit_service.py, dry_run_service.py, integration_diagnostic_service.py, pilot_service.py |
| `policy_governance.py` | 532 | 15 | 4 | prompts.py, verdict_intelligence.py, ai_verdict_service.py, dry_run_service.py, evaluation_service.py |
| `policy_version_governance_service.py` | 658 | 2 | 1 | prompts.py, prompt_studio_service.py |
| `policy_eligibility_service.py` | 242 | 3 | 1 | prompts.py, prompt_studio_service.py, verdict_pipeline.py |
| `policy_lifecycle_monitor.py` | 171 | 3 | 1 | prompts.py, fortisiem_service.py, learning_service.py |
| `historical_eligibility_service.py` | 569 | 3 | 2 | pilot.py, verdict_intelligence.py, integration_diagnostic_service.py |
| `historical_ground_truth_validator.py` | 531 | 13 | 11 | prompts.py, ais27_benchmark_runner.py, ais_evaluation_service.py, dry_run_service.py, empirical_benchmark_harness.py |
| `ground_truth_certification_service.py` | 1,430 | 2 | 1 | ground_truth.py, main.py |
| `independent_verdict_validator.py` | 1,115 | 3 | 18 | ais27_benchmark_runner.py, empirical_benchmark_harness.py, verdict_pipeline.py |
| `verdict_claim_validator.py` | 369 | 2 | 3 | policy_simulation_service.py, verdict_trustworthiness_engine.py |
| `verdict_guardrails_engine.py` | 287 | 3 | 3 | empirical_benchmark_harness.py, policy_simulation_service.py, verdict_trustworthiness_engine.py |
| `verdict_trustworthiness_engine.py` | 480 | 9 | 4 | pilot.py, verdict_intelligence.py, ais27_benchmark_runner.py, empirical_benchmark_harness.py, incident_service.py |
| `reasoning_integrity_engine.py` | 732 | 1 | 1 | independent_verdict_validator.py |
| `model_claim_extractor.py` | 539 | 4 | 14 | ais27_benchmark_runner.py, empirical_benchmark_harness.py, independent_verdict_validator.py, verdict_pipeline.py |
| `model_payload_allowlist.py` | 221 | 8 | 8 | incidents.py, ai_verdict_service.py, ais27_benchmark_runner.py, empirical_benchmark_harness.py, evidence_integrity_guardrail.py |
| `evidence_normalization_service.py` | 951 | 8 | 12 | incidents.py, ais27_benchmark_runner.py, analyst_review_service.py, empirical_benchmark_harness.py, ground_truth_certification_service.py |
| `evidence_contract_service.py` | 153 | 5 | 3 | verdict_intelligence.py, historical_eligibility_service.py, policy_governance.py, policy_simulation_service.py, verdict_pipeline.py |
| `evidence_preflight_validator.py` | 200 | 4 | 16 | ais27_benchmark_runner.py, empirical_benchmark_harness.py, independent_verdict_validator.py, verdict_pipeline.py |
| `evidence_sufficiency_engine.py` | 340 | 3 | 3 | verdict_intelligence.py, policy_simulation_service.py, verdict_trustworthiness_engine.py |
| `evidence_requirement_mapper.py` | 322 | 6 | 7 | prompts.py, bulk_quality_audit_service.py, evidence_contract_service.py, policy_generation_service.py, policy_quality_validator.py |
| `evidence_compaction_service.py` | 540 | 1 | 2 | token_budget_service.py |
| `token_budget_service.py` | 538 | 4 | 15 | ais27_benchmark_runner.py, empirical_benchmark_harness.py, llm_config_service.py, verdict_pipeline.py |
| `tokenizer_service.py` | 217 | 4 | 3 | ais27_benchmark_runner.py, evidence_compaction_service.py, openai_compatible.py, token_budget_service.py |
| `verified_semantic_retrieval_service.py` | 273 | 1 | 3 | verdict_pipeline.py |
| `evaluation_service.py` | 427 | 2 | 2 | evaluations.py, verdict_evaluation_engine.py |
| `ais_evaluation_service.py` | 1,268 | 1 | 2 | ais_evaluation.py |
| `empirical_accuracy_evaluator.py` | 266 | 3 | 4 | empirical_benchmark_harness.py, pilot_service.py, policy_simulation_service.py |
| `empirical_benchmark_harness.py` | 2,442 | 3 | 10 | run_empirical_benchmark.py, ais27_benchmark_runner.py, verdict_pipeline.py |
| `ais27_benchmark_runner.py` | 804 | 1 | 1 | ground_truth.py |
| `calibration_evaluator.py` | 168 | 2 | 2 | pilot_service.py, policy_simulation_service.py |
| `calibration_evaluation_service.py` | 260 | 1 | 1 | rules.py |
| `wilson_evaluator.py` | 48 | 1 | 4 | rule_learning_service.py |
| `confidence_normalizer.py` | 164 | 3 | 1 | ais27_benchmark_runner.py, independent_verdict_validator.py, openai_compatible.py |
| `actual_prompt_capture_service.py` | 659 | 2 | 1 | prompts.py, verdict_pipeline.py |
| `production_readiness_service.py` | 917 | 1 | 5 | prompts.py |
| `bulk_quality_audit_service.py` | 231 | 1 | 1 | prompts.py |
| `rule_learning_service.py` | 1,366 | 9 | 9 | rule_learning.py, main.py, ais_evaluation_service.py, analyst_review_service.py, automation_governor.py |
| `rule_intelligence_analyzer.py` | 617 | 11 | 8 | prompts.py, bulk_quality_audit_service.py, evidence_contract_service.py, fortisiem_service.py, integration_diagnostic_service.py |
| `detection_archetype_registry.py` | 861 | 10 | 9 | prompts.py, bulk_quality_audit_service.py, evidence_contract_service.py, evidence_requirement_mapper.py, evidence_sufficiency_engine.py |
| `learning_service.py` | 435 | 2 | 3 | learning.py, agent_memory_engine.py |
| `dry_run_service.py` | 524 | 3 | 4 | dry_run.py, validation_engine.py, tasks.py |

## 3. Identified Overlaps, Legacy Layers & Classifications

| Implementation | Classification | Role & Recommendation |
|---|---|---|
| `verdict_pipeline.py` + `ai_verdict_service.py` | `ACTIVE` | Authoritative live & simulation execution engine. **RETAIN**. |
| `ModelClaimExtractor` + `IndependentVerdictValidator` + `ReasoningIntegrityEngine` | `ACTIVE` | Primary claim grounding & reasoning integrity layer. **RETAIN (Protected)**. |
| `VerdictClaimValidator` + `VerdictGuardrailsEngine` + `VerdictTrustworthinessEngine` | `ACTIVE` | Defense-in-depth trust & safety guardrails invoked by `verdict_pipeline.py`. **RETAIN (Protected — do not remove validators)**. |
| `PolicySimulationService` (`policy_simulation_service.py`) | `ACTIVE` | Primary AIS 2.1 empirical evaluation engine. Contains internal `_simulate_model_output` passed as `simulated_output_fn` when `SIMULATED`. |
| `EmpiricalBenchmarkHarness` (`empirical_benchmark_harness.py`, 2,442L) & `AIS27BenchmarkRunner` (`ais27_benchmark_runner.py`, 804L) | `ACTIVE` (Eval) | Offline/3-mode GPU benchmark runners for AIS 2.5–2.7 empirical certification. **RETAIN** (`REQUIRED_HISTORICAL`). |
| `DryRunService` (`dry_run_service.py`, 524L) + `EvaluationService` (`evaluation_service.py`, 427L) | `DUPLICATE` (`ACTIVE`) | Phase 3 Dry-Run engine adapted (`LEGACY_DRY_RUN_ADAPTER`) onto `run_shared_verdict_pipeline`. Still actively called by `/agent-simulation-lab`. **REFACTOR** only after migrating UI to `/api/verdict-intelligence/*`. |
| `CalibrationEvaluationService` (`calibration_evaluation_service.py`, 260L) vs `CalibrationEvaluator` (`calibration_evaluator.py`, 168L) | `DUPLICATE` / `SUPERSEDED` | `CalibrationEvaluator` is active in `pilot_service.py` & `policy_simulation_service.py`. `CalibrationEvaluationService` only serves `GET /api/rules/{id}/calibration-report` (0 FE consumers). **CONSOLIDATE / VERIFY_FIRST**. |
| `WilsonScoreEvaluator` (`wilson_evaluator.py`, 48L) vs `EmpiricalAccuracyEvaluator.calculate_wilson_ci` | `DUPLICATE` | Identical Wilson 95% CI math. **CONSOLIDATE** (`RuleLearningService` can call shared helper). |
| `ais_evaluation_service.py:1096` `get_missing_inference_candidates` (22L) | `CONFIRMED_UNUSED` | 0 prod, 0 test, 0 script callers. **REMOVE** (Batch 1). |
