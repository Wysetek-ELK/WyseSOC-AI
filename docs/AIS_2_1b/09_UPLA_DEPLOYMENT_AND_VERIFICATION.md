# AIS 2.1b — 09: UPLA Deployment & Verification

## 1. UPLA Governance Lifecycle

- **Execution ID:** `upla-20261122-064926-40ca43`
- **Project ID:** `proj-98348ed9ed5e2ba1`
- **Operating Mode:** `FULL_WORKFLOW`
- **Profile:** `release`
- **Final Execution Status:** `COMPLETED_FULL_WORKFLOW`
- **Blocked:** `false`
- **Blocking Reasons:** `[]`
- **Workspace Fingerprint:** `f3c9a35a9b1bc655c32fad98dc531208cd7363501ad1ca016cab224f6655bc8b`

---

## 2. Gate 1 & Gate 2 Authorizations & Execution

In accordance with UPLA safety invariants:
1. **Gate 1 (GitHub Synchronization):**
   - Approval ID: `apr-71bb0a0c1b71`
   - Target: `https://github.com/Wysetek-ELK/WyseSOC-AI.git@feature/phase3-compact-ui`
   - Decision: `YES` (Human Authorized)
   - Status: `SYNCED_AND_VERIFIED`
   - Commit SHA: `d0046375b86ba84db06eff15811bd3ea4bdcf01a`
   - Remote SHA Verified: `true` [Live GitHub Verified]

2. **Gate 2 (Remote Deployment to Server 1):**
   - Approval ID: `apr-76d9121d5a8f`
   - Target: `server-1@d0046375b86ba84db06eff15811bd3ea4bdcf01a`
   - Decision: `YES` (Human Authorized)
   - Status: `DEPLOYED_AND_VERIFIED`
   - Rollback Status: `NOT_NEEDED`
   - Deployed Server: Server 1 (`172.26.41.240`, Application Role)

---

## 3. Remote Server Verification Results

- **Remote Commands Executed on Server 1:**
  1. `SSH preflight PASSED (root@172.26.41.240): prevSha=58f81813b7d6f5acb8a646994909cc72f33bb49c`
  2. `Backup metadata recorded at /var/backups/ai-verdict/prev-sha-upla-20261122-064926-40ca43.txt`
  3. `Checked out and verified exact Git SHA d0046375b86ba84db06eff15811bd3ea4bdcf01a in /opt/wysesoc-ai`
  4. `Executed remote command OK: cd /opt/wysesoc-ai/backend && ./venv/bin/alembic upgrade head`
  5. `Executed remote command OK: cd /opt/wysesoc-ai/backend && ./venv/bin/pytest tests/test_ais_heavy_tcp_e2e.py tests/test_rule_learning_platform.py tests/test_api_422_remediation.py -q`
  6. `Executed remote command OK: cd /opt/wysesoc-ai/frontend && npm run build`
  7. `Executed remote command OK: systemctl restart ai-verdict-backend.service ai-verdict-frontend.service`
  8. `Health check PASSED on ports 8000 (FastAPI) and 3000 (Next.js)`

- **Live GUI Acceptance via Headless Chrome CDP (`scripts/run_ais_2_1b_gui_acceptance.mjs`):**
  - Viewports Tested: `1440x900`, `1280x800`, `1727x972`, `1920x1080`
  - Compact Toolbar & Context Notice: Verified
  - Prioritized Summary Cards (4 Cards + Secondary Strip): Verified
  - Dominant Table Visibility: `tableTop: 522px`, visible on 1440x900 without scrolling
  - Zero Horizontal Scrolling: Verified across all viewports $\ge 1280\text{px}$
  - Screenshots Captured: 9 high-resolution images in `docs/AIS_2_1b/screenshots/`

