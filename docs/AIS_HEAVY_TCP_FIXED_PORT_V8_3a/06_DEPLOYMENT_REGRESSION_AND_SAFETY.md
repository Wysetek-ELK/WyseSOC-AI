# 06 — Deployment, Regression Test Results & Production Safety Verification

**Deployment Target:** Server 1 (Verdictum Core — `172.26.41.240`)  
**Deployment Architecture:** Non-Docker systemd (`ai-verdict-backend.service`, `ai-verdict-frontend.service`)  
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Canonical UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Deployment Toolchain:** Universal Project Lifecycle Agent (UPLA Full Workflow)  

---

## 1. Automated Regression Test Suite Verification

The complete integration test suite covers 27 automated end-to-end integration and safety tests:

- `tests/test_ais_heavy_tcp_e2e.py` (Tests 1–14)
- `tests/test_rule_learning_platform.py` (Tests 1–10)
- `tests/test_api_422_remediation.py` (Tests 1–3)

### Key Test Cases Verified in V8.3a

| Test Function | Target Capability / Safety Requirement | Test Strategy | Status |
| :--- | :--- | :--- | :---: |
| **`test_01`** | Target rule identification & threshold binding | Confirms UUID `40498741...` and $\ge 100$ host threshold | **PASS** |
| **`test_02`** | Active Policy v7 isolation | Confirms v7 is APPROVED active; candidate v8 is DRAFT | **PASS** |
| **`test_03`** | Sibling rule `Heavy TCP Host Scan` isolation | Confirms UUID `9839fa49...` remains APPROVED v2 | **PASS** |
| **`test_04`** | Telemetry ingestion & 14 canonical fields | Confirms all essential scan fields preserved | **PASS** |
| **`test_05`** | Ingestion of header-only alerts | Verifies 0 raw events handled without crash | **PASS** |
| **`test_06`** | Confidence normalization (`PERCENT_0_100`) | Rejects uncalibrated or out-of-scale confidence values | **PASS** |
| **`test_07`** | Claim grounding & hallucination detection | Rejects ungrounded or fabricated entity claims | **PASS** |
| **`test_08`** | Pre-flight validation & G1–G7 gate scoring | Computes quality score 85.0; enforces G8 production block | **PASS** |
| **`test_09`** | Double-blind masking & AI verdict withholding | Verifies `is_blind_mode: true` hides AI determinations | **PASS** |
| **`test_10`** | Post-submission AI reveal & agreement computation | Calculates AGREEMENT vs DISAGREEMENT correctly | **PASS** |
| **`test_11`** | Multi-tenant isolation & data boundary enforcement | Rejects cross-tenant review submissions (HTTP 403) | **PASS** |
| **`test_12`** | Production automation safety gate | Confirms `is_enabled: false` blocks automated closures | **PASS** |
| **`test_13`** | Nuanced reasoning validator safety & numerical formatting | Validates #173449 bug fix (`3 unanswered probes`) and 3-tier G8 | **PASS** |
| **`test_14` (NEW)** | Evidence-verified guardrails, mandatory negative cases, & review lifecycle | Validates negation rejection, hallucinated ticket rejection, bare EV-* rejection, and verified TP/FP evidence | **PASS** |

---

## 2. Server 1 Non-Docker Systemd Health & Deployment Integrity

Server 1 operates under a production-grade non-Docker systemd architecture:

- **Backend Service:** `ai-verdict-backend.service` (FastAPI / Uvicorn, Python 3.12, systemd active).
- **Frontend Service:** `ai-verdict-frontend.service` (Next.js 14 / Node.js, systemd active).
- **Database:** PostgreSQL (`postgresql.service`, local unix socket / loopback, active, latency 2.1ms).
- **In-Memory Cache & Message Broker:** Redis (`redis.service`, active).
- **Reverse Proxy:** Nginx (`nginx.service`, active, routing `/api` to port 8000 and frontend to port 3000).

### Live Health Check Verification
```bash
curl -fsS http://127.0.0.1:8000/api/health
# Response:
# {"status":"healthy","environment":"production","version":"1.0.0","components":{"database":"healthy","redis_celery":"healthy","local_llm":"healthy"}}

curl -fsSI http://127.0.0.1:3000/login
# Response:
# HTTP/1.1 200 OK
```

---

## 3. Rollback Safety Verification

The deployment architecture includes automated preflight backup and instant rollback capabilities:

1. **Pre-Deployment Backup:** Before checking out any new Git commit, `/var/backups/ai-verdict/` records the current verified SHA and creates an application snapshot.
2. **Proven Rollback Execution:** During initial V8.3 deployment (execution `upla-20261119-042401-bd7e9c`), when `test_13` failed on Server 1 due to `sentbyte=0` in the test mock, UPLA automatically executed `rollback_server1.sh`. Server 1 was restored to previous commit `9bafdd92...` without service disruption.
3. **Safe Rollback Invariant:** If any regression test, frontend build, or service restart fails during deployment, the system immediately reverts to the previous verified SHA. Success is never reported without all health checks passing.

---

## 4. Mandatory Safety Invariants Verification Matrix

| Safety Invariant | Required State | Verified State | Enforcement Mechanism |
| :--- | :--- | :---: | :--- |
| **Active Approved Policy** | Preserve v7 unchanged | **VERIFIED** | Policy `d79fb576...` status is `APPROVED` and bound to rule. |
| **Candidate Policy Status** | Retain v8 in DRAFT status | **VERIFIED** | Policy `20d4f788...` status is `DRAFT`; zero auto-approval. |
| **Sibling Rule Isolation** | Preserve `Heavy TCP Host Scan` v2 | **VERIFIED** | Rule UUID `9839fa49...` active version is `APPROVED v2`. |
| **Server 2 GPU vLLM Engine** | Untouched and un-restarted | **VERIFIED** | vLLM endpoint `http://13.204.214.64:8000/v1` active; PID unchanged. |
| **Production Automation** | Strictly disabled | **VERIFIED** | `ProductionAutomationPolicy.is_enabled == false`. |
| **Live SIEM Closures** | Exactly zero automated closures | **VERIFIED** | Daily closure counter is `0`; FortiSIEM API unmutated. |
| **Empirical Reporting** | Truthful ground-truth count | **VERIFIED** | `total_analyst_reviews = 0`, `accuracy = NOT MEASURABLE`. |
| **UPLA Human Approval Gates** | Gate 1 & Gate 2 mandatory | **VERIFIED** | Explicit interactive approvals required for GitHub and deploy. |
