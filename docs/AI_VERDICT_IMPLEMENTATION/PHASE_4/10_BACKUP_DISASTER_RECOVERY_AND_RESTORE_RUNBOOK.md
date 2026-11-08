# Report 10: Backup, Disaster Recovery & Restore Runbook (P4-REQ-09)

## 1. Disaster Recovery Objectives: RPO & RTO

In accordance with Phase 4 guidelines, disaster recovery metrics must be honestly disclosed rather than claimed as instantaneous or zero-loss:

- **Recovery Point Objective (RPO):**
  - **Standard Daily Snapshot:** **24 hours**.
  - **With Hourly WAL Archival:** **1 hour**.
  - Any incidents triaged between the last WAL archive and a catastrophic physical storage failure must be re-ingested from FortiSIEM (which retains raw logs independently).
- **Recovery Time Objective (RTO):**
  - **Full Restore to Alternate Hardware:** **30 minutes**.
  - Includes OS provisioning, database restore, Alembic verification, and service launch.

---

## 2. Automated Backup Utility (`backend/app/scripts/backup.py`)

`backup.py` creates a point-in-time snapshot of the database and generates a cryptographic manifest:

```bash
# Execute full snapshot backup
python -m app.scripts.backup --db-path /opt/ai-verdict/backend/ai_verdict.db --output-dir /var/backups/ai-verdict/
```

### Generated Manifest Schema (`manifest.json`):
```json
{
  "timestamp": "2026-11-08T17:09:15.285Z",
  "backup_id": "backup_20261108_113915",
  "database_type": "sqlite",
  "artifacts": {
    "database": {
      "file": "ai_verdict.db",
      "sha256": "5ff01fee34dd6545b09e12407d21116b4f02b4a397691fac7d628c6105261eb4",
      "size_bytes": 4337664
    }
  },
  "table_counts": {
    "users": 3,
    "rules": 14,
    "incidents": 128,
    "historical_ground_truth": 128,
    "audit_logs": 85,
    "dry_run_results": 205
  },
  "status": "COMPLETED"
}
```

---

## 3. Safe Restore Utility (`backend/app/scripts/restore.py`)

Restoration is protected by two pre-flight safety gates:
1. **Mandatory Checksum Verification:** Calculates the SHA-256 hash of the archive before touching target storage. If the hash does not match `manifest.json`, restore aborts immediately.
2. **Pre-Restore Rollback Copy:** Preserves the currently active target database as `ai_verdict.db.pre_restore_bak` before overwriting.

```bash
# 1. Validate archive integrity and perform dry-run simulation (No disk modifications)
python -m app.scripts.restore \
  --backup-dir /var/backups/ai-verdict/backup_20261108_113915 \
  --target-db /opt/ai-verdict/backend/ai_verdict.db \
  --dry-run

# 2. Execute live restore
python -m app.scripts.restore \
  --backup-dir /var/backups/ai-verdict/backup_20261108_113915 \
  --target-db /opt/ai-verdict/backend/ai_verdict.db
```

---

## 4. Disaster Recovery Execution Runbook (Step-by-Step)

In the event of total Server 1 failure or data corruption:

### Step 1: Stop Active Services
```bash
systemctl stop ai-verdict-backend ai-verdict-worker ai-verdict-frontend
```

### Step 2: Validate and Restore Backup
```bash
python -m app.scripts.restore \
  --backup-dir /var/backups/ai-verdict/backup_LATEST \
  --target-db /opt/ai-verdict/backend/ai_verdict.db
```

### Step 3: Verify Schema Version
```bash
cd /opt/ai-verdict/backend
./venv/bin/alembic check
./venv/bin/alembic heads
```

### Step 4: Verify Audit Trail Cryptographic Integrity
```bash
./venv/bin/python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.services.audit_service import AuditService

async def check():
    async with AsyncSessionLocal() as s:
        res = await AuditService(s).verify_audit_integrity()
        print('Audit Integrity Status:', res['integrity_status'])
asyncio.run(check())
"
```

### Step 5: Restart Services and Validate Observability
```bash
systemctl start ai-verdict-backend ai-verdict-worker ai-verdict-frontend
curl -s http://127.0.0.1:8000/health | jq .
```

