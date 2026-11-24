# AIS 2.6d — Workstream 18: Governed Deployment and Runtime Verification Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T17:10:00Z  
**Document Identity:** `docs/AIS_2_6d/18_GOVERNED_DEPLOYMENT_AND_RUNTIME_VERIFICATION.md`  
**Referenced Manifests:**  
- [DEPLOYMENT_IDENTITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/DEPLOYMENT_IDENTITY_MANIFEST.json)
- [POST_DEPLOYMENT_ACCEPTANCE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/POST_DEPLOYMENT_ACCEPTANCE.json)

---

## 1. UPLA Governance Framework Enforced

Verdictum AI operates under the Universal Project Lifecycle Agent (UPLA) framework in `FULL_WORKFLOW` mode (Project ID: `proj-98348ed9ed5e2ba1`). 

Under this governance policy, strict workflow and safety invariants are enforced:
1. **No Unapproved External Mutations:** Autonomous git pushes and remote deployments are denied by default.
2. **Two Separate Explicit Human Approval Gates:**
   - **Gate 1 (GitHub Sync):** Requires explicit human YES/NO approval before staging changes to the remote repository (`https://github.com/Wysetek-ELK/WyseSOC-AI.git`).
   - **Gate 2 (Remote Deployment):** Requires explicit human YES/NO approval before deploying changes to remote servers, verified only against the exact target Git commit SHA.
3. **No Direct SSH / SCP Bypass:** UPLA pre-tool security hooks intercept and block raw terminal SSH or SCP commands targeting production or staging servers.
4. **No Destructive Operations:** Force-pushes, hard resets, and automatic starting of billable cloud resources are strictly prohibited.

---

## 2. Server Inventory and Runtime Status

### Application Server 1 (Existing Deployed Services)
- **Host:** `172.26.41.240` (SSH Port 22, User: `root`, Key: `C:\Users\amits\.ssh\upla_server1_ed25519`)
- **Role:** Full-stack Application Host (Backend API + Next.js Frontend)
- **Deployment Directory:** `/opt/wysesoc-ai`
- **Environment:** `staging`
- **Managed Services:** `ai-verdict-backend.service`, `ai-verdict-frontend.service`
- **Health Check Specification:**
  - Frontend: `curl -fsSI http://127.0.0.1:3000/login`
  - Backend: `curl -fsS http://127.0.0.1:8000/api/health`
- **Current Runtime Status:** Verified healthy from prior deployment (`upla-20261124-152231-d8bb43`).

### GPU Inference Server 2 (LLM Runtime)
- **Host:** `13.204.214.64` (Port 8000)
- **Role:** Dedicated Inference Server (vLLM Engine)
- **Target Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **Context Length:** 8192 tokens max context (7424 input budget / 768 reserved completion)
- **Current Runtime Status:** `STOPPED` (AWS EC2 instance deallocated). Network preflight confirms TCP connection timeout.
- **Billing Protection:** Server 2 is governed under Non-Negotiable Requirement 18 and Checkpoint B. It will only be powered on when explicitly commanded by the operator.

---

## 3. Local Workspace Audit & Code Integrity

All development edits in AIS 2.6d are localized, fully tested, and ready for deployment upon operator approval:
- `backend/app/api/rule_learning.py`: Added support for `INCONCLUSIVE` analyst verdict submissions.
- `backend/app/services/analyst_review_service.py`: Added `INCONCLUSIVE` adjudication handling and review audit tracking.
- `frontend/next.config.ts`: Configured permanent redirects from `/agent-studio` and `/agent-studio/ground-truth` to `/agent-intelligence-studio`.
- `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx`: Updated review buttons, validation, and zero-leakage view.
- `backend/tests/test_ais_2_6d_empirical_integrity.py`: 6 targeted tests enforcing blind review isolation, token budget invariants, zero-denominator safety, and frozen prompt hashes.

---

## 4. Post-Deployment Acceptance Verification Plan

When the operator decides to push changes to Server 1:
1. Complete UPLA governance validation.
2. Record Gate 1 human approval (`upla.ps1 record-approval -Gate github`).
3. Execute governed GitHub sync (`upla.ps1 github-sync`).
4. Record Gate 2 human approval (`upla.ps1 record-approval -Gate deploy`).
5. Execute multi-server remote deploy (`upla.ps1 remote-deploy`), running database migrations, frontend compilation, and health checks on `172.26.41.240`.
