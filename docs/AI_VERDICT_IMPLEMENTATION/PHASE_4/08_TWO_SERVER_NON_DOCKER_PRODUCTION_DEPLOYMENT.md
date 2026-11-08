# Report 08: Two-Server Non-Docker Production Deployment (P4-REQ-08)

## 1. Architectural Topology

AI Verdict is deployed across two physically or virtually dedicated Linux Ubuntu Server LTS nodes without requiring Docker, container runtimes, or Kubernetes:

```
                          [ SOC Analysts / Ingress Traffic ]
                                          |
                                          | HTTPS / 443 (TLS 1.3)
                                          v
+--------------------------------------------------------------------------------------------------+
|                                  SERVER 1: APPLICATION & STORAGE                                 |
|                                                                                                  |
|   Private IP: 10.10.20.4                                                                         |
|   Hardware  : 8 vCPUs, 32 GB RAM, 100 GB NVMe Storage                                            |
|                                                                                                  |
|   Services:                                                                                      |
|   1. Nginx Reverse Proxy (Ports 80/443) -> TLS termination, CSP headers, Static assets          |
|   2. FastAPI Application (127.0.0.1:8000) -> 4 Uvicorn worker processes                          |
|   3. Celery Distributed Worker -> 4 concurrent execution threads                                 |
|   4. Next.js Frontend Server (127.0.0.1:3000) -> Node 22 SSR UI runtime                         |
|   5. PostgreSQL 16 (127.0.0.1:5432) -> Database with asyncpg connection pooling                  |
|   6. Redis 7 (127.0.0.1:6379) -> Celery message broker & task result backend                     |
+--------------------------------------------------------------------------------------------------+
                                          |
                                          | Private Internal Network (Port 8000)
                                          | Strictly Restricted via UFW Firewall
                                          v
+--------------------------------------------------------------------------------------------------+
|                                  SERVER 2: DEDICATED GPU INFERENCE                               |
|                                                                                                  |
|   Private IP: 10.10.20.5                                                                         |
|   Hardware  : AWS EC2 g4dn.2xlarge (1x NVIDIA T4 GPU, 16 GB VRAM, 8 vCPUs, 32 GB RAM)            |
|                                                                                                  |
|   Services:                                                                                      |
|   1. vLLM Serving Engine (10.10.20.5:8000)                                                       |
|      - Model: Qwen/Qwen2.5-7B-Instruct-AWQ                                                       |
|      - Quantization: AWQ 4-bit                                                                   |
|      - Max Model Context: 4096 tokens                                                            |
|      - GPU Memory Utilization: 0.90                                                              |
|   2. UFW Firewall: Denies all inbound traffic EXCEPT TCP 8000 from Server 1 (10.10.20.4)        |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Server 1 Deployment Execution (`deploy_server1.sh`)

Provisioning Server 1 is automated via `deployment/scripts/deploy_server1.sh`, which invokes `install_ubuntu.sh`:
1. **OS Packages:** Installs `build-essential`, `python3-venv`, `libpq-dev`, `postgresql`, `redis-server`, `nginx`, and `ufw`.
2. **Node.js:** Installs Node.js 22 LTS via NodeSource.
3. **Dedicated System User:** Creates unprivileged service user `aiverdict` (`uid/gid`). The application NEVER runs as root.
4. **Database Provisioning:** Creates PostgreSQL user `aiverdict_user`, database `ai_verdict`, and grants ownership.
5. **Python Virtual Environment:** Creates `/opt/ai-verdict/backend/venv` and installs all dependencies from `requirements.txt`.
6. **Alembic Migrations:** Executes `alembic upgrade head` to apply all versioned schema revisions.
7. **Frontend Build:** Runs `npm install` and `npm run build` in `/opt/ai-verdict/frontend`.
8. **Systemd Services:** Installs, enables, and starts:
   - `ai-verdict-backend.service`
   - `ai-verdict-worker.service`
   - `ai-verdict-frontend.service`
9. **Nginx Ingress:** Installs `ai-verdict.conf` into `/etc/nginx/sites-available/` and reloads Nginx.

---

## 3. Server 2 GPU Inference Setup (`setup_server2_gpu.sh`)

Provisioning Server 2 is automated via `deployment/scripts/setup_server2_gpu.sh <SERVER_1_PRIVATE_IP>`:
1. **NVIDIA CUDA Drivers:** Validates `nvidia-smi` and CUDA 12.x drivers.
2. **vLLM Virtual Environment:** Installs vLLM within `/opt/llm-server/venv`.
3. **Model Download & Cache:** Pre-fetches `Qwen/Qwen2.5-7B-Instruct-AWQ` to local NVMe storage.
4. **vLLM Systemd Unit:** Installs `llm-server.service` running as non-root user `llmuser`.
5. **Network Firewall Hardening:**
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow from 10.10.20.4 to any port 8000 proto tcp
   ufw enable
   ```
   Ensures the GPU inference port is completely inaccessible from the public internet or unauthorized LAN segments.

