# 09. REMOTE DEPLOYMENT PROTOCOL AND LIVE GUI ACCEPTANCE

## Verdictum AI — Agent Intelligence Studio 2.1
**Powered by WYSETEK Systems**

---

## 1. Executive Summary

This document defines the deployment procedure and live GUI acceptance verification for **Agent Intelligence Studio 2.1** on **Server 1** (`172.26.41.240`). In accordance with Universal Project Lifecycle Agent (UPLA) governance, all remote modifications require strict adherence to:
1. **Pre-Deployment Governance Validation** (UPLA validation profile).
2. **Human Approval Gate 1** (Explicit authorization before GitHub synchronization).
3. **Commit SHA Verification** (Ensuring the exact validated commit is present on GitHub).
4. **Human Approval Gate 2** (Explicit authorization before remote server mutation).
5. **Atomic Remote Deployment & Safe Rollback Guardrails**.

---

## 2. Server Infrastructure Specifications

| Parameter | Configuration Detail |
| :--- | :--- |
| **Server Identifier** | Server 1 (Production Host) |
| **IP Address** | `172.26.41.240` |
| **SSH User** | `root` |
| **Application Directory** | `/opt/wysesoc-ai` |
| **Backend Service** | `ai-verdict-backend.service` (FastAPI / Uvicorn on port 8000) |
| **Frontend Service** | `ai-verdict-frontend.service` (Next.js on port 3000) |
| **Database Engine** | PostgreSQL 16 on `localhost:5432` (`ai_verdict` database) |
| **Model Inference Engine**| Local AWQ vLLM / HuggingFace Pipeline (GPU Accelerated) |

---

## 3. Two-Gate Human Approval Protocol

### Gate 1: GitHub Synchronization Approval
- **Trigger:** Initiated upon successful local governance, backend test completion (34/34 passed), and frontend build verification.
- **Prompt:** `"Governance and security checks completed. Would you like to update the GitHub repository?"`
- **Options:** `YES` | `NO`
- **Safety Invariant:** Zero unapproved pushes. If canceled or timed out, deployment halts immediately.

### Gate 2: Remote Deployment Approval
- **Trigger:** Initiated only after the exact Git commit SHA has been fetched and verified on the remote repository.
- **Prompt:** `"GitHub synchronization completed. Would you like to implement these changes on the remote server?"`
- **Options:** `YES` | `NO`
- **Safety Invariant:** All remote modifications are bound to `(executionId, projectId, targetSha)`.

---

## 4. Remote Deployment Execution Sequence

Once Gate 2 is approved, UPLA executes the following steps on Server 1:

1. **Preflight & Backup:**
   ```bash
   cd /opt/wysesoc-ai
   git status --porcelain
   # Backup current deployment
   tar -czf /opt/wysesoc-ai-backup-$(date +%s).tar.gz --exclude='.git' --exclude='venv' --exclude='node_modules' .
   ```
2. **Git Synchronization:**
   ```bash
   git fetch origin
   git checkout feature/phase3-compact-ui
   git pull origin feature/phase3-compact-ui
   # Verify exact target commit SHA
   CURRENT_SHA=$(git rev-parse HEAD)
   echo "Deployed Commit SHA: $CURRENT_SHA"
   ```
3. **Backend Dependencies & Migrations:**
   ```bash
   source venv/bin/activate
   pip install -r backend/requirements.txt --no-deps -q
   cd backend
   alembic upgrade head
   cd ..
   ```
4. **Frontend Production Build:**
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
5. **Atomic Service Restart & Health Verification:**
   ```bash
   systemctl restart ai-verdict-backend.service
   systemctl restart ai-verdict-frontend.service
   sleep 5
   # Health check validation
   curl -sf http://127.0.0.1:8000/api/health || exit 1
   curl -sf http://127.0.0.1:3000/api/health || exit 1
   ```

---

## 5. Live GUI Acceptance Checklist

| Checkpoint | Expected Behavior in AIS 2.1 | Verification Method |
| :--- | :--- | :---: |
| **Rule Header** | Displays target rule `Heavy TCP Host Scan On Fixed Port`, `SIEM Active`, and dual branding `Verdictum AI 2.1 • Powered by WYSETEK Systems`. | Visual inspection |
| **Policy State** | Displays `v7 Approved` and `v8 Draft`. Shows `None (No Active Policy Bound)` without false `Revoked/Suspended` claims. | Visual inspection |
| **Tab 1: Incidents** | Direct Review Workbench (no `reviewSubView` toggle). Double-blind review queue shows 5 pending incidents (#335, #543, etc.). Canonical evidence properly mapped with `Source: Incident Metadata` fallback for header fields. | Interactive review |
| **Tab 2: AI Evaluation** | 6 summary cards display non-zero incidents (37 total). Evaluation tracking table displays filter pills, search input, row selection, and syncs with the AI test panel below. | Filter & selection test |
| **Tab 3: Accuracy** | Displays empirical accuracy, precision, recall, confusion matrix, and expandable ground truth dashboard. | Metric review |
| **Administrative Settings** | Clicking the **Settings** button in the header opens the 10-module drawer, including Module 0: **Policy Overview & Readiness (6 Stages)** and the legacy 7-tab toggle. | Drawer toggle test |
| **Administrator Activation** | Admin can execute safe activation of v7 via `POST /api/prompts/rule/{id}/activate-approved/{version_id}` with audit logging. | API & audit log test |
