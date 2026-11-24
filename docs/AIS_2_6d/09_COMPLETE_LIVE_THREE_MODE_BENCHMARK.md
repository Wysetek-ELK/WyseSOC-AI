# AIS 2.6d — Workstream 9: Complete Live Three-Mode Benchmark Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:25:00Z  
**Document Identity:** `docs/AIS_2_6d/09_COMPLETE_LIVE_THREE_MODE_BENCHMARK.md`  
**Execution State:** `BLOCKED_GPU_UNAVAILABLE`  
**Referenced Manifests:**  
- [MODE_A_LIVE_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/MODE_A_LIVE_EXECUTION_LEDGER.jsonl)
- [MODE_B_LIVE_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/MODE_B_LIVE_EXECUTION_LEDGER.jsonl)
- [MODE_C_VALIDATION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/MODE_C_VALIDATION_LEDGER.jsonl)
- [LIVE_BENCHMARK_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/LIVE_BENCHMARK_MANIFEST.json)
- [LIVE_BENCHMARK_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/LIVE_BENCHMARK_RESULTS.json)

---

## 1. Three-Mode Evaluation Architecture

AIS 2.6d maintains the three-mode benchmark architecture designed to isolate model capability, policy bias, and deterministic validation:

1. **Mode A — Neutral Prompt Baseline (Pure Raw Telemetry & Detection Rule):**
   - Prompt: `NEUTRAL_SOC_BASELINE_PROMPT.txt` (Hash: `eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056`).
   - Purpose: Measures the LLM's raw security reasoning without domain policy nudging.
   - Cohort: All 20 frozen incidents.
2. **Mode B — Approved Domain Policy Evaluation (Compiled Prompt Version 1):**
   - Prompt: Policy-compiled prompt with FortiSIEM / CrowdStrike domain directives (Hash: `fe1c4184cc5b8f020ee006c8175ba0144b0e82ba246b29a752490748e0ad65cc`).
   - Purpose: Evaluates whether approved organizational policy improves decision coverage or introduces systematic bias.
   - Cohort: All 20 frozen incidents.
3. **Mode C — Reused Inference with Independent Deterministic Validation:**
   - Evaluator: Deterministic rule validator checking telemetry support and contradiction states.
   - Purpose: Assesses whether programmatic post-validation mitigates hallucination and suppresses unsafe FP classifications.
   - Zero additional inference calls (re-evaluates Mode B inferences).

---

## 2. Infrastructure Block Statement

In compliance with Non-Negotiable Requirements 1, 2, and 18:
- GPU Server 2 (`http://13.204.214.64:8000/v1`) is unreachable (AWS EC2 instance stopped).
- Zero simulated or synthetic inference records have been fabricated.
- Mode A, Mode B, and Mode C live benchmark ledgers are created with explicit blocker manifests.

---

## 3. Workload Sizing & Runtime Estimates

Upon activation of Server 2:
- Mode A Live Inferences: 20 calls (~8.0 mins @ 24s/call)
- Mode B Live Inferences: 20 calls (~10.0 mins @ 30s/call)
- Mode C Post-Validation: 0 GPU calls (instant deterministic computation)
- Counterfactual Policy Testing: 11 calls (~5.5 mins)
- **Total Workload:** 51 requests (~23.5 minutes wall-clock time)
- Estimated GPU Cost: < $0.70 USD on `g5.xlarge`.

---

## 4. Benchmark Ledgers Specification

All live inference calls will log directly to `MODE_A_LIVE_EXECUTION_LEDGER.jsonl` and `MODE_B_LIVE_EXECUTION_LEDGER.jsonl` capturing:
- `timestamp_utc`, `incident_id`, `prompt_hash`, `actual_model_response_id`, `actual_prompt_tokens`, `actual_completion_tokens`, `latency_ms`, `raw_verdict`, `calibrated_confidence`, `execution_provenance: LIVE_GPU_INFERENCE`.
