# Report 09: Systemd Service Units & Process Supervision (P4-REQ-08)

## 1. Process Supervision Philosophy

In a container-free Linux production environment, **systemd** serves as the primary init system and process supervisor. It provides:
- Automatic crash restart with bounded backoff.
- Resource limits (`LimitNOFILE`, memory quotas).
- File system sandboxing and privilege reduction.
- Centralized structured logging to journald and `/var/log/ai-verdict/`.

---

## 2. Hardened Service Units Overview

The application is decomposed into three cooperating systemd services on Server 1:

```
+------------------------------------+
|    ai-verdict-backend.service      |  FastAPI application server (uvicorn, port 8000)
+------------------------------------+
                  |
                  v
+------------------------------------+
|    ai-verdict-worker.service       |  Celery distributed task worker (triage/replays)
+------------------------------------+
                  |
                  v
+------------------------------------+
|    ai-verdict-frontend.service     |  Next.js SSR application server (node, port 3000)
+------------------------------------+
```

---

## 3. Linux Sandboxing & Least Privilege Security

All services implement strict Linux security sandboxing directives:

```ini
[Service]
# Non-Root Execution
User=aiverdict
Group=aiverdict

# File System Sandboxing
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/ai-verdict /opt/ai-verdict/backend
PrivateTmp=true

# Privilege Hardening
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true

# Process Resilience
Restart=always
RestartSec=5s
LimitNOFILE=65535
```

### Directive Explanations:
1. **`ProtectSystem=strict`:** Mounts the entire OS filesystem (`/usr`, `/boot`, `/etc`, `/lib`) as strictly read-only for the process.
2. **`ProtectHome=true`:** Denies access to `/home`, `/root`, and `/run/user`.
3. **`NoNewPrivileges=true`:** Prevents the process and its children from gaining new privileges via setuid/setgid binaries.
4. **`PrivateTmp=true`:** Isolates `/tmp` into a private namespace, preventing symlink attacks or cross-process information leaks.
5. **`ReadWritePaths`:** Explicitly allows writes ONLY to `/var/log/ai-verdict` and application storage. All other disk regions are immutable.

---

## 4. Service Unit Definitions

### Backend (`ai-verdict-backend.service`):
```ini
[Unit]
Description=AI Verdict FastAPI Backend Application Service
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=aiverdict
Group=aiverdict
WorkingDirectory=/opt/ai-verdict/backend
EnvironmentFile=/opt/ai-verdict/backend/.env
ExecStart=/opt/ai-verdict/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='127.0.0.1'
Restart=always
RestartSec=5s
LimitNOFILE=65535
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/ai-verdict /opt/ai-verdict/backend
NoNewPrivileges=true
PrivateTmp=true
```

### Celery Worker (`ai-verdict-worker.service`):
```ini
[Unit]
Description=AI Verdict Celery Distributed Task Worker Service
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=aiverdict
Group=aiverdict
WorkingDirectory=/opt/ai-verdict/backend
EnvironmentFile=/opt/ai-verdict/backend/.env
ExecStart=/opt/ai-verdict/backend/venv/bin/celery -A app.workers.celery_app worker -Q live_triage,simulation_replay,maintenance -c 4 --loglevel=INFO
Restart=always
RestartSec=5s
LimitNOFILE=65535
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/ai-verdict /opt/ai-verdict/backend
NoNewPrivileges=true
PrivateTmp=true
```

---

## 5. Verification & Service Operations

```bash
# Check status of all AI Verdict processes
systemctl status ai-verdict-backend ai-verdict-worker ai-verdict-frontend

# Inspect live logs
journalctl -u ai-verdict-backend -f
tail -f /var/log/ai-verdict/worker.log
```

