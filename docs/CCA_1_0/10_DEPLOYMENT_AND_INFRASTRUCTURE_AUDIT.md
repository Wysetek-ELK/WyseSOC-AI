# 10 — Deployment & Infrastructure Audit

## 1. Deployment Artifacts Inventory (18 Files)

| File | Lines | Status |
|---|---:|---|
| `deployment/env.production.example` | 71 | `ACTIVE` / `VERIFY` |
| `deployment/logrotate/ai-verdict` | 10 | `ACTIVE` / `VERIFY` |
| `deployment/nginx/ai-verdict.conf` | 118 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/backup_db.sh` | 27 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/deploy_server1.sh` | 20 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/install_llm_server.sh` | 148 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/install_ollama_llm.sh` | 58 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/install_ubuntu.sh` | 163 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/rollback_server1.sh` | 45 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/setup_server2_gpu.sh` | 19 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/smoke_test_server2.py` | 163 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/start_services.sh` | 22 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/stop_services.sh` | 15 | `ACTIVE` / `VERIFY` |
| `deployment/scripts/verify_server1.sh` | 40 | `ACTIVE` / `VERIFY` |
| `deployment/systemd/ai-verdict-backend.service` | 32 | `ACTIVE` / `VERIFY` |
| `deployment/systemd/ai-verdict-frontend.service` | 32 | `ACTIVE` / `VERIFY` |
| `deployment/systemd/ai-verdict-scheduler.service` | 32 | `ACTIVE` / `VERIFY` |
| `deployment/systemd/ai-verdict-worker.service` | 33 | `ACTIVE` / `VERIFY` |

## 2. Key Infrastructure Findings
1. **Superseded LLM Installer**: `deployment/scripts/install_ollama_llm.sh` (58 lines, port 11434, Ollama `qwen2.5:7b`) is `SUPERSEDED` by `deployment/scripts/install_llm_server.sh` (vLLM AWQ on port 8000, called by `setup_server2_gpu.sh`). **Action:** `ARCHIVE`.
2. **Celery Beat Systemd Unit**: `deployment/systemd/ai-verdict-scheduler.service` runs Celery Beat without any `beat_schedule` in `celery_app.py`. Referenced by `install_ubuntu.sh`, `rollback_server1.sh`, `start_services.sh`, `stop_services.sh`, `verify_server1.sh` -> requires coordinated infrastructure decision (`VERIFY_FIRST`, Batch 6).
3. **Nginx Reverse Proxy (`deployment/nginx/ai-verdict.conf`)**: Proxies `/api/`, `/health`, `/metrics`, and `/` with `proxy_read_timeout 300s`. Matches `health.py` root routes.
4. **Disaster Recovery Scripts**: `backup_db.sh`, `rollback_server1.sh`, `verify_server1.sh`, `backend/app/scripts/backup.py`, `restore.py` are **REQUIRED** operational/DR utilities — retain strictly.
5. **Remote Parity Limitation**: Live Server 1 and Server 2 SSH inspection was not performed in this read-only local audit.
