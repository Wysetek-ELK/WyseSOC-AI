# 20 — Server 1 Deployment Verification

- **UPLA Execution**: `upla-20261126-090716-010d42`
- **Git Commit**: `2dc8d15a4517626bcae375e5754f4431693053f3` (`feature/phase3-compact-ui`)
- **Server**: `server-1` (`172.26.41.240`, `/opt/wysesoc-ai`)
- **Remote Checks**: `alembic upgrade head` PASS, remote `pytest` PASS, remote `npm run build` PASS, `ai-verdict-backend.service` & `ai-verdict-frontend.service` restarted cleanly, `/api/health` HTTP `200`, `/login` HTTP `200`.
