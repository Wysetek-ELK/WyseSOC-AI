# Phase 9 — Server 1 Setup Runbook (Application & Governance Node)

**Target OS:** Ubuntu 22.04 LTS or 24.04 LTS (Native Linux — No Docker)  
**Services:** FastAPI (`uvicorn`), Celery Worker & Beat Scheduler, Next.js Frontend (`next start`), PostgreSQL 16, Redis 7, Nginx TLS Reverse Proxy, Logrotate, UFW.

---

## 1. Prerequisites & Security Hygiene

1. Provision dedicated service account `aiverdict` and clone/checkout approved release commit into `/opt/ai-verdict`.
2. Prepare `/opt/ai-verdict/backend/.env` with `chmod 600` using `deployment/env.production.example`:
   - Generate cryptographically random `SECRET_KEY` and `AUDIT_SIGNING_KEY` (`openssl rand -hex 32`).
   - Set `APP_ENV="production"`, `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false"`, `FORTISIEM_MOCK_FALLBACK="false"`, `AUTO_MIGRATE_ON_STARTUP="false"`, `COOKIE_SECURE="true"`.
   - Set `LOCAL_LLM_BASE_URL` to the Server 2 private VLAN endpoint (`http://<SERVER2_PRIVATE_HOST>:8000/v1`).

## 2. Automated Native Installation

```bash
cd /opt/ai-verdict
sudo LOCAL_LLM_BASE_URL="http://<SERVER2_PRIVATE_HOST>:8000/v1" \
     INITIAL_ADMIN_PASSWORD="<STRONG_INITIAL_ADMIN_PASSWORD>" \
     bash deployment/scripts/install_ubuntu.sh
```

What `install_ubuntu.sh` executes idempotently:
1. Installs apt packages (`nginx`, `postgresql`, `postgresql-contrib`, `redis-server`, `python3-venv`, `logrotate`, `ufw`).
2. Ensures Node.js 22 LTS and creates `/var/log/ai-verdict` owned by `aiverdict`.
3. Initializes PostgreSQL user/database & `.env` only if absent (preserves existing credentials on re-runs).
4. Installs Python dependencies into `/opt/ai-verdict/backend/venv` and runs `alembic upgrade head` (including `008_soc_pilot`).
5. Builds Next.js production bundle (`npm ci && npm run build`).
6. Copies systemd unit files (`ai-verdict-backend`, `ai-verdict-worker`, `ai-verdict-frontend`, `ai-verdict-scheduler`), `/etc/logrotate.d/ai-verdict`, and Nginx configuration.
7. Restricts UFW ingress to ports `22`, `80`, and `443`.

*Note:* If running scheduled FortiSIEM polling via Celery Beat, explicitly enable and start `ai-verdict-scheduler` alongside the worker (`sudo systemctl enable --now ai-verdict-scheduler`).

## 3. Post-Install Verification & Safe Rollback

- **Verify Stack:**
  ```bash
  sudo bash /opt/ai-verdict/deployment/scripts/verify_server1.sh
  ```
- **Rollback to Approved Commit SHA:**
  ```bash
  sudo bash /opt/ai-verdict/deployment/scripts/rollback_server1.sh <APPROVED_COMMIT_SHA>
  ```
- Note that `rollback_server1.sh` preserves PostgreSQL data and HMAC audit records and re-runs `verify_server1.sh`.
- **Current Environment Verification Status:** All scripts passed offline `bash -n` syntax and INI validation; live Ubuntu host provisioning is **`NOT_TESTED` / `NOT_DEPLOYED`**.

