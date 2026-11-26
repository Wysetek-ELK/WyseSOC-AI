# AIS 2.7 — Workstream 8: GPU Runtime Verification and Live Smoke Test

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Authoritative Artifacts:** [GPU_RUNTIME_MANIFEST.json](GPU_RUNTIME_MANIFEST.json), [LIVE_SMOKE_TEST_RESULT.json](LIVE_SMOKE_TEST_RESULT.json)

## 1. Live GPU Server 2 Verification (Zero Blind Assumptions)

Server 2 (`http://13.204.214.64:8000/v1`) was queried directly from deployed Server 1 (`http://172.26.41.240/api/ground-truth/ais27/runtime-verify`) prior to any benchmark call:

| Property | Observed Runtime Value | Status |
|---|---|---|
| Inference Endpoint | `http://13.204.214.64:8000/v1` | Reachable from Server 1 (firewalled from external workstation) |
| Inference Engine | `vLLM` v`0.33.0` (`/version` HTTP `200`) | VERIFIED |
| Served Model ID | `Qwen/Qwen2.5-7B-Instruct-AWQ` (`/v1/models` HTTP `200`) | VERIFIED |
| Served `max_model_len` | `8192` tokens | VERIFIED |
| Server 1 Probe Latency | `32.21 ms` | PASS |
| Hardware Instance / VRAM | Historical claim: EC2 `g5.xlarge` / NVIDIA A10G 24 GB (`gpu_telemetry_verified=false` on Server 1 `/api/health`) | NOT_VERIFIED via HTTP |

## 2. Live Inference Smoke Test (Call #1 of 41)

- **Timestamp (UTC):** `2026-11-25T05:38:29.287726` -> `2026-11-25T05:38:29.694687`
- **HTTP Status:** `200` (`vllm_response_id`: `chatcmpl-969d0b6172c8e3a4`)
- **Model Returned:** `Qwen/Qwen2.5-7B-Instruct-AWQ` | **Finish Reason:** `stop`
- **Token Usage:** `43` prompt + `14` completion = `57` total tokens
- **Latency:** `406.98 ms`
- **Verdict:** **PASS** — End-to-end Server 1 -> Server 2 OpenAI-compatible live vLLM inference verified cleanly.
