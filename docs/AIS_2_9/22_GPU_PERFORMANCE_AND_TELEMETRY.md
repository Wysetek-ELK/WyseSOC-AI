# 22 — GPU Performance and Telemetry Verification

- **Requests Attempted / Succeeded / Failed**: `33 / 33 / 0` (within `<= 50` cap).
- **Smoke Test**: `811.49 ms`
- **Frozen 20 Latency (ms)**: min `61223.5`, avg `70097.0` (`70.1 s`), max `83934.6`
- **Live vLLM Telemetry**: Verified on `/inference-control` UI (`vLLM KV Cache Occupancy: 27.5%`, `Health Ping: 8.1 ms`, `1 running, 0 waiting`). Hardware NVML/DCGM VRAM & temperature remain explicitly marked `Unavailable (No NVML/DCGM)` — zero synthetic telemetry fabricated.
