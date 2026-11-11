# Phase 8.1 Remaining Work & Staging/Production Prerequisites (Stage 14)

## 1. Blocked Infrastructure & Live Hardware Milestones (`NOT_TESTED`)

Until authorized non-production staging hardware/appliances are connected, the following 6 acceptance criteria cannot be certified:

| Feature Criterion | Blocked Component | Required Verification When Infrastructure Connects |
|---|---|---|
| `DBM-01-C2` | Live PostgreSQL (`alembic upgrade head`) | Execute migrations `001->007` and live lock contention (`distributed_locks` + connection pooling) against staging PostgreSQL. |
| `WRK-02-C2` | Live Redis + Celery Worker Daemon | Execute queued `live_triage` & `dry_run` tasks across multi-process Celery workers backed by staging Redis. |
| `LLM-01-C2` | Live Server 2 GPU (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | Measure real inference latency, structured JSON schema adherence, token throughput, and live claim grounding quality. |
| `MON-02-C2` | Live Server 2 vLLM `/metrics` | Verify real GPU VRAM, cache usage, and active slot telemetry ingestion via Prometheus endpoint. |
| `QGS-02-C3` | Live `OPENAI_COMPATIBLE` Simulation Replay | Replace offline simulation placeholder with live Server 2 replay across real historical incidents. |
| `FSI-01-C3` | Live FortiSIEM Supervisor API (`443`) | Execute authenticated REST pull + XML rule sync + incremental watermark test against staging FortiSIEM. |

## 2. Empirical Dataset Accumulation Prerequisites

1. **Balanced Per-Rule Verified History (`>= 30` Cases/Rule, `>= 3` TP and `>= 3` FP):** Local DB contains only `8` non-synthetic human-adjudicated SIEM incidents (`0` CrowdStrike non-ML TPs; Prisma SASE has a 3-incident duplicate burst cluster). Accumulate independent analyst-reviewed TP and FP closures per active rule before attempting `CALIBRATED` / `autonomous_operation_eligible = true`.
2. **Exclude Synthetic Zero-Event Fixtures:** Exclude `PH_RULE_DEBUG_FUNNEL` (`INC-DEBUG-01..06`, `ev_cnt=0`) from rule certification cohorts.
3. **Production Deployment Flags (Do Not Relax):** Keep `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`, `FORTISIEM_MOCK_FALLBACK=false`, `FORTISIEM_VERIFY_SSL=true`, and dedicated staging vs production RepoDeploy Governor configs cleanly separated before deployment.

