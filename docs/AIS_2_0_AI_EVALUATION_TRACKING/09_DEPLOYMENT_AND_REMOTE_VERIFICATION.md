# Phase 9: Deployment & Remote Verification Runbook

## 1. Deployment Overview & Preconditions
In accordance with UPLA `FULL_WORKFLOW` policy, deployment to production infrastructure follows a strict two-gate procedure:
1. **Gate 1: GitHub Synchronization**
   - Pre-condition: All unit and regression tests pass locally, frontend build succeeds, working tree is clean.
   - Action: Push commit to remote branch `feature/phase3-compact-ui` on GitHub.
   - Verification: Local commit SHA and GitHub origin commit SHA must match exactly.
2. **Gate 2: Remote Deployment to Server 1 (`172.26.41.240`)**
   - Pre-condition: Gate 1 verified. User provides explicit interactive authorization.
   - Target Host: `root@172.26.41.240` (Server 1 - Control Plane & Backend).
   - Target Path: `/opt/wysesoc-ai`
   - Actions:
     - Pull latest commit on remote branch matching verified SHA.
     - Execute database migrations (`alembic upgrade head`) if any.
     - Rebuild/restart systemd services (`wysesoc-backend`, `wysesoc-frontend`).
     - Execute remote health checks and verify PostgreSQL record integrity.

---

## 2. Remote Verification Commands

### Backend Service Status & Health:
```bash
systemctl status wysesoc-backend.service --no-pager
curl -s http://127.0.0.1:8000/api/health | jq .
```

### AIS Evaluation API Verification:
```bash
# Query Heavy TCP Host Scan rule status
curl -s "http://127.0.0.1:8000/api/ais/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/evaluation-status?limit=5" | jq .
```

### PostgreSQL Live Data Verification:
```sql
SELECT 
    COUNT(*) AS total_incidents,
    COUNT(CASE WHEN pv.id IS NOT NULL AND pv.is_simulated = FALSE THEN 1 END) AS evaluated_incidents,
    COUNT(CASE WHEN ar.id IS NOT NULL THEN 1 END) AS reviewed_incidents
FROM incidents i
LEFT JOIN pilot_verdicts pv ON pv.incident_id = i.incident_id
LEFT JOIN analyst_verdict_reviews ar ON ar.incident_id = i.incident_id
WHERE i.rule_id = '40498741-ee6b-4a71-9101-0d6d3f77154c';
```

---

## 3. Rollback Procedure
If remote health checks fail:
1. Revert git working tree to previous verified commit SHA.
2. Re-run `systemctl restart wysesoc-backend wysesoc-frontend`.
3. Verify service recovery via `/api/health`.
