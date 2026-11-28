# 01 — Runtime Configuration Verification

- **Verified At (UTC)**: `2026-11-28T14:32:20.480527+00:00`
- **Server 1 (Verdictum Core)**: `http://172.26.41.240` (`verdictum-core-01`), deployed SHA `eb78e6ffc034b0cfc3560de0509642efda5b9e59`
- **Server 2 (Verdictum Cortex)**: `http://13.204.214.64:8000/v1` (`verdictum-cortex-01`), engine `vLLM / PyTorch CUDA`

## Capacity Distinction

1. **Model Theoretical Capacity**: Qwen3-14B native architecture supports 32,768 tokens (reference spec; not directly inspected via Server 2 filesystem).
2. **Configured vLLM `max_model_len`**: **`8192`** — independently verified via `/api/llm/config` (`verified_max_model_len: 8192`) AND live Server 2 `400 BadRequestError` when probing `max_tokens=8500`:
   `max_tokens=8500 cannot be greater than max_model_len=8192. Please request fewer output tokens.`
3. **Effective Runtime Context Capacity**: **`8192`** tokens.
4. **Maximum Available Completion Budget (Per Request)**: Dynamically computed as `8192 - actual_input_tokens - safety_margin` (32 tokens when `/tokenize` verified, 64 tokens on local BPE fallback).

## Verification Boundary Disclosure

- Server 2 (`13.204.214.64:8000`) is network-restricted to Server 1's outbound IP and has no SSH profile in `.upla/config.json`. Therefore, Server 2 OS-level `ps` flags, systemd unit file, vLLM pip version, and `nvidia-smi` telemetry could not be inspected directly from the workstation; all Server 2 runtime attributes reported here were verified through authorized Server 1 APIs and live vLLM responses.
