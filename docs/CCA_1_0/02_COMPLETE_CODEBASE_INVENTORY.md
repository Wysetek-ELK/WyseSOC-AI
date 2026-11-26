# 02 — Complete Codebase Inventory

## 1. Category Breakdown (2,229 Tracked Files)

| Category | File Count | Total Lines | Non-Empty Lines | Code Lines |
|---|---:|---:|---:|---:|
| `backend_api` | 26 | 7,962 | 7,126 | 7,048 |
| `backend_config` | 4 | 78 | 67 | 67 |
| `backend_core` | 2 | 178 | 150 | 138 |
| `backend_entrypoint` | 4 | 742 | 659 | 623 |
| `backend_migration` | 16 | 1,822 | 1,624 | 1,580 |
| `backend_migration_config` | 2 | 98 | 69 | 69 |
| `backend_model` | 26 | 1,696 | 1,362 | 1,294 |
| `backend_schema` | 31 | 3,280 | 2,760 | 2,706 |
| `backend_script` | 7 | 883 | 735 | 713 |
| `backend_service` | 87 | 43,306 | 39,430 | 38,005 |
| `backend_test` | 106 | 38,697 | 34,429 | 32,663 |
| `backend_util` | 4 | 179 | 140 | 133 |
| `backend_worker` | 3 | 487 | 446 | 442 |
| `deployment` | 18 | 1,048 | 895 | 833 |
| `docs` | 1689 | 154,003 | 136,708 | 136,708 |
| `fixture` | 1 | 0 | 0 | 0 |
| `frontend_app_support` | 2 | 497 | 432 | 432 |
| `frontend_asset` | 10 | 0 | 0 | 0 |
| `frontend_build_config` | 8 | 6,803 | 6,776 | 6,773 |
| `frontend_component` | 33 | 18,630 | 17,547 | 17,424 |
| `frontend_config` | 2 | 406 | 391 | 391 |
| `frontend_context` | 1 | 141 | 124 | 122 |
| `frontend_data` | 8 | 3,669 | 3,621 | 3,605 |
| `frontend_lib` | 5 | 5,634 | 5,244 | 5,210 |
| `frontend_page` | 31 | 16,582 | 15,642 | 15,567 |
| `frontend_test` | 16 | 2,520 | 2,222 | 2,093 |
| `root_asset` | 1 | 0 | 0 | 0 |
| `root_config` | 3 | 61 | 52 | 52 |
| `root_docs` | 13 | 2,305 | 1,907 | 1,907 |
| `root_script` | 39 | 10,618 | 9,646 | 9,324 |
| `scratch` | 31 | 3,062 | 2,888 | 2,836 |

## 2. Largest Application Source Files (>= 500 Lines)

| File Path | Category | Total Lines | Code Lines |
|---|---|---:|---:|
| `frontend/src/app/agent-intelligence-studio/page.tsx` | `frontend_page` | 5,162 | 4,880 |
| `frontend/src/lib/api.ts` | `frontend_lib` | 4,287 | 3,973 |
| `backend/app/services/empirical_benchmark_harness.py` | `backend_service` | 2,442 | 2,175 |
| `backend/app/services/fortisiem_service.py` | `backend_service` | 2,435 | 2,147 |
| `backend/app/api/prompts.py` | `backend_api` | 1,947 | 1,743 |
| `frontend/src/components/learning/RuleLearningDashboard.tsx` | `frontend_component` | 1,531 | 1,426 |
| `frontend/src/app/ai-triage-workbench/[id]/page.tsx` | `frontend_page` | 1,510 | 1,423 |
| `backend/app/services/policy_simulation_service.py` | `backend_service` | 1,492 | 1,364 |
| `backend/app/services/ground_truth_certification_service.py` | `backend_service` | 1,430 | 1,307 |
| `backend/app/services/verdict_pipeline.py` | `backend_service` | 1,381 | 1,289 |
| `backend/app/services/rule_learning_service.py` | `backend_service` | 1,366 | 1,202 |
| `frontend/src/app/verdict-intelligence/page.tsx` | `frontend_page` | 1,359 | 1,259 |
| `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx` | `frontend_component` | 1,329 | 1,277 |
| `frontend/src/components/admin-guide/WorkflowFlowDiagram.tsx` | `frontend_component` | 1,310 | 1,227 |
| `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` | `frontend_component` | 1,310 | 1,221 |
| `frontend/src/components/compact/AiTestWorkbench.tsx` | `frontend_component` | 1,283 | 1,197 |
| `backend/app/services/ais_evaluation_service.py` | `backend_service` | 1,268 | 1,088 |
| `frontend/src/components/review/GroundTruthCertificationPanel.tsx` | `frontend_component` | 1,261 | 1,209 |
| `frontend/src/app/human-review-queue/page.tsx` | `frontend_page` | 1,217 | 1,159 |
| `frontend/src/components/pilot/PilotControlAndDashboard.tsx` | `frontend_component` | 1,159 | 1,105 |
| `backend/app/services/pilot_service.py` | `backend_service` | 1,146 | 1,048 |
| `backend/app/services/independent_verdict_validator.py` | `backend_service` | 1,115 | 942 |
| `frontend/src/app/agent-configuration/page.tsx` | `frontend_page` | 1,059 | 989 |
| `frontend/src/components/compact/CompactDesignSystem.tsx` | `frontend_component` | 1,024 | 918 |
| `backend/app/services/prompt_studio_service.py` | `backend_service` | 984 | 837 |
| `frontend/src/app/ai-triage-workbench/page.tsx` | `frontend_page` | 955 | 909 |
| `backend/app/services/evidence_normalization_service.py` | `backend_service` | 951 | 828 |
| `frontend/src/app/telemetry-hub/page.tsx` | `frontend_page` | 945 | 876 |
| `backend/app/services/model_provider/openai_compatible.py` | `backend_service` | 924 | 833 |
| `backend/app/services/production_readiness_service.py` | `backend_service` | 917 | 825 |
| `frontend/src/components/compact/ManageVersionHistory.tsx` | `frontend_component` | 887 | 836 |
| `backend/app/services/policy_quality_validator.py` | `backend_service` | 885 | 731 |
| `backend/app/services/detection_archetype_registry.py` | `backend_service` | 861 | 797 |
| `backend/app/api/rule_learning.py` | `backend_api` | 842 | 758 |
| `backend/app/services/ingestion_service.py` | `backend_service` | 832 | 717 |
| `backend/app/services/ais27_benchmark_runner.py` | `backend_service` | 804 | 755 |
| `backend/app/api/verdict_intelligence.py` | `backend_api` | 778 | 684 |
| `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx` | `frontend_component` | 759 | 693 |
| `frontend/src/components/system/ServerInfrastructureMonitor.tsx` | `frontend_component` | 759 | 701 |
| `backend/app/services/llm_config_service.py` | `backend_service` | 746 | 667 |
| `backend/app/services/fortisiem_scheduler.py` | `backend_service` | 745 | 624 |
| `frontend/src/app/soc-chatbot/page.tsx` | `frontend_page` | 740 | 684 |
| `backend/app/services/reasoning_integrity_engine.py` | `backend_service` | 732 | 614 |
| `frontend/src/data/admin-guide/architectureFlowData.ts` | `frontend_data` | 732 | 722 |
| `backend/app/services/ai_verdict_service.py` | `backend_service` | 730 | 641 |
| `frontend/src/data/admin-guide/studioGuideData.ts` | `frontend_data` | 703 | 693 |
| `frontend/src/components/compact/AccuracyLearningSummary.tsx` | `frontend_component` | 684 | 629 |
| `frontend/src/app/agent-simulation-lab/page.tsx` | `frontend_page` | 679 | 635 |
| `backend/app/services/actual_prompt_capture_service.py` | `backend_service` | 659 | 587 |
| `backend/app/services/policy_version_governance_service.py` | `backend_service` | 658 | 557 |
| `backend/app/services/investigation_service.py` | `backend_service` | 652 | 567 |
| `backend/app/services/integration_diagnostic_service.py` | `backend_service` | 632 | 571 |
| `frontend/src/app/page.tsx` | `frontend_page` | 627 | 599 |
| `backend/app/services/rule_intelligence_analyzer.py` | `backend_service` | 617 | 537 |
| `frontend/src/components/admin-guide/StudioGuideSection.tsx` | `frontend_component` | 613 | 585 |
| `backend/app/services/system_monitor_service.py` | `backend_service` | 611 | 545 |
| `backend/app/services/analyst_review_service.py` | `backend_service` | 600 | 524 |
| `frontend/src/data/admin-guide/pagesGuideData.ts` | `frontend_data` | 596 | 578 |
| `backend/app/services/historical_eligibility_service.py` | `backend_service` | 569 | 524 |
| `frontend/src/lib/qualityExport.ts` | `frontend_lib` | 565 | 524 |
| `frontend/src/app/agent-memory/page.tsx` | `frontend_page` | 546 | 509 |
| `backend/app/services/evidence_compaction_service.py` | `backend_service` | 540 | 437 |
| `backend/app/services/incident_service.py` | `backend_service` | 540 | 474 |
| `backend/app/services/model_claim_extractor.py` | `backend_service` | 539 | 448 |
| `backend/app/services/token_budget_service.py` | `backend_service` | 538 | 455 |
| `backend/app/api/chat.py` | `backend_api` | 534 | 482 |
| `frontend/src/components/admin-guide/AdminGuideInteractiveReader.tsx` | `frontend_component` | 534 | 498 |
| `backend/app/services/policy_governance.py` | `backend_service` | 532 | 472 |
| `backend/app/services/historical_ground_truth_validator.py` | `backend_service` | 531 | 484 |
| `backend/app/services/dry_run_service.py` | `backend_service` | 524 | 466 |
| `backend/app/services/blind_review_guard.py` | `backend_service` | 520 | 487 |
| `backend/app/schemas/verdict_intelligence.py` | `backend_schema` | 517 | 396 |
