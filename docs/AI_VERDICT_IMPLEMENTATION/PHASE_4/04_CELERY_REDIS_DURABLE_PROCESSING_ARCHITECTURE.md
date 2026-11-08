# Report 04: Celery / Redis Durable Incident Processing Architecture (P4-REQ-04)

## 1. Background & Operational Necessity

In prior phases, incident triage and FortiSIEM synchronization executed in-process within FastAPI event loops or background tasks. In a production SOC environment supporting 10,000 incidents per day:
1. **Worker Crash Loss:** If a backend process terminated or was restarted during an LLM inference call, in-flight incidents were dropped without state recording.
2. **Backpressure Starvation:** Bursts of hundreds of simultaneous incoming SIEM webhooks could overwhelm the application server and saturate HTTP worker connections.
3. **Queue Visibility:** SOC managers lacked real-time visibility into backlog depth, retry counts, and dead-lettered failures.

---

## 2. Distributed Celery & Redis Queue Architecture

Phase 4 introduces an asynchronous task execution layer using **Celery** with **Redis 7** as the message broker on Server 1:

```
+-------------------------------------------------------------------------------------------------+
|                                 FASTAPI INGESTION / API WORKERS                                 |
|                                                                                                 |
|   FortiSIEM Webhook / Poll -----> Ingestion Pipeline -----> dispatch_incident_triage()          |
+-------------------------------------------------------------------------------------------------+
                                               |
                                               v
+-------------------------------------------------------------------------------------------------+
|                                     REDIS 7 MESSAGE BROKER                                      |
|                                                                                                 |
|   [ Queue: live_triage ] ---------> High Priority Incident Real-Time Analysis                   |
|   [ Queue: simulation_replay ] ---> Bulk Simulation & Historical Benchmark Replays              |
|   [ Queue: maintenance ] ---------> Telemetry Archival, Token Rollups & DB Cleanup              |
+-------------------------------------------------------------------------------------------------+
                                               |
                                               v
+-------------------------------------------------------------------------------------------------+
|                                  CELERY DISTRIBUTED WORKERS                                     |
|                                                                                                 |
|   - Worker Concurrency: 4 processes per worker unit                                             |
|   - Task Acks Late (task_acks_late=True): Re-delivers task if worker abruptly crashes           |
|   - Prefetch Multiplier = 1: Prevents one worker from hoarding tasks while others are idle     |
|   - Task Soft Limit: 285s / Hard Limit: 300s                                                    |
+-------------------------------------------------------------------------------------------------+
```

---

## 3. Durable Task State Machine

Every asynchronous task is persisted in the Server 1 database table `queued_tasks` across its complete lifecycle:

```
                  +-----------+
                  |  QUEUED   |  (Enqueued in Redis broker)
                  +-----------+
                        |
                        v
                  +-----------+
                  |PROCESSING |  (Worker claimed task; lock acquired)
                  +-----------+
                   /         \
   (Success)      /           \  (Transient Exception)
                 v             v
          +-----------+  +-----------+
          | COMPLETED |  | RETRYING  |  (Exponential backoff with jitter)
          +-----------+  +-----------+
                               |
                               | (Retry Count >= Max Retries: 3)
                               v
                         +-----------+
                         |DEAD_LETTER|  (Persisted error details for analyst review)
                         +-----------+
```

### State Machine Guarantees:
- **Idempotency:** Before executing LLM analysis, the worker checks if the incident already has a validated evaluation matching the current policy. If triaged, it returns the existing verdict without duplicate inference cost.
- **Bounded Exponential Backoff:** Retries use the formula: `delay = (2 ** retry_count) * 2.0 + jitter`.
- **Dead-Letter Containment:** Failing incidents never loop indefinitely. After 3 failed attempts, the task transitions to `DEAD_LETTER` with the full error trace recorded in `queued_tasks.error_message`.

---

## 4. Dual-Mode Dispatcher & Seamless Fallback

To preserve development and testing ergonomics where a live Redis server may not be running, `app/workers/tasks.py` implements a dual-mode dispatcher:

```python
async def dispatch_incident_triage(incident_id, trigger_source="LIVE", is_simulated=False, db=None):
    use_celery = settings.USE_ASYNC_CELERY and is_redis_available()
    if use_celery:
        task = triage_incident_task.apply_async(
            args=[incident_id, trigger_source, is_simulated],
            queue="live_triage"
        )
        return {"dispatch_mode": "CELERY_ASYNC", "task_id": task.id, "status": "QUEUED"}
    else:
        # Fallback to direct async in-process execution with identical state machine
        return await _execute_incident_triage_core(...)
```

---

## 5. Verification Evidence

Test module `backend/tests/test_celery_queues.py` validates:
- `test_celery_configuration_and_queues`: PASSED. Confirms serialization, timezone, queue declarations, and late acknowledgement configuration.
- `test_task_state_machine_transitions`: PASSED. Confirms sequential progression: `QUEUED` -> `PROCESSING` -> `RETRYING` -> `DEAD_LETTER`.

