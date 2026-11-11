# Phase 9 — Remaining External Integration & Certification Work

This document strictly distinguishes offline software completion (`DEVELOPMENT_COMPLETE` + `PHASE_9_CODE_READY`) from external infrastructure validation and empirical certification items that **cannot** be executed without provisioned staging/production systems.

---

## Remaining Work Matrix (`NOT_TESTED` / `NOT_DEPLOYED`)

| Item ID | Related Registry Criteria | What Remains | Blocker / Environment Prerequisite |
|---|---|---|---|
| `REM-01` | `DEP-01-C2`, `DBM-01-C2`, `WRK-02-C2` | Native Ubuntu Server 1 provisioning (`install_ubuntu.sh`), PostgreSQL 16 pooled execution, Redis 7 broker, live Celery worker + Beat execution, Nginx TLS reverse proxy, and systemd restart verification. | Provisioned Ubuntu Server 1 host + TLS certs + PostgreSQL/Redis services. |
| `REM-02` | `LLM-01-C2`, `MON-02-C2`, `DEP-01-C2`, `PRF-01-C2` | Native Ubuntu Server 2 GPU setup (`install_llm_server.sh`), vLLM CUDA boot with real model weights, `smoke_test_server2.py --base-url http://<SERVER2>:8000/v1`, live Prometheus `/metrics` scraping, and concurrency/token latency benchmark. | Provisioned GPU host (`>= 14 GiB` VRAM) with CUDA drivers on private VLAN. |
| `REM-03` | `FSI-01-C3` | Live FortiSIEM Supervisor API rule/incident ingestion test (`STAGING_INTEGRATION_TESTS` read-only poll, verifying field mapping across real SIEM schemas). | Network connectivity + read-only service credentials to live FortiSIEM instance. |
| `REM-04` | `PIL-02-C2` | Controlled SOC Pilot `SHADOW` trial run followed by gated `ANALYST_ASSISTED` pilot run under SOC Lead supervision. | Live Server 1 + Server 2 + real FortiSIEM feed + approved rule policies. |
| `REM-05` | `QGS-02-C3` | Empirical Verdict Accuracy & G8 Certification + Confidence Calibration: requires `>= 10 VERIFIED_TP` and `>= 10 VERIFIED_FP` (per rule minimum `>= 5`) and `>= 30` independent verified human-adjudicated cases for calibration (`calibrated_probability`). | Independent SOC Tier-2/3 human ground-truth labeling & real LLM evaluation cohort. |
| `REM-06` | Staging Runner Gate | Re-run `python scripts/run_integration_suite.py --mode STAGING_INTEGRATION_TESTS` and `--mode LIVE_MODEL_VALIDATION` on Server 1 until `overall_status == "PASSED"`. | Items `REM-01` through `REM-03` complete. |

---

## Acceptance Rule for Future Operational Sign-Off

Do **not** mark any of the above `VERIFIED` or claim empirical verdict accuracy until real hardware logs (`smoke_test_server2.py`, `verify_server1.sh`, `run_integration_suite.py`, and Historical Eligibility/Empirical Evaluation outputs on real adjudicated incidents) confirm passing execution without simulated fallbacks.

