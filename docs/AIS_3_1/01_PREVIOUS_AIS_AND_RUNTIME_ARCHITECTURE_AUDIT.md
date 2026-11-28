# AIS 3.1 — Workstream 1: Previous AIS & Runtime Architecture Audit

**Product:** Verdictum AI — Agentic SOC Intelligence (WYSETEK)  
**Cohort Audited:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Audit Date (UTC):** `2026-11-28`

---

## 1. Reconciliation of Previous AIS Phases (AIS 2.8, AIS 2.9, AIS 3.0)

| Phase | Deployed Commit SHA | Primary Status | Key Verified Empirical Result | Remaining Carry-Forward Gap |
|---|---|---|---|---|
| **AIS 2.8** | `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509` | `AIS_2_8_BLOCKED_PENDING_GPU_AUTHORIZATION` | Mode A/B/C baseline on AIS 2.7 (`Qwen2.5-7B-Instruct-AWQ`: 10.0% Mode B binary end-to-end); offline tests 55 passed | Server 2 live Qwen3-14B execution awaited operator JWT & budget |
| **AIS 2.9** | `2dc8d15a4517626bcae375e5754f4431693053f3` | `FROZEN_REGRESSION_TARGETS_MET` | `Qwen/Qwen3-14B-AWQ` on `AIS_2_6E_FROZEN_20`: 95.0% (19/20) validated exact agreement, 100.0% (9/9) TP recall, 90.0% (9/10) binary correctness, 0/20 context overflows, `33/33` live GPU requests | 0/20 GT-3 (single-reviewer GT-2); `132501348` FP abstained; AIS 3.0 100-incident holdout unreviewed (`0/100`) |
| **AIS 3.0 -> AIS 3.1 Entry** | `2dc8d15a4517626bcae375e5754f4431693053f3` | Ready for Holdout Evaluation | All 100 holdout incidents manually reviewed & locked (`100/100 GT2_SINGLE_REVIEW`); Server 1 & Server 2 ONLINE | UI displayed stale AIS 2.6e/2.7 20-cohort text, Vendor defaulted to `Prisma SASE`, `Exposure Risk: 100` uninvestigated |

---

## 2. Active Verdict Pipeline & Component Verification

```text
Original SIEM Incident (FortiSIEM / PostgreSQL incidents + incident_events)
        |
        v  [AIS31BenchmarkService._prepare_incident_wire_payload / verdict_pipeline.py]
HistoricalGroundTruthValidator.sanitize_incident_for_inference
  + build_model_facing_payload (allowlist — zero GT / ai_verdict / analyst fields)
        |
        +---> EvidenceNormalizationService.normalize_incident_evidence -> CanonicalEvidenceRecord[]
        +---> RuleDefinitionBuilder.build_complete_rule_spec (conditions, logic, thresholds, raw schema)
        +---> EvidenceIntelligenceEngine.enrich_incident_evidence (typed IPs, paths, hashes, protocols)
        |
        v  [Policy Freeze & Token Accounting]
FROZEN_NEUTRAL_SYSTEM_PROMPT (NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX)
  + ModelTokenizerService.render_wire_user_message
  + TokenBudgetService.budget_prompt (8192 max context - 768 completion = 7424 input ceiling)
  + ModelTokenizerService.count_wire_prompt_tokens_remote (vLLM /tokenize parity)
        |
        v  [Server 2: Verdictum Cortex — http://13.204.214.64:8000/v1]
vLLM 0.33.0 — Qwen/Qwen3-14B-AWQ (temperature=0.0, top_p=1.0, enable_thinking=false)
        |
        v
AIS27BenchmarkRunner._parse_raw_vllm_reply -> Raw LLM Verdict (TP / FP / REQUIRES_ATTENTION)
        |
        v
ModelClaimExtractor.extract_and_ground_claims + IndependentVerdictValidator.validate_verdict
        |
        v
Validated Application Verdict (TP / FP / REQUIRES_ATTENTION) -> Persisted in ais31_benchmark_results
        |
        v  [Post-Run RBAC-Restricted Comparison]
Locked Human Ground Truth (AnalystVerdictReview, GT2_SINGLE_REVIEW) -> Empirical Metrics
```

---

## 3. Component Audit Classification

### Verified & Active in Runtime
1. **Verdict Pipeline & Sanitization:** `HistoricalGroundTruthValidator.sanitize_incident_for_inference`, `build_model_facing_payload`, `EvidenceNormalizationService`, `EvidencePreflightValidator`, `EvidenceIntelligenceEngine`, `RuleDefinitionBuilder`.
2. **Tokenization & Context Budget:** `TokenBudgetService` + `ModelTokenizerService.count_wire_prompt_tokens_remote` using live vLLM `/tokenize` (`max_model_len=8192`, `max_tokens=768`, `target_input_budget=7424`).
3. **Verdict Parsing & Validation:** `robust_parse_model_verdict_json`, `ModelClaimExtractor`, `IndependentVerdictValidator` (preserved unmodified; note: CrowdStrike/Prisma-specific FP/TP rules in `IndependentVerdictValidator` may abstain to `REQUIRES_ATTENTION` on generic FortiSIEM rules, so AIS 3.1 reports Raw LLM vs Validated App separately).
4. **RAG & Learning Isolation:** `VerifiedSemanticRetrievalService` contains `88` `LearningRecord` rows (`83` verified) restricted to 3 AIS 2.x rules; **0/100** holdout incidents appear in `LearningRecord`, and AIS 3.1 benchmark sets `rag_block=""`, `rag_excluded=True`, `memory_excluded=True`.
5. **Server 1 Application Host:** `172.26.41.240`, deploy directory `/opt/wysesoc-ai` (corrected from older doc path `/opt/ai-verdict`), PostgreSQL healthy (`1.54ms`), Redis/Celery healthy (`queue_depth=0`).
6. **Server 2 Inference Host:** `13.204.214.64:8000/v1` (`verdictum-cortex-01`), vLLM `0.33.0`, loaded model `Qwen/Qwen3-14B-AWQ`, `max_model_len=8192`, HTTP `200`, `25.7ms` probe latency from Server 1. Directly unreachable from workstation (security-group restricted to Server 1).

### Defective / Incomplete Components Found & Fixed in AIS 3.1
1. **Legacy Policy Coverage Across 30 Holdout Rules:** Only `20/30` holdout rules have `APPROVED` policy versions (`16` legacy v1 + `4` with newer DRAFT); `10/30` rules (`19` incidents) have only `DRAFT v1`. Resolved by freezing `NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX` + `RuleDefinitionBuilder` uniformly across all 100 holdout items.
2. **Vendor Resolution Bug:** `GroundTruthCertificationService` fell back to `"Prisma SASE"` for all non-CrowdStrike rules, mislabeling all 100 FortiSIEM holdout incidents. Fixed with `_resolve_cohort_item_vendor`.
3. **Exposure Risk `100/100` Counter Bug:** Flagged any incident with non-null `ground_truth` ORM row (even empty `resolution=""` on `85/100` items) or `ai_verdict` ORM field without checking actual RAG/Learning/prompt leakage or `BLIND_ENFORCED` masking. Fixed with structured 4-state taxonomy (`_classify_item_exposure`).
4. **Hardcoded AIS 2.6e / 20-Cohort UI Text:** Replaced in `human-review-queue/page.tsx`, `GroundTruthCertificationPanel.tsx`, and `AccuracyLearningSummary.tsx`.
5. **`ais27_benchmark_runner.py:661` Hardcoded Contract:** Replaced hardcoded CrowdStrike/Prisma `contract_key` lookup with dynamic `get_rule_semantics_and_contract`.
6. **Missing AIS 3.1 Orchestration Engine:** Added `ais31_benchmark_runs` & `ais31_benchmark_results` (migration `017_ais31_holdout_benchmark.py`) and `AIS31BenchmarkService`.
