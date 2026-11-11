# Phase 9.1 — Remaining External Integration & Validation Work

No development blockers or code defects remain unresolved in offline local verification. All **9** remaining unverified acceptance criteria depend strictly on live infrastructure, physical hardware, or production data accumulation:

| Criterion ID | Feature / Module | Required Live / Production Environment | Required Execution Evidence |
|---|---|---|---|
| `LLM-01-C2` | `LLM-01` (Local LLM / Server 2 Integration) | Provisioned Ubuntu GPU Server 2 running vLLM serving target AWQ/GGUF weights reachable from Server 1 over private VLAN | `deployment/scripts/smoke_test_server2.py --live-server2` & `scripts/run_integration_suite.py --mode LIVE_MODEL_VALIDATION` returning `PASSED` with non-mock `LIVE_PROVIDER` provenance |
| `MON-02-C2` | `MON-02` (Monitoring & Operational Reliability) | Live Server 2 vLLM `/metrics` Prometheus endpoint | Verified `gpu_telemetry_verified=True` and live KV cache / request counters captured in `/api/system/servers/live` |
| `PRF-01-C2` | `PRF-01` (Automated Testing & Performance) | Real Server 2 GPU node under concurrent SOC evaluation workload | Measured P50/P95 latency, tokens/sec throughput, and concurrency saturation behavior under load |
| `QGS-02-C3` | `QGS-02` (Policy Quality Gates & Simulation) | Live Server 2 `OPENAI_COMPATIBLE` endpoint + eligible historical dataset (`>= 30` cases / rule) | Non-simulated `DryRun` historical replay and Gate `G8` evaluation against verified human ground truth |
| `FSI-01-C3` | `FSI-01` (FortiSIEM Integration) | Customer FortiSIEM Supervisor appliance + read-only API credentials | Live FortiSIEM incident pull, event pagination, rule definition sync, and deduplication run log |
| `WRK-02-C2` | `WRK-02` (Background Workers & Reconciliation) | Server 1 systemd `redis-server`, `ai-verdict-worker`, `ai-verdict-scheduler` | Real distributed Celery task dispatch across `live_triage`, `simulation_replay`, and `maintenance` queues |
| `DBM-01-C2` | `DBM-01` (Database Models & Migrations) | Live PostgreSQL 15+ instance on Server 1 | Clean `alembic upgrade head` (`008_soc_pilot`) and `APP_ENV=production` schema startup validation |
| `DEP-01-C2` | `DEP-01` (Deployment Package & Staging) | Target Ubuntu LTS Server 1 + Server 2 + Nginx + TLS | `install_ubuntu.sh` + `verify_server1.sh` + `scripts/run_integration_suite.py --mode STAGING_INTEGRATION_TESTS` passing |
| `PIL-02-C2` | `PIL-02` (SOC Pilot Execution) | Integrated Server 1 + Server 2 + FortiSIEM staging/pilot cohort | Controlled `SHADOW` -> `ANALYST_ASSISTED` SOC pilot evaluation & calibration study (`>= 30` verified labels per rule) |

