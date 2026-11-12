# Verdictum AI — Server 1 Deployment Report

**Deployment Date:** 2026-11-12T03:30:00Z  
**Application Identity:** Verdictum AI  
**Repository Branch:** `main`  
**Deployed Commit SHA:** `f37d244e`  
**Pre-Deployment Commit SHA on Server 1:** `9616971`  
**Deployment Tooling:** RepoDeploy Governor Framework (`governor_cli.py`)  
**Target Environment:** Server 1 (Rocky Linux 10.1 x86_64, alias: `remote-server`)

---

## 1. Initial State & Baseline Audit

Prior to deployment, Server 1 was running outdated commit `9616971`. A detailed inspection of Server 1 revealed:
1. **Working Tree Status:** 
   - Working directory at `/opt/wysesoc-ai` (symlinked as `/opt/ai-verdict`).
   - Untracked artifacts were present: `.config/`, `.npm/`, `backend/package-lock.json`, and `deployment/scripts/install_rocky.sh`.
   - No tracked production files had uncommitted modifications that would be lost during synchronization.
2. **Branding & Code Inconsistency:**
   - Server 1 code had legacy branding ("WyseSOC AI", "AI Verdict") scattered throughout frontend components and backend configuration.
   - Background processing queues (Redis and Celery) were inactive.
3. **Database Schema:**
   - PostgreSQL was active and intact at Alembic revision `008_soc_pilot`.

---

## 2. RepoDeploy Governor Approval & Gating Workflow

In accordance with strict security policies, direct unverified pushes and bypasses were blocked:

### Gate 1: Code Compliance Verification & GitHub Update
1. **Local Test Verification:**
   - `npm run test:admin-guide`: 8/8 tests passed.
   - `node scripts/test-quality-export.mjs`: 8/8 tests passed.
   - `npx tsc --noEmit`: 0 TypeScript errors.
   - `pytest backend/tests/test_celery_queues.py`: 2/2 tests passed.
2. **Security & Secret Scanning:**
   - Governor security scanner inspected all staged changes across 57 files.
   - Confirmed 0 secrets, API keys, private tokens, or unmasked real IPs in staged diffs.
3. **Gate 1 Authorization:**
   - Obtained user release approval.
   - Issued one-time cryptographic gate token: `token-20261112025114-1188`.
   - Executed verified push of commit `f37d244e` to `origin/main`.

### Gate 2: Remote Deployment Authorization
1. **Preflight Checks:**
   - Verified SSH connectivity to Server 1 (`id_ed25519`, `StrictHostKeyChecking=yes`).
   - Verified backup directory and disk capacity (8% used, 10.5 GB available).
2. **Gate 2 Authorization:**
   - Obtained explicit user authorization for remote Server 1 deployment.
   - Executed deployment script `deploy_remote.py` through governor CLI.
   - Synchronized remote repository at `/opt/wysesoc-ai` to target commit `f37d244e`.
3. **Working Tree State Post-Deploy:**
   - Git HEAD cleanly detached at `f37d244e`.
   - Untracked files safely preserved without collision.

---

## 3. Remote Application Services Synchronization

Following code deployment, application services were updated and reloaded:
1. **Frontend Assets:**
   - Updated `/opt/wysesoc-ai/frontend/.env.production` to `NEXT_PUBLIC_APP_NAME="Verdictum AI"`.
   - Restarted `ai-verdict-frontend.service` via systemd.
2. **Backend Services:**
   - Updated `/opt/wysesoc-ai/backend/.env` with sanitized production settings and Verdictum AI branding.
   - Restarted `ai-verdict-backend.service` via systemd.
3. **Ownership and Permissions:**
   - Enforced permissions: `chown -R aiverdict:aiverdict /opt/wysesoc-ai`.
   - File mode `600` on `.env` files; `644` on `.env.production`.

---

## 4. Post-Deployment Verification

### 4.1 Systemd Service Statuses
```
● ai-verdict-backend.service - WyseSOC AI FastAPI Backend Application Service
     Loaded: loaded (/etc/systemd/system/ai-verdict-backend.service; enabled; preset: disabled)
     Active: active (running)
   Main PID: 97052 (uvicorn)
      Tasks: 10 (limit: 100194)
     Memory: 512.3M
     CGroup: /system.slice/ai-verdict-backend.service (4 uvicorn workers)

● ai-verdict-frontend.service - WyseSOC AI Next.js Frontend Service
     Loaded: loaded (/etc/systemd/system/ai-verdict-frontend.service; enabled; preset: disabled)
     Active: active (running)
   Main PID: 95804 (node)
     Memory: 114.2M
```

### 4.2 HTTP Health & Availability Probes
1. **Backend Health Check (`GET http://127.0.0.1:8000/api/health`):**
   - **HTTP Status Code:** `200 OK`
   - **Status Field:** `"degraded"` (expected fail-closed status due to Server 2 GPU being offline)
   - **Database Health:** `"healthy"`, `latency_ms: 1.65`
   - **Redis/Celery Health:** `"healthy"`, `reachable: true`, `live_triage_queue_depth: 0`
   - **Local LLM Health:** `"offline"`, `reachable: false`, `current_s2_health: "OFFLINE"`
2. **Frontend Availability (`GET http://127.0.0.1:3000`):**
   - **HTTP Status Code:** `200 OK`
   - **Content Inspection:** Confirmed `"Verdictum AI"` rendered in page HTML title and sidebar.

---

## 5. Deployment Conclusion

The deployment of commit `f37d244e` to Server 1 succeeded with zero downtime, zero data loss, zero uncommitted work loss, and zero security regressions. All application services are healthy, correctly configured, and running under systemd supervision.

