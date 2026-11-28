# AIS 3.1 — Workstream 16: Backend, Frontend & Integration Regression Testing

**Machine-Readable Evidence:** [TEST_EXECUTION_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/TEST_EXECUTION_RESULTS.json)

---

## 1. Local Workspace Executed Test Summary

| Component & Suite | Environment | Executed | Passed | Failed | Skipped / Blocked | Notes |
|---|---|---:|---:|---:|---:|---|
| **Backend Core AIS & Security (`pytest`, 16 suites)** | Local Windows venv, in-memory SQLite + ASGITransport mocks | **84** | **84** | **0** | 0 | Includes `test_ais_3_1_holdout_benchmark.py` (5 tests: frozen manifest, token budget, idempotent resume/dedup, RBAC 401/403, Alembic 017 migration, `raw_payload` fallback & `incidentReso` stripping) + AIS 2.4a/2.6f/2.7/2.8/2.9 + Heavy TCP + validator + token + GT isolation + injection + RAG + metrics |
| **Backend Legacy Fixture / Seeded-DB Suites (7 suites)** | Local Windows venv | **31** | — | *(blocked)* | **31** | Excluded cleanly with documented reasons: missing local `fixtures/Incident json.zip` (`test_empirical_benchmark_harness.py` 13, `test_ais_2_4_regression.py` 2, `test_ais_2_3b_1_regression.py` 1, `test_ais_2_3a_integrity.py` 1), unseeded local 0-byte `ai_verdict.db` (`test_v1_2_2a` 9, `test_v1_2_2b` 4), and outdated hardcoded `008_soc_pilot` head assertion (`test_database_migrations.py` 1 vs actual `017_ais31_holdout_benchmark`) |
| **Frontend Unit & UI Integrity (`npm test`, 17 `.mjs` suites)** | Local Node.js `--experimental-strip-types` | **72** | **72** | **0** | 0 | Includes `ais-3-1-ui-integrity.test.mjs` (`3/3` PASS) |
| **Frontend Production Build (`next build`)** | Local Next.js 16.4.5 + TypeScript | **32 routes** | **PASS** | 0 | 0 | Clean compilation after `.next` lock cleanup |
| **Frontend ESLint (`npm run lint`)** | Local ESLint | — | 0 | *(legacy)* | — | Exited `1` (`369` errors, `258` warnings across pre-existing frontend components) |

---

## 2. Deployed Server 1 & Live GPU Integration Verification

| Integration Test Executed Against Live Server 1 (`172.26.41.240`) | Scope & Mode | Result | Verified Outcome |
|---|---|---|---|
| **Remote Deployment Smoke Pytest (`upla` post-checkout)** | Deployed Server 1 PostgreSQL (`test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`) | **PASS** | Exit code `0` |
| **Remote Frontend Production Build** | Deployed `/opt/wysesoc-ai/frontend` (`npm run build`) | **PASS** | Exit code `0`, `ai-verdict-frontend.service` active |
| **Alembic Migration `017_ais31_holdout_benchmark`** | Live Server 1 PostgreSQL | **PASS** | `ais31_benchmark_runs` & `ais31_benchmark_results` created cleanly |
| **Live vLLM `/tokenize` Audit (`100` holdout incidents)** | Server 1 -> Server 2 `Qwen/Qwen3-14B-AWQ` | **PASS (`100/100`)** | `0` overflows, `0` `events == []`, `max = 7317 <= 7424` |
| **Live 5-Incident GPU Pilot (`AIS31-PILOT5-V2-20261128`)** | Server 1 -> Server 2 `Qwen/Qwen3-14B-AWQ` | **PASS (`5/5`)** | `5/5` real GPU completions (`0` failures, `0` leaks) |
| **Full 100-Incident Live Benchmark (`AIS31-FULL100-20261128`)** | Server 1 -> Server 2 `Qwen/Qwen3-14B-AWQ` | **PASS (`100/100`)** | `100/100` completed (`0` failed), idempotent resume confirmed (`executed_in_call=0`) |
| **Live Unauthenticated RBAC Probes (`6/6` endpoints)** | Server 1 HTTP `:80` | **PASS (`6/6`)** | All `6` returned `401 Unauthorized` |
| **Remote Headless Chrome CDP UI Acceptance** | Server 1 `:3000` (`1440x900`) | **PASS** | Zero console errors, zero network errors, zero horizontal overflow |
