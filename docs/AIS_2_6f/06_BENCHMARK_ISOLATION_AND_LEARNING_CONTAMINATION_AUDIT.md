# 06 — Benchmark Isolation & Learning Contamination Audit

- All items in `AIS_2_6E_FROZEN_20` carry `excluded_from_learning = True`.
- `GroundTruthCertificationService` never writes to `LearningRecord`.
- `ReviewOrchestrator.submit_verdict`, `AnalystReviewService`, `VerifiedSemanticRetrievalService`, and `AgentMemoryEngine` check `is_frozen_benchmark_incident` / `get_benchmark_incident_identifiers` to keep benchmark incidents permanently out of `LearningRecord`, RAG precedents, and operational prompt feedback.
