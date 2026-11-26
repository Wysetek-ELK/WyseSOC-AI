# 02 — Architecture and Runtime Audit

- Audited `TokenBudgetService`, `ModelTokenizerService`, `AIS27BenchmarkRunner`, `OpenAICompatibleProvider`, `verdict_pipeline`, `ModelClaimExtractor`, `VerdictClaimValidator`, `IndependentVerdictValidator`, and `GroundTruthCertificationService`.
- Confirmed `Verdictum Core` (`verdictum-core-01`, `172.26.41.240`) and `Verdictum Cortex` (`verdictum-cortex-01`, `Qwen/Qwen3-14B-AWQ`, `max_model_len=8192`) runtime parity without touching Server 2 service state.
