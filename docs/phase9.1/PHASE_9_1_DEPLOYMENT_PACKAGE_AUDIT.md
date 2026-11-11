# Phase 9.1 — Deployment Package Consistency Audit (Offline Only)

## 1. Audit Scope

Performed an offline consistency and contract audit across `deployment/scripts/*`, `deployment/systemd/*`, `deployment/nginx/*`, `deployment/logrotate/*`, `deployment/env.production.example`, `backend/alembic/versions/008_soc_pilot.py`, `deployment/scripts/smoke_test_server2.py`, and `scripts/run_integration_suite.py`. Remote SSH access and remote server provisioning were **not** executed per Phase 9.1 scope.

---

## 2. Confirmed Deployment Inconsistencies Found & Remediated

1. **CRLF (`\r\n`) Line Endings on Linux Artifacts:**
   - `deployment/scripts/deploy_server1.sh`, `deployment/scripts/setup_server2_gpu.sh`, `deployment/nginx/ai-verdict.conf`, and `deployment/systemd/ai-verdict-{backend,worker,frontend}.service` contained Windows CRLF line endings that break native Ubuntu Bash execution (`#!/usr/bin/env bash\r`) and Linux systemd/Nginx parsers.
   - **Fix:** Normalized all files under `deployment/` cleanly to Unix LF (`\n`) and added root [`.gitattributes`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/.gitattributes) enforcing `eol=lf` across `deployment/**` and `scripts/*.py`.
2. **Incomplete `ai-verdict-scheduler` & `redis-server` Unit Handling Across Server 1 Scripts:**
   - `install_ubuntu.sh` copied `ai-verdict-scheduler.service` without enabling or starting it in `systemctl enable` / `systemctl restart`.
   - `start_services.sh` omitted `redis-server`, `ai-verdict-worker`, and `ai-verdict-scheduler`.
   - `stop_services.sh` omitted `ai-verdict-scheduler` and `ai-verdict-worker`.
   - `verify_server1.sh`, `deploy_server1.sh`, and `rollback_server1.sh` omitted `ai-verdict-scheduler`.
   - **Fix:** Aligned all 5 scripts so `postgresql`, `redis-server`, `ai-verdict-backend`, `ai-verdict-worker`, `ai-verdict-scheduler`, `ai-verdict-frontend`, and `nginx` are consistently enabled, started/restarted in dependency order, stopped in reverse order, and verified.
3. **Ubuntu Redis Service Alias Dependency:**
   - `ai-verdict-{backend,worker,scheduler}.service` referenced `redis.service`, whereas Ubuntu 22.04/24.04 installs `redis-server.service` (checked by `verify_server1.sh`). Updated `After=` and `Wants=` across all 3 unit files to `redis-server.service`.
4. **Loopback Mock Misclassification Prevention in Integration Tooling:**
   - `deployment/scripts/smoke_test_server2.py` now records `"execution_provenance": "HTTP_MOCK"` (vs `"LIVE_PROVIDER"` only for non-loopback or `--live-server2`) and `"is_loopback_target"`.
   - `scripts/run_integration_suite.py` now explicitly blocks loopback `HTTP_MOCK` targets from reporting `PASSED` in `LIVE_MODEL_VALIDATION` mode (`status="BLOCKED"`, `classification="NOT_TESTED"`), enforced via `test_integration_runner_blocks_loopback_mock_from_live_model_validation`.

---

## 3. Port, Environment Variable & Schema Alignment Verified

- **Ports:** FastAPI Uvicorn on `127.0.0.1:8000` (`ai-verdict-backend.service`, `ai-verdict.conf`, `verify_server1.sh`), Next.js on `127.0.0.1:3000` (`ai-verdict-frontend.service`, `ai-verdict.conf`, `verify_server1.sh`), vLLM default port `8000` (`env.production.example`, `install_llm_server.sh`).
- **Environment Template (`deployment/env.production.example`):** Contains placeholder strings (`REPLACE_WITH_OPENSSL_RAND_HEX_32_...`, `REPLACE_WITH_DB_PASSWORD`, `REPLACE_WITH_SERVER2_PRIVATE_HOST`), `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false"`, `FORTISIEM_MOCK_FALLBACK="false"`, `COOKIE_SECURE="true"`, matching `backend/app/config.py`.
- **Static Checks & Offline Contracts:** Recorded in [`deployment_package_audit.json`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/phase9.1/evidence/deployment/deployment_package_audit.json) and [`offline_contract_results.json`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/phase9.1/evidence/deployment/offline_contract_results.json) (`4/4` offline contracts `PASSED`).

