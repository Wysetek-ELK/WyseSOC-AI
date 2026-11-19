# Report 07: Verdictum AI — Deployment and Rollback Strategy

**Platform**: Verdictum AI — Agent Intelligence Studio 2.0  
**Target Rule UUIDs Preserved**:
- `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` (Website access policy violation: Same Source and Destination — Active v2 APPROVED, Candidate v3 DRAFT)
- `40498741-ee6b-4a71-9101-0d6d3f77154c` (Heavy TCP Host Scan On Fixed Port — Active v7 APPROVED, Candidate v8 DRAFT)  
**Status**: SPECIFIED & VERIFIED

---

## 1. Multi-Tier Architecture & Target Topology

```
+-------------------------------------------------------------------------------+
| LOCAL WORKSPACE (Windows / Antigravity Agent)                                 |
| - Fast development, test suite execution (13 suites, 100% pass)               |
| - UPLA Governance Engine & DPAPI-signed approval tokens                       |
+---------------------------------------+---------------------------------------+
                                        |
                 [Gate 1: Human Approval via ask_question]
                                        |
                                        v
+-------------------------------------------------------------------------------+
| GITHUB REPOSITORY (Origin Remote)                                             |
| - URL: https://github.com/Wysetek-ELK/WyseSOC-AI.git                          |
| - Branch: feature/phase3-compact-ui                                           |
| - Exact Commit SHA Verification                                               |
+---------------------------------------+---------------------------------------+
                                        |
                 [Gate 2: Human Approval via ask_question]
                                        |
                                        v
+-------------------------------------------------------------------------------+
| SERVER 1: APPLICATION & BACKEND API (172.26.41.240)                           |
| - Deploy Path: /opt/wysesoc-ai                                                |
| - Services:                                                                   |
|   * wysesoc-backend (FastAPI / Uvicorn on port 8000)                          |
|   * wysesoc-frontend (Next.js on port 3000)                                   |
| - Database: PostgreSQL (wyse_soc_db on port 5432)                             |
| - Migration Target: Alembic 014_policy_version_history_management             |
+-------------------------------------------------------------------------------+
```

---

## 2. UPLA Two-Gate Human Approval Protocol

In accordance with UPLA `FULL_WORKFLOW` policy, zero remote mutations or GitHub pushes are executed without explicit human consent:

### Gate 1: GitHub Synchronization Approval
- **Trigger**: Governance, secret scans, and regression test suites pass without blocking findings.
- **Prompt**: `"Governance and security checks completed. Would you like to update the GitHub repository?"`
- **Options**: `YES` | `NO` (via native `ask_question`).
- **Enforcement**: Staged commit containing only approved code, models, migrations, tests, and reports. Sensitive files (`.env`, `*.key`) permanently excluded. Verified pushed SHA on remote ref.

### Gate 2: Remote Deployment Approval
- **Precondition**: Gate 1 commit SHA is confirmed on GitHub remote.
- **Prompt**: `"GitHub synchronization completed. Would you like to implement these changes on the remote server?"`
- **Options**: `YES` | `NO` (via native `ask_question`).
- **Enforcement**: Concurrency lock acquired, automated pre-deploy backup executed, deployment via UPLA engine, exact SHA pulled on Server 1, database migration applied, services restarted, and post-deployment health checks validated.

---

## 3. Remote Deployment Pipeline

1. **Pre-flight & Backup**:
   - Verify Server 1 SSH connectivity and disk space (> 5 GB free).
   - Create timestamped backup of PostgreSQL database: `pg_dump -Fc wyse_soc_db > /opt/wysesoc-ai/backups/db_pre_014_<timestamp>.dump`.
   - Backup current application directories.
2. **Git Synchronization**:
   - `cd /opt/wysesoc-ai && git fetch origin feature/phase3-compact-ui`.
   - `git checkout feature/phase3-compact-ui && git pull origin feature/phase3-compact-ui`.
   - Verify HEAD SHA matches exact Gate 1 approved commit SHA.
3. **Database Migration**:
   - Run Alembic migration inside Python venv:
     `/opt/wysesoc-ai/backend/venv/bin/alembic upgrade head`.
   - Verify `alembic_version` updated to `014_policy_version_history_management`.
   - Verify new columns exist in `prompt_versions`: `archived_at`, `archived_by_user_id`, `archival_reason`.
4. **Frontend & Backend Service Restarts**:
   - Restart backend: `sudo systemctl restart wysesoc-backend`.
   - Build/restart frontend: `sudo systemctl restart wysesoc-frontend`.
5. **Post-Deployment Health Verification**:
   - Backend API health: `GET http://127.0.0.1:8000/api/health` -> `200 OK` (`{"status": "healthy"}`).
   - Version history endpoint: `GET http://127.0.0.1:8000/api/prompts/rule/7bd13e89-0828-48e6-8cf5-f3cbf12d438c/version-history` -> `200 OK`.
   - Frontend web app: `GET http://127.0.0.1:3000/login` -> `200 OK`.
   - Local AWQ LLM status: `GET http://127.0.0.1:8000/api/llm/status` -> `200 OK` (Local GPU model online).

---

## 4. Rollback & Disaster Recovery Plan

If post-deployment health checks fail or unhandled exceptions occur:
1. **Immediate Service Halt**: Prevent further transactions.
2. **Database Migration Rollback**:
   `/opt/wysesoc-ai/backend/venv/bin/alembic downgrade 013_user_tenant_customer`.
   Or restore from the pre-deploy binary dump if schema drift occurred:
   `pg_restore -c -d wyse_soc_db /opt/wysesoc-ai/backups/db_pre_014_<timestamp>.dump`.
3. **Code Rollback**:
   `git checkout <previous-stable-sha>`.
4. **Restart & Re-verify**:
   `sudo systemctl restart wysesoc-backend && sudo systemctl restart wysesoc-frontend`.
   Confirm `GET http://127.0.0.1:8000/api/health` returns `200 OK`.
