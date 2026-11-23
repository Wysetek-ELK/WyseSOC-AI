# AIS 2.2 Report 11: Remote Deployment & GUI Acceptance

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** READY FOR STAGED DEPLOYMENT  

---

## 1. Remote Host Target Architecture

- **Primary Application Server (Server 1):** `172.26.41.240`
- **Target Directories:**
  - Backend: `/opt/wysesoc-ai/backend`
  - Frontend: `/opt/wysesoc-ai/frontend`
- **Systemd Managed Services:**
  - `ai-verdict-backend.service` (FastAPI on port 8000 via Uvicorn)
  - `ai-verdict-frontend.service` (Next.js on port 3000)
  - `ai-verdict-poller.service` (Continuous FortiSIEM ingestion poller)

---

## 2. Preflight Safety & UPLA Deployment Invariants

In accordance with UPLA Operating Mode `FULL_WORKFLOW`:
1. **Gate 1 (GitHub Synchronization):** Local changes must pass governance and security checks, receive explicit user approval via `ask_question`, and be pushed cleanly to GitHub. Remote commit SHA must be verified.
2. **Gate 2 (Remote Deployment):** Remote deployment requires a second separate explicit user approval via `ask_question`.
3. **Automated Remote Preflight:**
   - Pre-deployment backup of `/opt/wysesoc-ai` into timestamped archive (`/opt/backups/wysesoc-ai-<timestamp>.tar.gz`).
   - Clean git pull on Server 1 matching verified commit SHA.
   - Database migration check (`alembic upgrade head`).
   - Atomic service restart: `systemctl restart ai-verdict-backend ai-verdict-frontend`.
   - Health check probe: `curl -f http://127.0.0.1:8000/api/health` and `curl -f http://127.0.0.1:3000`.
   - Safe rollback mechanism if health check fails.

---

## 3. Live GUI Acceptance Verification Matrix

Following deployment to Server 1, the following UI states will be verified in an authenticated browser session:

| Tab | Component | Expected Verification Criteria |
|---|---|---|
| **Tab 1: Review Incidents** | `ReviewIncidentsWorkbench` | Double-blind review interface; raw event payload inspector; double-blind masking active before analyst submission. |
| **Tab 2: Test AI** | `AiTestWorkbench` | Current Incidents card displays **35** (not 0); Abstained card displays **33**; Not Evaluated displays **2**; table populates with 35 operational rows. Model context strip displays `Qwen/Qwen2.5-7B-Instruct-AWQ` and policy `v7 Active`. |
| **Tab 3: Accuracy & Learning** | `AccuracyLearningSummary` | Persistent Population Scope Selector displays both **Current Incident Inventory (35)** and **Cumulative Historical Cohort (65)**. Switching scopes correctly updates metrics without hiding the buttons. Displays `Selective Accuracy: NOT MEASURABLE` with Wilson confidence intervals. |
