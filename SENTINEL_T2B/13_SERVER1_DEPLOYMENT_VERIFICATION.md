# 13 — Server 1 Deployment Verification

- **UPLA Execution ID**: `upla-20261128-142508-2a4156`
- **Gate 1 (GitHub Sync)**: Approved (`YES`), pushed commit `eb78e6ffc034b0cfc3560de0509642efda5b9e59` to `feature/phase3-compact-ui`, remote SHA verified.
- **Gate 2 (Server 1 Deployment)**: Approved (`YES`), deployed to `server-1` (`172.26.41.240`, `/opt/wysesoc-ai`).
- **Deployment Steps Verified**:
  1. Backup metadata recorded at `/var/backups/ai-verdict/prev-sha-upla-20261128-142508-2a4156.txt` (previous SHA `0e492c90b0ebf0f967ab9488774052c83e90792b`).
  2. Alembic migration `019_sentinel_chat_persistence` applied (`alembic upgrade head`).
  3. Remote deploy-gate pytest passed (`test_ais_heavy_tcp_e2e.py`, `test_rule_learning_platform.py`, `test_api_422_remediation.py`).
  4. Frontend `npm run build` succeeded.
  5. `ai-verdict-backend.service` & `ai-verdict-frontend.service` restarted and health-checked (`http://127.0.0.1:3000/login` & `http://127.0.0.1:8000/api/health`).
  6. Server 2 (`13.204.214.64:8000`) remained running and untouched throughout.
