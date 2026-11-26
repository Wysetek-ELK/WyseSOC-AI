# AIS 2.7 — Workstream 20: GPU Usage, Cost Accounting & Shutdown Status

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [GPU_USAGE_AND_COST_MANIFEST.json](GPU_USAGE_AND_COST_MANIFEST.json), [gpu_closeout_verify.json](inference_evidence/runtime_provenance/gpu_closeout_verify.json)

## 1. Observed Resource Utilization

- **Total Successful GPU Calls:** `41 / 41` authorized (`1` smoke + `20` Mode A + `20` Mode B)
- **Gateway Retries:** `1 / 5` max (`1` HTTP 504 on `132499009` combined call prior to single-mode split)
- **Total Tokens Consumed:** `208474` (`186831` prompt + `21643` completion)
- **Aggregate Live Inference Wall Time:** `1716.83 s` (~`28.6` minutes pure generation across `41` calls; Mode A mean `41450.15 ms`, Mode B mean `44370.97 ms`)
- **Cloud Billing Dollar Cost:** **UNVERIFIED** from Server 1 HTTP telemetry (`gpu_telemetry_verified=false`; hardware EC2 instance `g5.xlarge` is historical metadata only).

## 2. Closeout State & Operator Action Required

- Server 1 `/api/health` verified post-benchmark: `active_concurrent_slots = 0`, `live_triage_queue_depth = 0`, `current_s2_health = ONLINE`.
- **GPU Server 2 Status:** **LEFT RUNNING intentionally** per Checkpoint A operator authorization (`do not automatically stop GPU Server 2 unless separately authorized`). **Operator must manually stop/shut down Server 2 (`13.204.214.64:8000`) when finished to stop hourly billing.**
