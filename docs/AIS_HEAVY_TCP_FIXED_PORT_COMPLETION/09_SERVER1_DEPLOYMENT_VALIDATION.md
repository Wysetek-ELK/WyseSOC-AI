# 09 — Server 1 Deployment & Rollback Safety Validation

**Target Host:** Server 1 (`172.26.41.240`, `verdictum-core-01`, `/opt/wysesoc-ai`, non-Docker systemd)
**Git Repository & Branch:** `https://github.com/Wysetek-ELK/WyseSOC-AI.git` (`feature/phase3-compact-ui`)
**Final Verified Deployed Commit SHA:** `800bc077d77f6b694f5b43d4b02fa7671b4ebf04`
**Server 2 Local GPU LLM (`13.204.214.64:8000`):** **UNTOUCHED** (`Qwen/Qwen2.5-7B-Instruct-AWQ` remained running throughout)

---

## 1. UPLA-Governed Deployment History (Two-Gate Human Approval Audit)

Every code deployment to GitHub (Gate 1) and Server 1 (Gate 2) followed the mandatory UPLA Full Workflow (`run-governance` → Gate 1 explicit `YES` → remote SHA verification → Gate 2 explicit `YES` → backup + checkout + pytest + build + restart + health check):

| UPLA Execution ID | Commit SHA | Gate 1 (GitHub) | Gate 2 (Server 1) | Verification Result | Rollback Proof |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `upla-20261118-130709-359f43` | `ebffba0ee70daf4bec86adc6b095f87ddc02520f` | `SYNCED_AND_VERIFIED` | `DEPLOYED_AND_VERIFIED` | Backend pytest + Next.js build + systemd health **PASS** | `NOT_NEEDED` |
| `upla-20261118-143229-429ee2` | `4e709713490fdc8c410a768e0ab295aa922b54ac` | `SYNCED_AND_VERIFIED` | `FAILED_AT_DEPLOYMENT` (`test_09` 4096-token budget failure) | Pre-restart pytest gate caught token overflow before service restart | **`ROLLBACK_SUCCEEDED`** cleanly back to `ebffba0e` (live proof of automated rollback protection!) |
| `upla-20261118-144149-2c1d96` | `8502a24d6f29c7e448f61cc9c27f88935150400b` | `SYNCED_AND_VERIFIED` | `DEPLOYED_AND_VERIFIED` | All backend pytest (incl. `test_09`) + Next.js build + health **PASS** | `NOT_NEEDED` |
| **`upla-20261118-144854-c645a7`** *(Current Live)* | **`800bc077d77f6b694f5b43d4b02fa7671b4ebf04`** | **`SYNCED_AND_VERIFIED`** | **`DEPLOYED_AND_VERIFIED`** | All backend pytest (incl. strengthened `test_09`) + Next.js build + health **PASS** | `NOT_NEEDED` (backup at `/var/backups/ai-verdict/prev-sha-upla-20261118-144854-c645a7.txt`) |

---

## 2. Final Deployment Step-by-Step Verification (`upla-20261118-144854-c645a7`)

1. **SSH Preflight:** `PASSED (root@172.26.41.240): prevSha=8502a24d6f29c7e448f61cc9c27f88935150400b`
2. **Pre-Deploy Backup:** Recorded at `/var/backups/ai-verdict/prev-sha-upla-20261118-144854-c645a7.txt`
3. **Exact SHA Verification:** Checked out and verified exact Git SHA `800bc077d77f6b694f5b43d4b02fa7671b4ebf04` in `/opt/wysesoc-ai`
4. **Backend Automated Tests:** `cd /opt/wysesoc-ai/backend && ./venv/bin/pytest tests/test_ais_heavy_tcp_e2e.py tests/test_rule_learning_platform.py tests/test_api_422_remediation.py -q` → **OK (ALL PASSED)**
5. **Frontend Production Build:** `cd /opt/wysesoc-ai/frontend && npm run build` → **OK (0 errors)**
6. **Service Restart:** `systemctl restart ai-verdict-backend.service ai-verdict-frontend.service` → **OK**
7. **Post-Deploy Health Verification:**
   - `systemctl is-active --quiet ai-verdict-backend.service` → **ACTIVE**
   - `systemctl is-active --quiet ai-verdict-frontend.service` → **ACTIVE**
   - `curl -fsSI http://127.0.0.1:3000/login` → **HTTP 200 OK**
   - `curl -fsS http://127.0.0.1:8000/api/health` → **HTTP 200 OK**

---

## 3. Post-Deploy Live Component Health (`GET http://172.26.41.240/api/health`)

| Component | Status | Verified Details |
| :--- | :---: | :--- |
| **Application (`Verdictum Core`)** | `healthy` | `environment: production`, `version: 1.0.0`, CPU `0.5%`, RAM `12.6%` (`1.94/15.36 GB`), Disk `9.4%` |
| **PostgreSQL 16.4** | `healthy` | `connected: true`, latency `2.19 ms`, pool `20` |
| **Redis / Celery** | `healthy` | `reachable: true`, `live_triage_queue_depth: 0` |
| **Server 2 Local LLM (`Verdictum Cortex`)** | `healthy` (`ONLINE`) | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `OPENAI_COMPATIBLE`, `LIVE_PROVIDER`, circuit breaker `CLOSED`, `0/4` slots |
| **Sibling Rule Non-Regression (`9839fa49-...`)** | `ELIGIBLE` | `Heavy TCP Host Scan` remains on untouched `APPROVED v2` |
