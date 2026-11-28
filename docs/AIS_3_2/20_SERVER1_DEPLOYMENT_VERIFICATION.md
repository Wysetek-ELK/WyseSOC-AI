# AIS 3.2 — 20: Server 1 Deployment Verification

Executed via UPLA `FULL_WORKFLOW` (`upla-20261128-132159-9732f9`):
- **Gate 1 (`GITHUB`):** Approval `apr-a328725efe8a`, pushed commit `0e492c90b0ebf0f967ab9488774052c83e90792b` to `feature/phase3-compact-ui` (`SYNCED_AND_VERIFIED`).
- **Gate 2 (`DEPLOYMENT`):** Approval `apr-4a2e8a5e7f3a`, backed up metadata to `/var/backups/ai-verdict/`, pulled `0e492c90b0ebf0f967ab9488774052c83e90792b` on `172.26.41.240`, ran `alembic upgrade head`, ran backend smoke pytest, ran `npm run build`, restarted `ai-verdict-backend.service` and `ai-verdict-frontend.service`, passed health checks.
- **Post-Deploy Live HTTP:** `GET /api/health` -> `200` (`postgresql` healthy, `redis_celery` healthy, `Qwen/Qwen3-14B-AWQ` `ONLINE`, circuit breaker `CLOSED`), `GET /login` -> `200`, `GET /api/ais32/overview` -> `401`. Server 2 untouched.
