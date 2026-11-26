# 25 — Remote Deployment & Runtime Verification

- **UPLA Gate 1 (`GITHUB`):** Approved `YES` -> Pushed and verified remote SHA `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509` on `feature/phase3-compact-ui`.
- **UPLA Gate 2 (`DEPLOYMENT`):** Approved `YES` -> Deployed exact SHA `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509` to `server-1` (`172.26.41.240`, `/opt/wysesoc-ai`).
- **Remote Checks Executed by UPLA Engine:** `alembic upgrade head`, targeted pytest (`test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`), `npm run build`, systemd service restarts (`ai-verdict-backend.service`, `ai-verdict-frontend.service`), `/login`, `/api/health`.
- **Live HTTP Verification (`GET http://172.26.41.240/api/health`):** `status="healthy"`, `database_type="postgresql"`, `redis_celery="healthy"`, `local_llm.model_name="Qwen/Qwen3-14B-AWQ"`, `current_s2_health="ONLINE"`.
