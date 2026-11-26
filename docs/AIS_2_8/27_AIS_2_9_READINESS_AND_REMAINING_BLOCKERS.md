# 27 — AIS 2.9 Readiness & Remaining Blockers

1. **BLK-28-01 (Live Execution Auth):** Supply Server 1 admin bearer token (or temporary benchmark credential) to execute live Qwen3-14B Experiments A2, C, and D via `http://172.26.41.240/api/ground-truth/ais27/*`.
2. **BLK-28-02 (Head-to-Head Model Switch):** Coordinate switching Server 2 (`verdict-llm`) temporarily back to `Qwen/Qwen2.5-7B-Instruct-AWQ` to execute fair-parity Experiment B baseline runs, then restore Qwen3-14B-AWQ.
3. **BLK-28-03 (NVML/DCGM Hardware Exporter):** Deploy an authenticated NVML/DCGM metrics endpoint on Server 2 and set `LOCAL_LLM_GPU_TELEMETRY_URL` on Server 1 if physical GPU VRAM/temp telemetry is required (`gpu_telemetry_verified=true`).
4. **BLK-28-04 (Transport Encryption):** Ensure Server 1 -> Server 2 traffic stays strictly on encrypted private VPC/VPN/TLS (`G10`).
5. **BLK-28-05 (GT-3 & Expanded Held-Out Cohort):** Complete GT-3 dual review on non-clustered unseen incidents before any AIS 2.9 certification gate.
