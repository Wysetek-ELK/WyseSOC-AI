# Phase 9 — Deployment Readiness Assessment

**Assessment Mode:** Offline Configuration, Syntax, Packaging & Static Security Audit  
**Remote Server Deployment Status:** `NOT_DEPLOYED` (out of scope for Phase 9 development closure)

---

## 1. Deployment Artifacts Inventory (Native Ubuntu LTS, No Docker)

| Component | Artifact Path | Phase 9 Status |
|---|---|---|
| Production Env Template | `deployment/env.production.example` | Updated: Removed hardcoded private IP (`10.x.x.5`), added `LOCAL_LLM_CONTEXT_BUDGET=4096` and `LOCAL_LLM_MAX_TOKENS=512`, enforced `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false"`, `FORTISIEM_MOCK_FALLBACK="false"`. |
| Server 1 Installer | `deployment/scripts/install_ubuntu.sh` | Audited & `bash -n` verified: PostgreSQL, Redis, Nginx, Node 22 build, Python venv, Alembic head, systemd & ufw configuration, placeholder `REPLACE_WITH_SERVER2_PRIVATE_HOST`. |
| Server 1 Verification | `deployment/scripts/verify_server1.sh` | Added & `bash -n` verified: Checks systemd active states, Alembic current, `redis-cli ping`, `nginx -t`, `/api/health`, Frontend `/login`. |
| Server 1 Rollback | `deployment/scripts/rollback_server1.sh` | Added & `bash -n` verified: Restores approved commit SHA cleanly, preserves DB/audit logs, rebuilds frontend, restarts systemd units, executes `verify_server1.sh`. |
| Server 2 Setup | `deployment/scripts/install_llm_server.sh`, `setup_server2_gpu.sh` | Audited & `bash -n` verified: vLLM native setup, NVIDIA driver/VRAM checks, `ufw` restricted to Server 1 IP, logrotate configured. Hardcoded IP removed from `setup_server2_gpu.sh`. |
| Server 2 Smoke Test | `deployment/scripts/smoke_test_server2.py` | Added & contract-tested: Checks `/health`, `/v1/models`, `/v1/chat/completions`, structured JSON output, error handling, `/metrics`. Emits exit code `2` (`NOT_EXECUTED`) when host unreachable. |
| Systemd Services | `deployment/systemd/ai-verdict-*.service` (4 units) | Added `ai-verdict-scheduler.service`; parsed all 4 via Python `configparser` (`[Unit, Service, Install]`, strict systemd sandboxing verified). |
| Reverse Proxy & Logs | `deployment/nginx/ai-verdict.conf`, `deployment/logrotate/ai-verdict` | TLS 1.2/1.3 headers, 50MB archive limit, 300s proxy timeouts, 14-day rotated logs. |

---

## 2. Offline Validation Evidence

Recorded in `docs/phase9/evidence/deployment/deployment_static_validation.json`:
- **Shell Syntax (`bash -n`)**: 10/10 scripts in `deployment/scripts/*.sh` passed (`PASSED`).
- **Systemd Unit INI Parsing**: 4/4 `.service` files passed (`[Unit, Service, Install]`).
- **Environment Template Audit**: Verified `LOCAL_LLM_CONTEXT_BUDGET` and `LOCAL_LLM_MAX_TOKENS` present; zero hardcoded RFC1918/public IPs across `deployment/` and `scripts/`.
- **Database Schema Head (`backend/alembic/versions/008_soc_pilot.py`)**: Tested upgrade from `007_distributed_locks -> 008_soc_pilot` and downgrade rollback cleanly on SQLite.

## 3. Non-Executed Runtime Targets

- Real Ubuntu 22.04/24.04 systemd daemon execution, Nginx TLS termination with live certificates, PostgreSQL 16 + Redis 7 live cutover, and vLLM CUDA GPU boot remain **`NOT_TESTED` / `NOT_DEPLOYED`**.

