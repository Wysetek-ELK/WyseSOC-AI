# AIS 3.1 — Workstream 8: Server 2 GPU & Inference Runtime Truth

**Machine-Readable Evidence:** [GPU_RUNTIME_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/GPU_RUNTIME_MANIFEST.json)

---

## 1. Server 1 & Server 2 Connectivity Discovery

- **Server 1 (`Verdictum Core` / `172.26.41.240`, deploy path `/opt/wysesoc-ai`):**
  - PostgreSQL database: `healthy` (`1.54ms` latency, `pool_size=20`).
  - Redis & Celery: `healthy` (`reachable=true`, `live_triage_queue_depth=0`).
  - Configured Local LLM Endpoint: `http://13.204.214.64:8000/v1`, `configured_provider=OPENAI_COMPATIBLE`, `allow_mock_fallback=false`, `timeout=180.0s`.
- **Direct Workstation Connectivity:** Direct TCP from the developer workstation to `13.204.214.64:8000` is blocked by network/security-group rules (all GPU probes and benchmark dispatches execute **from Server 1** over authorized ingress).
- **Frontend Indicator Note:** When a UI screenshot shows `Cortex inference status: Offline`, that reflects either an unauthenticated/stale client poll or transient probe rather than Server 2 state; Server 1's live `/api/health` and `/api/ground-truth/ais27/runtime-verify` verify Server 2 is **ONLINE**.

---

## 2. Verified Server 2 Runtime Configuration (Read-Only Probe from Server 1)

| Parameter | Verified Runtime Value | Source |
|---|---|---|
| **Endpoint** | `http://13.204.214.64:8000/v1` | `/api/llm/config` & `/api/ground-truth/ais27/runtime-verify` |
| **Loaded Model ID (`/v1/models`)** | **`Qwen/Qwen3-14B-AWQ`** | Live vLLM `models_payload` (`HTTP 200`) |
| **vLLM Version (`/version`)** | `0.33.0` | Live `/version` probe (`HTTP 200`) |
| **Actual `max_model_len`** | `8192` | Live `/v1/models` payload |
| **Target Input Budget / Completion** | `7424` max input / `768` max output tokens | `/api/llm/config` model profile |
| **Probe Latency** | `25.7 ms` | Live `/api/ground-truth/ais27/runtime-verify` (`errors: []`) |
| **Server 2 Restarts / Edits Performed** | **None (`false`)** | Strict non-interference compliance |
| **Qwen3 Thinking Mode** | `enable_thinking: false` passed in `chat_template_kwargs` | `AIS27BenchmarkRunner._dispatch_vllm` |
| **Physical Hardware Telemetry (NVML/DCGM)** | `gpu_telemetry_verified: false` (no direct SSH/NVML exporter on Server 2) | `/api/health` `local_llm` |

---

## 3. Qwen3 Reasoning & Thinking-Trace Handling

- All AIS 3.1 GPU requests pass `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` with `temperature=0.0` and `max_tokens=768`, suppressing `<think>` chains so completion tokens serve structured JSON output cleanly.
- If any raw response contains `<think>...</think>` tags or reasoning fields, `AIS27BenchmarkRunner._parse_raw_vllm_reply` strips/isolates them for audit persistence without exposing internal reasoning traces to standard analyst UI views.
