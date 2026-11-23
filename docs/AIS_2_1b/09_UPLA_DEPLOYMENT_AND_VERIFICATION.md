# AIS 2.1b — 09: UPLA Deployment & Verification

## 1. UPLA Governance Lifecycle

- **Execution ID:** `upla-20261122-064605-3abc60`
- **Project ID:** `proj-98348ed9ed5e2ba1`
- **Operating Mode:** `FULL_WORKFLOW`
- **Profile:** `release`
- **Overall Status:** `WARNING` (Non-blocking pre-existing baseline exceptions)
- **Blocked:** `false`
- **Blocking Reasons:** `[]`
- **Workspace Fingerprint:** `c1548f1e5d98f377a18a2ab8b3dd4f55ded365d5c1ff16b91ba082e4f539289b`

---

## 2. Gate 1 & Gate 2 Authorizations

In accordance with UPLA safety invariants:
1. **Gate 1 (GitHub Synchronization):** Awaiting human decision (`YES` / `NO`) via native UI prompt.
2. **Gate 2 (Remote Deployment to Server 1):** Triggered after Gate 1 commit SHA verification on GitHub.

---

## 3. Remote Server Verification Plan

- **Target Server:** Server 1 (`172.26.41.240`)
- **Services:**
  - `soc-backend.service` (FastAPI / Uvicorn on port 8000)
  - `soc-frontend.service` (Next.js on port 3000)
- **Verification Commands:**
  - Systemd status: `systemctl status soc-backend soc-frontend`
  - Health check: `curl http://172.26.41.240:3000/api/health`
  - Headless Chrome CDP Live GUI Acceptance script: `node scripts/run_ais_2_1b_gui_acceptance.mjs`
