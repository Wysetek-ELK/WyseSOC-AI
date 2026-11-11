# Phase 9.1 — Regression Test & Build Verification Report

## 1. Automated Verification Summary

| Suite / Command | Scope | Result | Notes / Evidence |
|---|---|---|---|
| `cd backend; python -m pytest --ignore=tests/e2e_browser -v` | Full offline backend unit, integration, adversarial, security, migration & pilot suites | **299 passed, 0 failed, 0 warnings** (281.24s) | Eliminated all 6,072 Python/SQLAlchemy/Pydantic/Alembic warnings without global suppression (`docs/phase9.1/evidence/tests/pytest_backend_full_report.txt`). |
| `cd backend; python -m pytest tests/test_phase9_1_hardening.py -v` | Phase 9.1 provenance separation, historical persistence, prod seed guard, 3-role Pilot RBAC, integration runner guard, deployment LF/unit check | **6 passed, 0 failed, 0 warnings** | Verified under isolated SQLite + local HTTP mock server. |
| `cd frontend; npx tsc --noEmit` | Frontend TypeScript strict check | **0 errors** | Clean compilation across updated UI & `src/lib/provenance.ts`. |
| `cd frontend; npm run test:admin-guide` | Admin Guide data & route contract suite | **7 / 7 passed** | Executed cleanly on Node `--experimental-strip-types`. |
| `cd frontend; npm run build` | Next.js 16.4.5 Turbopack production build | **30 / 30 routes built** | All static/dynamic routes compiled cleanly. |
| `cd backend; python -m pytest tests/e2e_browser/test_phase9_1_ui_e2e.py -v` | Chromium headless role consistency (`Administrator`, `SOC Analyst`, `Read-Only Viewer`), no hardcoded login secret, `HTTP_MOCK` vs `S2 Now: OFFLINE` provenance | **1 passed (5/5 steps), 0 console/page errors** | Evidence: `docs/phase9.1/evidence/frontend/phase9_1_browser_e2e_report.json` + `p91_01..p91_04.png`. |
| `cd backend; python -m pytest tests/e2e_browser/test_phase9_ui_e2e.py -v` (`PHASE9_EVIDENCE_ROOT` redirected) | Phase 9 SOC pilot lifecycle, SHADOW isolation, Analyst override, Supervisor verify, S2 offline fail-closed, Viewer lock | **1 passed (9/9 steps), 0 console/page errors** | Evidence saved to `docs/phase9.1/evidence/frontend/phase9_repro/` (preserving `docs/phase9/` untouched). |
| `cd backend; python -m pytest tests/e2e_browser/test_phase8_2_ui_e2e.py -v` | Issue 1 zero-denominator, Inference Control `DEGRADED (S2 OFFLINE)`, historical live vs simulated workbench badges, AIS Viewer RBAC | **1 passed (4/4 steps), 0 console/page errors** | Historical `docs/phase8.2/` restored after capturing `phase8_2_repro_summary.json`. |
| `cd backend; python -m pytest tests/e2e_browser/test_phase8_1_ui_e2e.py -v` | AIS 3-tier eligibility, `INVALID_MODEL_OUTPUT`, uncalibrated trust cap, Human Review persistence | **1 passed, 0 console/page errors** | Historical `docs/phase8.1/` restored after capturing `phase8_1_repro_report.json`. |
| `cd backend; python -m pytest tests/e2e_browser/test_phase8_ui_e2e.py -v` | End-to-end Phase 8 UI login, AIS gates, dry-run lab, workbench, review queue, Admin Guide | **1 passed, 0 console/page errors** | Historical `docs/phase8/` restored after capturing `phase8_repro_summary.json`. |
| `python scripts/run_integration_suite.py --mode OFFLINE_CONTRACT_TESTS` | Server 1/2 wire contract, PostgreSQL compile + Alembic 008 roundtrip, Celery queue contract, FortiSIEM pull/parser contracts | **PASSED (4/4 contract groups)** | Evidence: `docs/phase9.1/evidence/deployment/offline_contract_results.json`. |
| `python scripts/validate_feature_registry.py` | Feature registry schema, path verification, rollup parity, and Markdown synchronization | **PASSED (19 modules, 44 features, 78 impl, 69 verif)** | Confirmed via CLI validator & `pytest backend/tests/test_feature_registry.py`. |

---

## 2. Explicit Scope Boundaries

- All LLM-backed browser and backend tests above used deterministic local HTTP test servers (`127.0.0.1` HTTP mocks explicitly labeled `HTTP_MOCK` / `MOCK_HTTP_E2E`), or the deterministic `SIMULATED` test provider for historical replay tests (`allow_simulated=True`).
- No remote Server 1 / Server 2 / PostgreSQL / Redis / FortiSIEM deployment or live hardware GPU validation was executed in this closure baseline.
