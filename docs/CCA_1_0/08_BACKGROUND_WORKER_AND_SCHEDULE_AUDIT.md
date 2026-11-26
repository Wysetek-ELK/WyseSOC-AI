# 08 — Background Worker & Schedule Audit

## 1. Discovered Background Infrastructure
1. **Celery + Redis (`backend/app/workers/celery_app.py`, `tasks.py`)**:
   - Configured queues: `live_triage`, `simulation_replay`, `maintenance`.
   - Registered tasks (`tasks.py`):
     - `triage_incident_task` -> routed to `live_triage`, dispatched by `dispatch_incident_triage()`.
     - `run_policy_simulation_task` -> routed to `simulation_replay`, dispatched by `dispatch_policy_simulation()`.
     - `run_dry_run_job_task` -> routed to `simulation_replay`, dispatched by `DryRunService`.
   - In-process fallback: When `USE_ASYNC_CELERY=false` or Redis is unavailable, `dispatch_*` runs tasks in-process asynchronously.
2. **In-Process Continuous Poller (`backend/app/services/fortisiem_scheduler.py` — `SentinelIngestWorker`)**:
   - Started in `FastAPI` `lifespan()` (`main.py:250-255`).
   - Uses `scheduler_state.json` atomic file locking for multi-worker leader election across 4 Uvicorn processes (`_try_claim_or_renew_leadership`, `_claim_or_renew_backlog_lease`).
   - Polls FortiSIEM and drains pending incident AI verdicts (`run_pending_reconciliation_until_drained`).

## 2. Findings & Anomalies

| Component | Location | Finding | Classification | Risk | Recommended Action |
|---|---|---|---|---|---|
| `ai-verdict-scheduler.service` (Celery Beat) | `deployment/systemd/ai-verdict-scheduler.service` & `celery_app.py` | Systemd runs `celery beat`, but `celery_app.py` defines **0 `beat_schedule` jobs**. Actual periodic polling runs in `SentinelIngestWorker` inside Uvicorn. | `POSSIBLY_UNUSED` | `HIGH` | `VERIFY_FIRST` (Confirm `verify_server1.sh` dependency before disabling unit or migrating poller to Beat) |
| `maintenance` Celery Queue | `backend/app/workers/celery_app.py:40-43` | Queue `maintenance` is declared and consumed by `ai-verdict-worker.service`, yet **0 tasks** are routed to it. | `POSSIBLY_UNUSED` | `LOW` | `VERIFY_FIRST` (Retain if reserved for retention cleanup job) |
