# 05 — Qwen3 Live Runtime Verification

- **Verified Model**: `Qwen/Qwen3-14B-AWQ` (revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, vLLM `0.33.0`).
- **Live Probe Results** (`/api/ground-truth/ais27/runtime-verify`):
  - `/health`: HTTP `200`
  - `/v1/models`: HTTP `200`, `max_model_len=8192`
  - Probe Latency: `18.98 ms`
- **Configuration Integrity**: `enable_thinking=False`, `context_budget=8192`, `max_tokens=768`, `target_input_budget=7424`. Systemd service `vllm-server.service` + `90-qwen3-14b.conf` preserved unmodified; Qwen2.5 cache preserved; automatic closure disabled.
