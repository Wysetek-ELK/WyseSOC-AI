# Remaining Work, Dependencies & Next Priorities

- **Updated At:** 2026-11-10T19:55:00+05:30
- **Repository Commit:** `0148142` (`0148142f3abd6dad87a903b90f7b25edb8d41def`)
- **Registry Reference:** [`docs/FEATURE_IMPLEMENTATION_STATUS.md`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/FEATURE_IMPLEMENTATION_STATUS.md)

---

## 1. Environmental & Hardware Blockers Outside Dry-Run Sandbox

1. **Live Server 2 vLLM GPU Validation (`LLM-01`, `MON-02`, `QGS-02`):**
   - *Status:* `PARTIAL` verification (offline client/contract/fail-closed logic verified; physical GPU hardware unreachable in local sandbox).
   - *Required Action:* Execute `OPENAI_COMPATIBLE` triage, Prometheus `/metrics` scraping, and live G8 policy simulation against an online Server 2 vLLM deployment with real quantized weights (`AWQ`/`FP8`) and verify structured `supporting_claims` compliance rate on real model generations.
2. **Live FortiSIEM Supervisor API Roundtrip (`FSI-01`):**
   - *Status:* `PARTIAL` verification.
   - *Required Action:* Verify TLS credentials, pagination checkpoints, triggering-event enrichment, and rule XML fetch directly against target FortiSIEM Supervisor host in staging.
3. **Production PostgreSQL + Redis + Celery Cluster Execution (`DBM-01`, `WRK-02`):**
   - *Status:* `PARTIAL` verification (SQLite in-memory tests + worker import/unit tests pass).
   - *Required Action:* Run `alembic upgrade head` against staging PostgreSQL, verify `migrate_sqlite_to_postgres.py`, start dedicated Celery `live_triage` and `simulation` workers with Redis, and verify multi-process concurrency locks (optionally upgrading process-local `_get_incident_lock` to PostgreSQL advisory locks or Redis distributed locks for multi-worker deployments).

---

## 2. Functional & Calibration Gaps Remaining

1. **Empirical Calibration Corpus Accumulation (`VTC-01`, `VTC-02`, `G8`):**
   - *Status:* Implemented calibration guardrails correctly suppress calibration claims and cap trust scores at `<= 6/10` when rules have `< 30` balanced adjudicated incidents.
   - *Next Priority:* Curate `>= 30` independently verified TP and FP ground-truth incidents per priority detection rule so G8 empirical simulation scores and `CalibrationEvaluator` reliability curves become empirically populated rather than `INSUFFICIENT_DATA` / `NOT_CALIBRATED`.
2. **Automated Frontend Browser E2E Suite (`FEU-01`, `FEU-02`, `TST-02`):**
   - *Status:* Frontend compiles cleanly with zero TypeScript errors (`npx tsc --noEmit`) and passes `npm run test:admin-guide`, while multi-tab React interactive DOM/API flows remain untested in headless Chromium.
   - *Next Priority:* Add Playwright integration tests covering login, Agent Intelligence Studio rule switching/approval UI, AI Triage Workbench canonical evidence tab, and Verdict Intelligence dashboards.
3. **Production Security Settings Hardening Validation:**
   - Ensure staging/production `.env` enforces `APP_ENV=production`, a non-default >=32-byte `SECRET_KEY`, `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`, and restricted CORS/TLS ingress before any live cutover.

