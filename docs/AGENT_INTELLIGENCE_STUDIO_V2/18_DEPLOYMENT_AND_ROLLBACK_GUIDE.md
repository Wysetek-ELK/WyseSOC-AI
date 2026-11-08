# 18. DEPLOYMENT AND ROLLBACK OPERATIONAL GUIDE

## Standard Operating Procedures (SOP)

This document outlines the operational procedures for deploying, verifying, and rolling back Agent Intelligence Studio 2.0.

> [!IMPORTANT]
> In strict compliance with the **RepoDeploy Governor Rules**, zero direct unverified `git push` operations are executed. All deployments require automated pre-flight testing and explicit two-stage user authorization.

---

## 1. Pre-Deployment Verification Checklist

Before initiating any deployment or git commit, execute the following automated verification suite:

1. **Backend Test Suite Verification:**
   ```powershell
   python -m pytest backend/tests -v
   ```
   - Must achieve 100% pass rate (177/177 tests passing).
   - Ensure zero regressions in Phase 1 security controls or Phase 2 claim grounding.
2. **Frontend Production Build Verification:**
   ```powershell
   npm --prefix frontend run build
   ```
   - Must exit with code 0.
   - Zero TypeScript errors.
   - 28/28 routes successfully prerendered / compiled.
3. **Database Migration Verification:**
   ```powershell
   cd backend
   alembic current
   ```
   - Must show head revision `005_agent_intelligence_studio_v2`.
4. **Secrets & Network Isolation Verification:**
   - Confirm no private keys, `.env` credentials, or production public IP addresses are staged.

---

## 2. Deployment Procedure

Once pre-flight checks are verified and authorization is granted:

### Step 1: Database Migration (Staging / Production)
Run the database upgrade script within the virtual environment:
```bash
alembic -c backend/alembic.ini upgrade head
```
*Verification:* Query `alembic_version` table to verify current revision is `005_agent_intelligence_studio_v2`.

### Step 2: Backend Service Restart
Restart the FastAPI application and Celery workers:
```bash
systemctl restart ai-verdict-backend
systemctl restart ai-verdict-celery
```
*Health Check:*
```bash
curl -f http://127.0.0.1:8000/api/health
```
Expect HTTP 200 with database status `healthy`.

### Step 3: Frontend Deployment
Deploy the Next.js production build:
```bash
npm --prefix frontend run build
systemctl restart ai-verdict-frontend
```

---

## 3. Post-Deployment Validation

1. Navigate to `/agent-intelligence-studio`.
2. Inspect the Rules Directory Table:
   - Verify Archetype Badges and Definition Status Badges render correctly.
3. Open `PH_RULE_LARGE_OUTBOUND_XFER`:
   - Verify Quality Score gauge displays.
   - Verify all 6 tabs load (Policy Editor, Quality Gates, SIEM Semantics, Evidence Contract, Simulation Lab, Drift & Monitoring).
4. Run a test bulk audit on a sample of 10 rules.

---

## 4. Rollback Procedures

### Scenario A: Rollback of a Single Policy Version
If a specific approved policy version exhibits unexpected triage behavior in production:
1. Open the rule in Agent Intelligence Studio (`/agent-intelligence-studio`).
2. Navigate to the **Policy Editor** tab.
3. In the version history dropdown, select the previous stable version (e.g. Version 1).
4. Click **"Rollback to this Version"**.
5. The system creates a new version ($N+1$) with the stable content, atomically updates the Evidence Contract, and logs an HMAC audit event. **Zero downtime is incurred.**

### Scenario B: Database & Code Rollback (Emergency)
If an unexpected schema incompatibility or critical runtime regression occurs post-deployment:
1. **Revert Database Migration:**
   ```bash
   alembic -c backend/alembic.ini downgrade 004_postgres_and_hardening
   ```
2. **Revert Git Branch:**
   ```bash
   git checkout main
   ```
3. **Restart Services:**
   ```bash
   systemctl restart ai-verdict-backend
   systemctl restart ai-verdict-celery
   systemctl restart ai-verdict-frontend
   ```
4. Verify system health at `/api/health`.
