# AI VERDICT — PHASE 2: DEPLOYMENT & ROLLBACK GUIDE
## 12. DEPLOYMENT & ROLLBACK GUIDE

---

### 1. Deployment Architecture
Phase 2 changes are entirely application-layer Python services, schemas, and Next.js frontend components.
- **Database Schema Changes:** None. Phase 2 leverages existing JSON/JSONB fields in `incidents.ai_verdict` and relationships, requiring **zero database migrations** and zero downtime.
- **Hardware Prerequisites:** Server 1 (FastAPI backend + Next.js frontend) and Server 2 (Local LLM inference).
- **Environment Variables:** No new environment variables required. Inherits all Phase 1 hardened configurations (`SECRET_KEY`, `APP_ENV`).

---

### 2. Pre-Deployment Verification Checklist
Before deploying Phase 2 to staging or production:
1. Ensure working tree is on branch `feat/phase-2-evidence-grounding`.
2. Run backend test suite:
   ```bash
   cd backend
   python -m pytest tests/test_evidence_normalization.py tests/test_evidence_contracts.py tests/test_evidence_preflight.py tests/test_evidence_grounding.py tests/test_independent_verdict_validator.py tests/test_phase2_integration.py -v
   # Must report 51 passed
   ```
3. Run full regression test suite:
   ```bash
   cd backend
   python -m pytest tests -q
   # Must report 135 passed
   ```
4. Run frontend typecheck:
   ```bash
   cd frontend
   npx tsc --noEmit
   # Must exit with code 0
   ```
5. Build frontend production assets:
   ```bash
   cd frontend
   npm run build
   # Must compile cleanly without errors
   ```

---

### 3. Deployment Steps

#### Step 1: Backend Deployment
1. Pull the approved commit SHA on the target Linux host via SSH.
2. Ensure Python virtual environment dependencies are active.
3. Restart FastAPI service:
   ```bash
   sudo systemctl restart ai-verdict-backend
   ```
4. Verify backend health:
   ```bash
   curl -f http://127.0.0.1:8000/api/system/servers
   ```

#### Step 2: Frontend Deployment
1. Build Next.js application:
   ```bash
   cd frontend && npm run build
   ```
2. Restart Next.js systemd service:
   ```bash
   sudo systemctl restart ai-verdict-frontend
   ```
3. Verify workbench UI responds with HTTP 200.

---

### 4. Rollback Procedure
If unexpected runtime issues occur post-deployment:
1. Revert to the last known stable Phase 1 commit:
   ```bash
   git checkout <PHASE_1_COMMIT_SHA>
   ```
2. Restart backend and frontend services:
   ```bash
   sudo systemctl restart ai-verdict-backend
   sudo systemctl restart ai-verdict-frontend
   ```
3. Verify system stability:
   - Run `python -m pytest tests/test_phase1_security_controls.py -v` (12/12 passing).
   - Check UI at `/ai-triage-workbench`.
4. Stored incidents with Phase 2 verdict data in `incidents.ai_verdict` remain backwards-compatible, as the JSON payload simply contains additional informational keys ignored by Phase 1 code.

