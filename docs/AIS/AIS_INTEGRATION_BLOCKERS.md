# AIS Integration Blockers & Remediation Register

**Target System:** Agent Intelligence Studio (AIS) 2.3  
**Target Environments:** Server 1 (FastAPI/PostgreSQL) & Server 2 (vLLM GPU Host)  
**Audit Date:** 2026-11-11  
**Total Identified Blockers:** 7 (2 P0 Critical, 3 P1 High, 2 P2 Medium/Low)

---

## 1. Blocker Summary Matrix

| ID | Priority | Category | Component | Operational Impact | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **BLK-01** | **P0** | Network / GPU | Server 2 (vLLM) | Real LLM inference unreachable (TCP timeout); all live/sim triage blocked | **OPEN** |
| **BLK-02** | **P0** | Deployment | Server 1 (Codebase) | Server 1 running outdated commit `9616971` (missing AIS 2.1–2.3 remediations) | **OPEN** |
| **BLK-03** | **P1** | Infrastructure | Server 1 (Queues) | Redis and Celery inactive; async simulation replay cannot process | **OPEN** |
| **BLK-04** | **P1** | Data Quality | Server 1 (Corpus) | 99.56% of labeled data is ML-generated; 0 independent human GT; N=2 < 5 | **OPEN** |
| **BLK-05** | **P1** | Rule Governance | Server 1 (SIEM Rules) | Rules store runtime counters (`incidentCount`) rather than correlation logic | **OPEN** |
| **BLK-06** | **P2** | Schema | Server 1 (PostgreSQL) | `historical_ground_truth.resolved_by` column missing in Server 1 DB | **OPEN** |
| **BLK-07** | **P2** | Configuration | Server 1 (`.env`) | Trailing newlines inside quoted `.env` values (e.g. `30.0\n`) | **OPEN** |

---

## 2. Detailed Blocker Analysis & Actionable Remediation

### BLK-01: Server 2 Local LLM Host Unreachable (P0 - Critical)
- **Host Affected:** Server 2 (`http://192.0.2.50:8000/v1` [Masked: RFC 5737])
- **Observed Behavior:** TCP socket probe from Server 1 to port 8000 timed out after 3,003.9 ms. HTTP `/health` and `/models` probes timed out. Triage on incident `173265` raised `LocalLLMUnavailableError`.
- **Root Cause:** Host powered off, vLLM service down, AWS Security Group dropping port 8000 packets from Server 1, or dynamic public IP changed upon restart.
- **Remediation Steps:**
  1. Check EC2 instance state for Server 2: `aws ec2 describe-instance-status --instance-ids <INSTANCE_ID>`.
  2. If instance was restarted and acquired a new public IP, update Server 1 `.env`:
     ```powershell
     python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py config-llm --llm-ip <NEW_SERVER2_IP> --llm-port 8000
     ```
  3. Ensure vLLM process is running on Server 2:
     ```bash
     vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --host 0.0.0.0 --port 8000 --max-model-len 8192
     ```
  4. Ensure Security Group permits inbound TCP 8000 from Server 1 outbound IP (`203.0.113.124` [Masked]).
- **Verification:** Run `python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py test-inference`. Expect HTTP 200 and completion within 1,500ms.

---

### BLK-02: Server 1 Deployment Desynchronization (P0 - Critical)
- **Host Affected:** Server 1 (`/opt/wysesoc-ai`)
- **Observed Behavior:** Server 1 is running git commit `9616971f47e24bfe7fcf8881f8da0457509294ba` with dirty status, detached at `HEAD`. Current repository baseline is `6cdb82a3` (AIS 2.3).
- **Impact:** Server 1 lacks the canonical evaluation pipeline, Priority 3b token compaction, exact-rule filtering, G1–G8 revised scoring, and historical eligibility fixes.
- **Remediation Steps:**
  1. Ensure all local tests and scans pass: `governor_cli.py status --run-tests`.
  2. Request Stage 1 GitHub gate token and push verified changes.
  3. Request Stage 2 deployment gate token:
     ```powershell
     python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py deploy-gate --commit-sha 6cdb82a3 --approved
     python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py deploy --commit-sha 6cdb82a3 --token-id <TOKEN_ID>
     ```
- **Verification:** Run `governor_cli.py audit-remote` and verify `git.sha` matches `6cdb82a3`.

---

### BLK-03: Redis & Celery Inactive on Server 1 (P1 - High)
- **Host Affected:** Server 1 (`localhost:6379`)
- **Observed Behavior:** `systemctl is-active redis` and `systemctl is-active celery` returned `inactive`. Socket connection to 6379 failed with `Connection refused`.
- **Impact:** Background simulation replay cannot execute; enqueued jobs remain stalled.
- **Remediation Steps:**
  1. On Server 1:
     ```bash
     sudo systemctl start redis-server
     sudo systemctl enable redis-server
     ```
  2. Start Celery worker configured for `simulation_replay`:
     ```bash
     sudo systemctl start wysesoc-ai-celery
     sudo systemctl enable wysesoc-ai-celery
     ```
- **Verification:** Run `governor_cli.py audit-remote` and verify `redis_celery.redis_ping == true`.

---

### BLK-04: Ground-Truth Scarcity & Lack of Human Provenance (P1 - High)
- **Host Affected:** Server 1 (`historical_ground_truth`, `investigations`)
- **Observed Behavior:** 2,734 of 2,746 labeled incidents (99.56%) have `is_ml_generated = true`. Zero incidents have `is_independently_verified = true`. Target rule `PH_RULE_HEAVY_TCP_HOST_SCAN` has only 2 incidents ($N=2 < 5$).
- **Impact:** Empirical G8 evaluation cannot pass mathematically ($N < 5$); policies cannot achieve empirical certification for autonomous operation.
- **Remediation Steps:**
  1. SOC analysts must triage and label at least 5–10 incidents for target rules.
  2. Populate `cleared_user`, `cleared_reason`, and set `investigations.is_independently_verified = true`.
- **Verification:** Query `SELECT COUNT(*) FROM investigations WHERE is_independently_verified = true;` (Expect $\ge 5$ per target rule).

---

### BLK-05: SIEM Rules Store Runtime Counters Rather Than Authoritative Logic (P1 - High)
- **Host Affected:** Server 1 (`rules.pattern_logic`)
- **Observed Behavior:** Target rules contain `{"incidentCount": 230}` rather than correlation condition expressions (e.g. distinct destination ports > 20 within 5 minutes).
- **Impact:** Gate G1 warns about missing authoritative correlation parameters and assigns partial semantics.
- **Remediation Steps:**
  1. Update FortiSIEM rule sync script to extract XML condition definitions rather than incident counters.
  2. Trigger Rule Intelligence Snapshot regeneration.
- **Verification:** Inspect `GET /api/verdict-intelligence/rules/{id}/quality-assessment` and verify G1 score $\ge 12/15$.

---

### BLK-06: Database Schema Discrepancy on `resolved_by` (P2 - Medium)
- **Host Affected:** Server 1 (`historical_ground_truth`)
- **Observed Behavior:** Querying `hgt.resolved_by` fails with PostgreSQL error `column hgt.resolved_by does not exist`. Server 1 uses `cleared_user`.
- **Impact:** Any service attempting to query `resolved_by` directly causes an uncaught database error.
- **Remediation Steps:** Ensure all SQL queries use `cleared_user` or add an Alembic migration adding `resolved_by` as an alias column if required.

---

### BLK-07: `.env` Formatting Inconsistencies on Server 1 (P2 - Low)
- **Host Affected:** Server 1 (`/opt/wysesoc-ai/backend/.env`)
- **Observed Behavior:** Several settings have embedded trailing newlines (e.g. `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false\n"`, `FORTISIEM_TIMEOUT="25.0\n"`).
- **Impact:** Python `str.strip()` handles this in most cases, but raw subprocesses or bash scripts parsing `.env` can encounter syntax errors.
- **Remediation Steps:** Run `sed -i 's/\r$//' /opt/wysesoc-ai/backend/.env` and re-save using AIS 2.3 `LLMConfigService._upsert_env_vars`.

