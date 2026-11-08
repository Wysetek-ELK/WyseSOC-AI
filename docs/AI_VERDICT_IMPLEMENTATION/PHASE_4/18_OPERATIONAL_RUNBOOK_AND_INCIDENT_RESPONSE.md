# Report 18: Operational Runbook & Incident Response (P4-REQ-08 / P4-REQ-09)

## 1. Daily Operations & Health Monitoring

### System Health Inspection:
```bash
# Query component-level health endpoint
curl -s http://127.0.0.1:8000/health | jq .

# Scrape Prometheus metrics
curl -s http://127.0.0.1:8000/metrics | grep ai_verdict
```

### Checking Systemd Service Units:
```bash
# Verify backend, worker, and frontend status
systemctl status ai-verdict-backend ai-verdict-worker ai-verdict-frontend

# Inspect live application logs
journalctl -u ai-verdict-backend -n 100 --no-pager
journalctl -u ai-verdict-worker -n 100 --no-pager
```

---

## 2. Standard Maintenance Procedures

### A. Executing Database Migrations:
```bash
cd /opt/ai-verdict/backend
sudo -u aiverdict ./venv/bin/alembic check
sudo -u aiverdict ./venv/bin/alembic upgrade head
```

### B. Performing Automated Snapshot Backup:
```bash
sudo -u aiverdict ./venv/bin/python -m app.scripts.backup \
  --db-path /opt/ai-verdict/backend/ai_verdict.db \
  --output-dir /var/backups/ai-verdict/
```

### C. Rotating Audit Signing Secret:
1. Update `AUDIT_SIGNING_KEY` in `/opt/ai-verdict/backend/.env`.
2. Restart backend and worker:
   ```bash
   systemctl restart ai-verdict-backend ai-verdict-worker
   ```
3. Previous audit entries remain verifiable because `key_id` records the key epoch.

---

## 3. Incident Response Playbooks

### Playbook 1: Local LLM GPU Server 2 Becomes Unreachable
- **Symptoms:** `/health` reports `local_llm.status = "offline"`, `circuit_breaker_state = "OPEN"`, and live triage produces `REQUIRES_ATTENTION` with abstention reason `LOCAL_LLM_UNAVAILABLE`.
- **Diagnosis:**
  ```bash
  # Check Server 2 connectivity from Server 1
  curl -m 5 -s http://10.10.20.5:8000/v1/models | jq .
  ```
- **Remediation:**
  1. SSH into Server 2 (`ssh -i key.pem ubuntu@10.10.20.5`).
  2. Inspect vLLM service: `systemctl status llm-server`.
  3. Check GPU status: `nvidia-smi`. Look for GPU memory exhaustion or driver errors.
  4. Restart vLLM service: `sudo systemctl restart llm-server`.
  5. Once Server 2 responds, Server 1's circuit breaker will automatically transition from `OPEN` -> `HALF_OPEN` -> `CLOSED` within 30 seconds.

### Playbook 2: Celery Worker Queue Backlog Accumulation
- **Symptoms:** `/metrics` reports `ai_verdict_queue_depth > 500`.
- **Diagnosis:**
  ```bash
  # Check Redis queue length
  redis-cli llen live_triage
  ```
- **Remediation:**
  1. Inspect worker processes: `systemctl status ai-verdict-worker`.
  2. If tasks are stalled on deadlocks, restart worker: `systemctl restart ai-verdict-worker`.
  3. If volume exceeds single-worker processing capacity, increase concurrency in `deployment/systemd/ai-verdict-worker.service` (`-c 8`).

### Playbook 3: Audit Log Tampering Alert
- **Symptoms:** Routine verification script reports `integrity_status = "TAMPER_DETECTED"`.
- **Diagnosis:**
  ```bash
  sudo -u aiverdict ./venv/bin/python -c "
  import asyncio
  from app.database import AsyncSessionLocal
  from app.services.audit_service import AuditService
  async def run():
      async with AsyncSessionLocal() as s:
          print(await AuditService(s).verify_audit_integrity())
  asyncio.run(run())
  "
  ```
- **Remediation:**
  1. Identify affected `tampered_ids`.
  2. Cross-reference PostgreSQL Write-Ahead Log (WAL) or transaction logs to identify database user and time of unauthorized modification.
  3. Isolate affected records and initiate forensic incident investigation.

