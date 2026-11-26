# 18 — GPU Latency, Throughput & Telemetry Verification

- **Telemetry Separation Integrity**: Synthetic GPU VRAM (`24.0 GB`) & synthetic compute % remain completely removed. `Physical GPU Telemetry` (`Unavailable` without NVML/DCGM exporter) is strictly separated from live `vLLM KV Cache Occupancy` and `API health` vs `inference generation` latency.
- **Measured Inference Latency (`Qwen/Qwen3-14B-AWQ` on `g4dn.2xlarge` Tesla T4, `max_num_seqs=1`)**:
  - Smoke Test (`61` tok): `822.09 ms`
  - **Exp A (`20` calls)**: avg `62912.49 ms`, range `48934.03..85021.03 ms`, total GPU time `1258.25 s`
  - **Exp B (`20` calls)**: avg `66131.95 ms`, range `43879.29..84183.75 ms`, total GPU time `1322.64 s`
  - **Exp C (`20` calls)**: avg `69084.74 ms`, range `56183.33..80285.09 ms`, total GPU time `1381.69 s`
  - **Exp R (`15` calls)**: avg `56153.18 ms`, range `38788.35..82028.06 ms`, total GPU time `842.3 s`
