# AIS 3.1 — Workstream 17: Server 1 Deployment & Remote GUI Acceptance

**Deployment Engine:** UPLA (`FULL_WORKFLOW`, `release` profile)  
**Verified Deployed Commit SHA (Server 1):** `8c760c3b9f7957ad4283678ff1f8d1a31dd5dd96` (`feature/phase3-compact-ui`)  
**Previous Server 1 SHA Recorded for Rollback:** `7615325d6360c02ea06cf9613a7ae5df3095f5b4`  
**Deploy Path:** `/opt/wysesoc-ai` on `172.26.41.240` (`verdictum-core-01`)

---

## 1. Authorized UPLA Deployment Execution

Two authorized Gate 1 (`GITHUB`) -> Gate 2 (`DEPLOYMENT`) cycles executed cleanly:
1. **`upla-20261128-095647-fadc65`** -> `fff9ff61b24458ad6d28b81f0398baeab6567859`: Initial AIS 3.1 backend, Alembic migration `017_ais31_holdout_benchmark`, frontend UI fixes, and initial audit artifacts.
2. **`upla-20261128-102224-f64f6e`** -> `8c760c3b9f7957ad4283678ff1f8d1a31dd5dd96`: Evidence-plumbing fix (`inc.raw_payload` fallback for aggregated FortiSIEM incidents) and `incidentReso` leakage guard hardening discovered in Pilot Cycle 1.

Both deployments verified:
- Pre-deploy backup metadata written to `/var/backups/ai-verdict/`.
- `alembic upgrade head` succeeded (`017_ais31_holdout_benchmark`).
- Server-side `pytest` and `npm run build` succeeded on `/opt/wysesoc-ai`.
- `ai-verdict-backend.service` & `ai-verdict-frontend.service` restarted and verified active (`http://127.0.0.1:8000/api/health` + `http://127.0.0.1:3000/login` returned HTTP `200`).
- **Server 2 (`13.204.214.64:8000`, `Qwen/Qwen3-14B-AWQ`) was NEVER touched, restarted, stopped, or modified.**

---

## 2. Live Remote GUI Verification (`http://172.26.41.240:3000`, `1440x900` CDP)

Captured real Chromium headless screenshots in `docs/AIS_3_1/screenshots/`:
1. [`01_human_review_queue_certification.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/01_human_review_queue_certification.png) & [`02_human_review_queue_holdout_scrolled.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/02_human_review_queue_holdout_scrolled.png):
   - Verified `AIS_3_0_INDEPENDENT_HOLDOUT_100 (100)` selected, **My Human Reviews `100/100`** preserved, **2nd Reviews `0/100`**, **GT-3 Certified `0`**, **Conflicts `0`**, **Benchmark Eligible `100`**, **Bench Executed `100`**, **Bench Completed `100`**, **Quarantined `0`**.
   - Verified stale `AIS 2.6e`, `AIS 2.7`, `All 20 Cohort`, `Priority 5 Pilot`, and `Remaining 15` strings removed (`All 100 Cohort` active, Vendor chips showing `FortiSIEM` & `FortiGate / Firewall`, Exposure showing `No Detected Exposure` & `Historical / AI Masked`, sidebar `Qwen3-14B-AWQ (Active)`).
2. [`03_agent_intelligence_studio_overview.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/03_agent_intelligence_studio_overview.png), [`05_agent_intelligence_studio_accuracy.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/05_agent_intelligence_studio_accuracy.png), & [`06_agent_intelligence_studio_ais31_card.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/06_agent_intelligence_studio_ais31_card.png)
3. [`04_detection_intelligence.png`](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/screenshots/04_detection_intelligence.png)

- **Browser Telemetry:** `0` console exceptions, `0` failed network responses (`4xx/5xx`), and `overflowX: false` across all tested routes.
