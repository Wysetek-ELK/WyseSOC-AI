# AIS 3.1 — Workstream 11: Full 100-Incident Holdout Live GPU Benchmark Execution

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Run ID:** `64253e31-4e75-4d51-9f54-cc80a62fa17c` (`run_key: AIS31-FULL100-20261128`)  
**Benchmark Grade:** `PROVISIONAL_SINGLE_REVIEW_BENCHMARK`  
**Machine-Readable Evidence:**
- [BENCHMARK_RUN_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/BENCHMARK_RUN_MANIFEST.json)
- [LIVE_GPU_BENCHMARK_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/LIVE_GPU_BENCHMARK_RESULTS.json)

---

## 1. Execution Provenance & Configuration

| Execution Property | Verified Value |
|---|---|
| Target Model | `Qwen/Qwen3-14B-AWQ` |
| Actual Model Returned (`/v1/chat/completions`) | `Qwen/Qwen3-14B-AWQ` (`100/100`) |
| Server 2 Runtime | `http://13.204.214.64:8000/v1`, `vLLM 0.33.0`, `max_model_len = 8192` |
| Sampling Parameters | `temperature = 0.0`, `top_p = 1.0`, `enable_thinking = false`, `max_tokens = 768` |
| Policy Freeze SHA-256 | `3b09dd249e3fad38ac795f88e957b1b305bd04025cc8fb6cc4605584b461fb6c` (`NEUTRAL_SOC_BASELINE_V2`) |
| Holdout Manifest SHA-256 | `5e856ff85f0008cee40dec45c2f9e560ed760dd0413dcb7b559f7ff70d293d27` |
| RAG & Agent Memory | Strictly Excluded (`rag_excluded = true`, `memory_excluded = true`) |
| Mock Fallback | Strictly Disabled (`LIVE_SERVER2_VLLM` provenance on all `100` rows) |

---

## 2. Full Cohort Accounting & Runtime Telemetry

| Accounting / Telemetry Metric | Verified Value |
|---|---:|
| Original Holdout Population | **100** |
| Eligible Population Executed | **100** (`0` quarantined) |
| Successful Inference Executions | **100 / 100** (`100.0%`) |
| Technical Failures / Context Overflows | **0** (`0.0%`) |
| Not Executed | **0** |
| Finish Reason Distribution | `stop`: **100 / 100** (`0` `length` truncations on wire) |
| Total Prompt Tokens Consumed | **577,230** |
| Total Completion Tokens Generated | **54,031** |
| Total Wall Clock Runtime | **6,135.4 s** (`~102.3 min`, sequential `batch_size=1` checkpointing) |
| Mean Inference Latency | **60,302.14 ms** (`60.30 s`) |
| Median Inference Latency | **55,581.95 ms** (`55.58 s`) |
| P95 Inference Latency | **81,632.30 ms** (`81.63 s`) |

---

## 3. Idempotent Resume & Wire Prompt Spot-Checks

- Running a follow-up batch resume pass (`run_key=AIS31-FULL100-20261128`, `batch_size=5`) returned `executed_in_call: 0`, `completed_count: 100`, `failed_count: 0`, confirming duplicate execution prevention.
- Direct retrieval via `GET /api/ground-truth/ais31/runs/64253e31-4e75-4d51-9f54-cc80a62fa17c/wire-prompt/{fid}` on FIDs `13960` (`tok=6210`, `chatcmpl-9afac4e76ec76c66`), `8601` (`tok=4417`, `chatcmpl-80346f5d5e052869`), and `14341` (`tok=4299`, `chatcmpl-81f1e2dde2aca297`) verified exact `vllm_tokenize_api` parity and `leak_flags = []`.
- Ground truth comparison executed **only after** all 100 incidents reached `status = COMPLETED`.
