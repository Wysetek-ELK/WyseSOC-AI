# 03 — GPU Telemetry Root Cause & Correction

## 1. Root Causes Identified

1. `backend/app/services/system_monitor_service.py` previously synthesized hardware GPU utilization and VRAM from vLLM KV cache gauges (`gpu_memory_total_gb = 24.0`, `gpu_memory_used_gb = round(5.5 + cache_factor * 12.0, 2)`, and `gpu_percent = min(100.0, round(12.0 + active_requests * 45.0, 1))`, producing synthetic `57%` GPU load and `24.0 GB` on a `15,360 MiB` Tesla T4).
2. `_generate_fallback_history_points()` and `_seed_historical_baseline()` seeded synthetic `24.0 GB` GPU points into historical charts.
3. Frontend `ServerInfrastructureMonitor.tsx` fell back to `?? 24 GB` and combined VRAM + KV cache in one bar.

## 2. Implemented Remediation

- Removed all synthetic `24.0 GB` and active-request GPU formulas and synthetic S2 GPU seed metrics.
- Extended `_parse_vllm_metrics` to extract `vllm:gpu_cache_usage_factor`/`kv_cache_usage_perc` -> `kv_cache_usage_percent`, `active_requests`, `waiting_requests`, `tokens_per_second`, `prompt_tokens_per_second`, plus authentic DCGM / `nvidia_smi` Prometheus gauges when present.
- Added optional `LOCAL_LLM_GPU_TELEMETRY_URL` polling for NVML/DCGM exporters while keeping `gpu_percent`, `gpu_memory_used_gb`, `gpu_memory_total_gb`, and `gpu_temp_c` strictly `None` when hardware gauges are absent.
- Separated **Physical GPU VRAM**, **vLLM KV Cache Occupancy**, and **Health Ping vs Inference Queue** in `ServerInfrastructureMonitor.tsx`.
