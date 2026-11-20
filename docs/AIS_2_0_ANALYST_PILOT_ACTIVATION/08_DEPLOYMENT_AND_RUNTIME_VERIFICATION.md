# Report 08 — Deployment and Runtime Verification
**Verdictum AI — AIS 2.0 Deployment State & Server Runtime Identity**
**Date:** November 20, 2026  
**Status:** FACTUALLY VERIFIED & ACTIVE  
**Deployment Host:** Server 1 (`172.26.41.240`) & Server 2 (`172.26.41.241`)  

---

## 1. Executive Summary

This report documents the live deployment environment, systemd service units, and health checks across Verdictum AI infrastructure. The application server (Server 1) hosts the Next.js frontend, FastAPI backend, PostgreSQL 15, and Celery workers, while Server 2 hosts the isolated Local AWQ LLM.

---

## 2. Infrastructure Inventory & Runtime Identity

| Server Host | IP Address | Deployed Directory | Active systemd Services | Runtime Role | Status |
|:---|:---|:---|:---|:---|:---:|
| **Server 1** | `172.26.41.240` | `/opt/wysesoc-ai` | `ai-verdict-backend.service`<br>`ai-verdict-frontend.service`<br>`ai-verdict-worker.service`<br>`ai-verdict-scheduler.service`<br>`postgresql.service`<br>`redis-server.service`<br>`nginx.service` | Application, Database, Ingestion, Background Triage, Workbench GUI | **ACTIVE (HEALTHY)** |
| **Server 2** | `172.26.41.241` | `/opt/vllm-inference` | `vllm-inference.service` | Dedicated Local AWQ LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ` @ `temp: 0.01`) | **UNTOUCHED & PROTECTED** |

---

## 3. Database Migration State (PostgreSQL on Server 1)

The PostgreSQL database `ai_verdict_db` on Server 1 has applied all migrations through head:
- **Migration 014 (`014_policy_version_history_management`):** Added lifecycle status (`DRAFT`, `APPROVED`, `ARCHIVED`), `was_ever_approved`, and archive metadata.
- **Migration 015 (`015_approved_version_immutability`):** Backfilled historical approvals and enforced PostgreSQL check constraint `ck_prompt_versions_approved_was_ever_approved`.

---

## 4. Live Health Check & Endpoint Verification Protocol

```bash
# Authoritative Post-Deployment Health Verification Loop
sleep 5 && for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do 
  (systemctl is-active --quiet ai-verdict-backend.service && \
   systemctl is-active --quiet ai-verdict-frontend.service && \
   curl -fsSI http://127.0.0.1:3000/login >/dev/null 2>&1 && \
   curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1) && exit 0 || sleep 2; 
done; 
exit 1
```

### Verified HTTP Responses
- `GET http://127.0.0.1:8000/api/health` -> HTTP 200 `{"status": "healthy", "database": "connected", "redis": "connected", "llm_bridge": "reachable"}`
- `GET http://127.0.0.1:3000/login` -> HTTP 200 OK (Clean HTML response, zero SSR hydration mismatches)
- `GET http://127.0.0.1:8000/api/prompts/rules` -> HTTP 200 OK (All detection rules operational)
