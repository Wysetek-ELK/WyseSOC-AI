# Verdictum AI — Server 1 Redis & Celery Infrastructure Report

**Report Date:** 2026-11-12T04:10:00Z  
**Target Node:** Server 1 (Rocky Linux 10.1 x86_64)  
**Message Broker:** Redis v8.10.2 (Port 6379)  
**Distributed Task Engine:** Celery v5.7.0 (Python 3.12 Virtualenv)  
**Operational Status:** **ACTIVE & VERIFIED (Zero Queue Lag)**

---

## 1. Background Processing Architecture

Verdictum AI decouples asynchronous incident evaluations, historical simulation replays, and maintenance operations from the FastAPI request/response lifecycle using Redis as an in-memory message broker and Celery as a distributed task worker daemon.

```
+-------------------------------------------------------------+
|                     FastAPI Backend                         |
|   (Producer: dispatches async triage, simulation runs)      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                       Redis Broker                          |
|             (Port 6379 / Memory: 1.34 MB)                   |
|  +---------------------+-------------------+-------------+  |
|  |     live_triage     | simulation_replay | maintenance |  |
|  +---------------------+-------------------+-------------+  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    Celery Worker Daemon                     |
|           (4 Prefork Processes / Concurrency: 4)            |
|  Tasks:                                                     |
|   - app.workers.tasks.triage_incident_task                  |
|   - app.workers.tasks.run_policy_simulation_task            |
|   - app.workers.tasks.run_dry_run_job_task                  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                 Durable State Persistence                   |
|   (PostgreSQL queued_tasks table: PROCESSING -> COMPLETED)  |
+-------------------------------------------------------------+
```

---

## 2. Redis Compilation & Systemd Deployment

### 2.1 Environmental Constraints & Compilation
Server 1 operates in a secure, air-gapped network perimeter with no direct outbound internet route to external RPM mirrors. To install Redis without internet access:
1. Downloaded official `redis-stable.tar.gz` locally.
2. Transferred the archive to Server 1 via SCP to `/tmp/redis-stable.tar.gz`.
3. Extracted source files using standard Python archive libraries.
4. Compiled core server binaries in `/tmp/redis-stable/src` using `make -j4 MALLOC=libc redis-server redis-cli`, avoiding unnecessary auxiliary module compilation failures.
5. Installed binaries to `/usr/local/bin/redis-server` and `/usr/local/bin/redis-cli` (mode `755`).

### 2.2 Systemd Configuration (`/etc/systemd/system/redis.service`)
```ini
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
Type=simple
User=redis
Group=redis
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli shutdown
Restart=always
RestartSec=3
LimitNOFILE=65536
RuntimeDirectory=redis
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
```

### 2.3 Kernel Tuning & Overcommit Configuration
To ensure Redis background snapshots execute reliably without memory allocation failures:
- Applied kernel parameter: `sysctl vm.overcommit_memory=1`.
- Persisted configuration: `/etc/sysctl.d/99-redis.conf`.

### 2.4 Verified Service Telemetry
- **Active State:** `active (running)` under systemd supervision.
- **Port Binding:** `127.0.0.1:6379`.
- **Memory Consumption:** `1.34 MB` (used memory human).
- **Connected Clients:** 11 active worker and backend client connections.
- **CLI Verification:** `redis-cli ping` -> `PONG`.

---

## 3. Celery Worker Configuration & Deployment

### 3.1 Worker Service Definition (`/etc/systemd/system/ai-verdict-worker.service`)
```ini
[Unit]
Description=Verdictum AI Celery Background Worker Service
After=network.target redis.service postgresql.service
Wants=redis.service postgresql.service

[Service]
Type=simple
User=aiverdict
Group=aiverdict
WorkingDirectory=/opt/wysesoc-ai/backend
EnvironmentFile=/opt/wysesoc-ai/backend/.env
ExecStart=/opt/wysesoc-ai/backend/venv/bin/celery -A app.workers.celery_app worker -Q live_triage,simulation_replay,maintenance -c 4 --loglevel=INFO
Restart=always
RestartSec=5s
LimitNOFILE=65535
StandardOutput=append:/var/log/ai-verdict/worker.log
StandardError=append:/var/log/ai-verdict/worker-error.log

[Install]
WantedBy=multi-user.target
```

### 3.2 Queue Configuration & Routing Rules
Configured in `app/workers/celery_app.py`:
- **`live_triage`:** Exchange `ai_verdict`, routing key `incident.live`. Assigned to `triage_incident_task`.
- **`simulation_replay`:** Exchange `ai_verdict`, routing key `simulation.replay`. Assigned to `run_policy_simulation_task` and `run_dry_run_job_task`.
- **`maintenance`:** Exchange `ai_verdict`, routing key `system.maintenance`. Assigned to diagnostic probes and maintenance workflows.
- **Worker Concurrency:** 4 prefork processes (PIDs: 97046, 97047, 97048, 97049).
- **Time Limits:** Hard limit 300 seconds; soft limit 285 seconds.
- **Durability Controls:** `task_acks_late=True`, `task_reject_on_worker_lost=True`.

---

## 4. Live Worker Telemetry & Queue Observability

Executing live inspection against the Celery control plane on Server 1:
```
->  celery@SOC-AI-Agent: OK
        pong
1 node online.
```

### 4.1 Queue Depths
- `live_triage`: **0 pending tasks**
- `simulation_replay`: **0 pending tasks**
- `maintenance`: **0 pending tasks**

### 4.2 Registered Task Signatures
1. `app.workers.tasks.triage_incident_task`
2. `app.workers.tasks.run_policy_simulation_task`
3. `app.workers.tasks.run_dry_run_job_task`

---

## 5. Offline Task Probe & Durable State Machine Validation

To verify end-to-end task dispatch and state transitions without triggering real LLM inference:
1. Executed diagnostic probe `probe_server1_celery.py`.
2. Created a task tracking record in `queued_tasks` table for entity `offline-probe-task-001`.
3. Transitioned task status from `PROCESSING` to `COMPLETED`.
4. Persisted completion timestamp `2026-11-12T03:55:54.520007` with verified JSON payload:
   ```json
   {
     "task_id": "7407947c-2ea4-4be4-9796-7e9999ff2f39",
     "status": "COMPLETED",
     "completed_at": "2026-11-12T03:55:54.520007",
     "result": {
       "probe_result": "PASSED_OFFLINE_VERIFICATION"
     }
   }
   ```
5. Confirmed database persistence and transaction isolation.

---

## 6. Production Safety Controls

In accordance with Phase 3 readiness rules:
- **Autonomous Incident Closure:** Disabled (`ENABLE_AUTO_CLOSURE=false`).
- **SIEM Writeback:** Disabled (`ENABLE_AUTO_SIEM_WRITEBACK=false`).
- **Operating Mode:** Set to `advisory`.
All background processing infrastructure is durable, responsive, and ready for workload scaling.
