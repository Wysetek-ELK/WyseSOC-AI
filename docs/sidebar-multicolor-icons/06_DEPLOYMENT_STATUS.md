# 06 — Deployment Validation & Status Report

**Date:** 2026-11-18  
**Deployment Status:** **NOT DEPLOYED (Remote Environment Not Configured / Local Toolchain Unavailable)**

---

## 1. Audited Deployment Architecture

Inspected `DEPLOYMENT.md` and `deployment/scripts/`:

- **Target Host:** Server 1 (`Ubuntu Server 22.04 / 24.04 LTS`), application root `/opt/ai-verdict`, dedicated service user `aiverdict`.
- **Frontend Service:** `ai-verdict-frontend.service` (Next.js production build served on `127.0.0.1:3000` behind Nginx reverse proxy `deployment/nginx/ai-verdict.conf`).
- **Established Scripts:**
  - Full deployment entrypoint: `deployment/scripts/deploy_server1.sh` (calls `install_ubuntu.sh`).
  - Health verification: `deployment/scripts/verify_server1.sh` (checks systemd units, Alembic, Redis, Nginx, backend `/api/health`, and frontend `/login` on `127.0.0.1:3000`).
  - Safe rollback: `deployment/scripts/rollback_server1.sh <APPROVED_COMMIT_SHA>`.
- **Frontend-Only Deployment Principle:** Because this change modifies **only** frontend UI files under `frontend/` (zero backend, database, migration, Celery worker, or LLM inference changes), deploying to Server 1 requires **only** rebuilding `frontend/` and restarting `ai-verdict-frontend` (no backend restart, no Alembic migration, no Server 2 GPU touch).

---

## 2. Deployment Blockers Identified

Verified via `upla.ps1 validate-config`, `upla.ps1 toolchain-audit`, and `~/.ssh/` inspection:

1. **No Configured Remote Deployment Server:** `.upla/config.json` has `deployment.configured = false` and `servers = []` (zero authorized remote hostnames/IPs configured).
2. **No SSH Credentials / Agent Active:** `~/.ssh/` contains no private key files (`sshPrivateKeyFilesDetected: 0`) and `ssh-agent` is `Stopped`.
3. **No Local Git / Node.js Toolchain:** `git` and `node`/`npm` are not installed on this Windows workstation (`localGitReady: false`), preventing local production build verification or GitHub push from this shell prior to deployment.

---

## 3. Authorized Frontend-Only Deployment Procedure (Once Server 1 Access & Git Sync Are Ready)

After syncing the verified commit to GitHub (`https://github.com/Wysetek-ELK/WyseSOC-AI.git`, branch `feature/phase3-compact-ui` or approved PR target) and obtaining explicit human approval:

```bash
# On Server 1 (Ubuntu LTS) — Frontend-Only Rollout (No Backend/DB/GPU Changes)
cd /opt/ai-verdict
git fetch origin
git checkout <VERIFIED_COMMIT_SHA>

cd /opt/ai-verdict/frontend
sudo -u aiverdict npx tsc --noEmit
sudo -u aiverdict npm run test:sidebar-icons
sudo -u aiverdict npm test
sudo -u aiverdict npm run build

# Restart ONLY the Next.js frontend service (avoids unnecessary backend/DB restarts)
sudo systemctl restart ai-verdict-frontend

# Post-deployment health checks
sudo systemctl status ai-verdict-frontend --no-pager
curl -fsSI http://127.0.0.1:3000/login | head -n 5
bash /opt/ai-verdict/deployment/scripts/verify_server1.sh
```

### Rollback Plan

If a critical navigation regression occurs after deployment:

```bash
# Fast frontend-only rollback to previous approved SHA
cd /opt/ai-verdict
git checkout <PREVIOUS_APPROVED_SHA>
cd /opt/ai-verdict/frontend
sudo -u aiverdict npm run build
sudo systemctl restart ai-verdict-frontend
curl -fsSI http://127.0.0.1:3000/login | head -n 5

# Or full server rollback script if needed:
# sudo bash /opt/ai-verdict/deployment/scripts/rollback_server1.sh <PREVIOUS_APPROVED_SHA>
```

---

## 4. Verification Classification

- **Verified:** Audited `DEPLOYMENT.md`, `deploy_server1.sh`, `verify_server1.sh`, `rollback_server1.sh`, `.upla/config.json`, and local SSH/Git/Node availability.
- **Unexecuted:** Remote deployment, remote frontend build, and live post-deploy health verification.
- **Remaining Blockers:** Configure authorized Server 1 SSH host/key and install Git/Node.js (or execute from CI/Server 1 directly).
