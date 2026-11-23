# AIS 2.4b — Deployment and GPU Runtime Verification Report

**Document ID:** AIS-2.4B-07  
**Version:** 1.0  
**Date:** 2026-11-23  
**Status:** COMPLETE / INFRASTRUCTURE AUDITED  
**Classification:** Restricted — Internal Security Evaluation  

---

## 1. Executive Summary

This report provides the comprehensive architecture, network topology, runtime state, and deployment readiness audit of the Verdictum AI — Agent Intelligence Studio (AIS) production environment.

The audit verified:
1. **Server 1 Status:** Currently running Git commit `5fb50c3` (AIS 2.3b.1). AIS 2.4 (`2033c09`) and AIS 2.4a (`2d97bed`) are merged to `origin/feature/phase3-compact-ui` but were NOT deployed because Human Approval Gate 2 was declined in prior phases.
2. **Server 2 Status:** Active vLLM instance serving `Qwen/Qwen2.5-7B-Instruct-AWQ` at maximum context 4,096 tokens with 768 reserved completion tokens.
3. **Network Boundary Isolation:** Server 2 (`172.26.41.241`) is hosted in a private AWS VPC subnet accessible exclusively from Server 1 (`172.26.41.240`). Direct TCP access from the local developer workstation to port 8000 is blocked (`TcpTestSucceeded: False`).
4. **Context Expansion Readiness (8,192 Tokens):** A complete, reversible procedure for expanding Server 2 to 8,192 tokens has been formulated, including GPU VRAM headroom calculations and rollback mechanisms.

---

## 2. Infrastructure Inventory & Baseline State

```
+-----------------------------------------------------------------------------------------------------------------------+
| Component          | Host / IP              | OS / Platform     | Software / Service         | Current Deployed State |
+--------------------+------------------------+-------------------+----------------------------+------------------------+
| Application Server | Server 1: 172.26.41.240| Ubuntu 22.04 LTS  | FastAPI / Next.js / Celery | Commit 5fb50c3         |
| Database Server    | Server 1: 172.26.41.240| PostgreSQL 15     | postgresql.service         | Operational            |
| LLM Provider Host  | Server 2: 172.26.41.241| Ubuntu 22.04 LTS  | vLLM v0.6.3 / CUDA 12.4    | Context: 4,096 tokens  |
| Model Artifact     | Server 2               | HuggingFace Hub   | Qwen2.5-7B-Instruct-AWQ    | AWQ 4-bit Quantized    |
| Source Repository  | GitHub (Remote)        | Wysetek-ELK       | feature/phase3-compact-ui  | Commit 2d97bed         |
| Local Workstation  | Developer Machine      | Windows 11        | PowerShell / Python 3.12   | Commit 2d97bed + diff  |
+-----------------------------------------------------------------------------------------------------------------------+
```

---

## 3. Network Topology & Isolation Model

```
+-------------------------------------------------------------------------------------------+
|                                    AWS VPC (172.26.0.0/16)                                |
|                                                                                           |
|   +--------------------------+                         +------------------------------+   |
|   |         SERVER 1         |                         |           SERVER 2           |   |
|   |      172.26.41.240       |    Private VPC Subnet   |        172.26.41.241         |   |
|   |                          |    (Port 8000 ALLOWED)  |                              |   |
|   |  - FastAPI Backend (8000)|------------------------>|  - vLLM Service (8000)       |   |
|   |  - Next.js UI (3000)     |                         |  - Qwen2.5-7B-Instruct-AWQ   |   |
|   |  - PostgreSQL (5432)     |                         |  - Context: 4,096 (curr)     |   |
|   |  - Celery Worker         |                         |                              |   |
|   +--------------------------+                         +------------------------------+   |
|                 ^                                                     ^                   |
|                 |                                                     |                   |
+-----------------|-----------------------------------------------------|-------------------+
                  |                                                     |
             SSH (Port 22)                                    TCP 8000 BLOCKED
               ALLOWED                                      (Security Group Deny)
                  |                                                     |
        +-------------------+                                           |
        | Local Workstation |-------------------------------------------+
        +-------------------+
```

### Direct Reachability Verification:
- `Test-NetConnection -ComputerName 172.26.41.240 -Port 22` -> **SUCCESS** (`TcpTestSucceeded: True`)
- `Test-NetConnection -ComputerName 172.26.41.241 -Port 8000` -> **FAILED** (`TcpTestSucceeded: False`)

This confirms that the local developer environment cannot directly dispatch HTTP inference requests to Server 2. All live inference must be initiated either on Server 1 or via backend APIs dispatched through Server 1.

---

## 4. Context Window Expansion Plan (8,192 Tokens)

### 4.1 Theoretical & Empirical VRAM Feasibility
- **GPU Hardware:** NVIDIA L4 (24 GB GDDR6) / A10G (24 GB)
- **Model Weights (AWQ 4-bit):** ~4.3 GB
- **Base CUDA / PyTorch Overhead:** ~1.2 GB
- **KV Cache per 1,000 tokens (Qwen2.5-7B):** ~0.22 GB (fp16 KV cache)
- **At 4,096 tokens (Concurrency = 4):**
  $$\text{VRAM} = 4.3 + 1.2 + (4 \times 4.096 \times 0.22) = 5.5 + 3.6 = 9.1\text{ GB} \le 24\text{ GB}$$
- **At 8,192 tokens (Concurrency = 4):**
  $$\text{VRAM} = 4.3 + 1.2 + (4 \times 8.192 \times 0.22) = 5.5 + 7.2 = 12.7\text{ GB} \le 24\text{ GB}$$
- **Conclusion:** Expanding to 8,192 tokens is physically feasible on 24 GB hardware, retaining >11 GB safety headroom for memory fragmentation.

### 4.2 Step-by-Step Reversible Execution Procedure
1. **Service Configuration Modification (on Server 2):**
   ```bash
   # /etc/systemd/system/vllm.service
   # Change:
   # ExecStart=/usr/local/bin/vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --port 8000 --max-model-len 4096
   # To:
   ExecStart=/usr/local/bin/vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --port 8000 --max-model-len 8192 --gpu-memory-utilization 0.90
   ```
2. **Reload & Restart:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart vllm.service
   ```
3. **Health Check Verification (from Server 1):**
   ```bash
   curl -s http://172.26.41.241:8000/health
   # Expected: {"status": "ok"}
   curl -s http://172.26.41.241:8000/v1/models | jq .
   ```
4. **Rollback Procedure:**
   If vLLM experiences Out-of-Memory (OOM) or startup failure, immediately revert the service file to `--max-model-len 4096`, run `systemctl daemon-reload`, and restart.

---

## 5. Server 1 Deployment Plan (AIS 2.4b)

### 5.1 Deployment Prerequisites
1. Human Approval Gate 1 passed (GitHub sync).
2. Remote commit SHA verified on `origin/feature/phase3-compact-ui`.
3. Human Approval Gate 2 explicitly granted by user.

### 5.2 Server 1 Target Operations
1. **Git Fetch & Checkout:**
   ```bash
   cd /opt/verdictum/WyseSOC-AI
   git fetch origin feature/phase3-compact-ui
   git checkout <TARGET_COMMIT_SHA>
   ```
2. **Backend Dependencies & Validation:**
   ```bash
   source venv/bin/activate
   pip install -r backend/requirements.txt
   pytest backend/tests/test_ais_2_4b_validator_integrity.py
   ```
3. **Database Migration Check:**
   No schema changes are required for AIS 2.4b. Existing PostgreSQL database schema is preserved.
4. **Service Restart:**
   ```bash
   sudo systemctl restart verdictum-backend.service
   sudo systemctl restart verdictum-celery.service
   ```
5. **Post-Deployment Verification:**
   - Verify API health: `curl http://localhost:8000/api/v1/health`
   - Verify AIS benchmark endpoint: `curl http://localhost:8000/api/v1/ais/benchmark/status`
   - Verify UI rendering: `curl -I http://localhost:3000`

---

## 6. UPLA Governance Gate Status

| Gate | Target | Status | Reason / Condition |
|---|---|---|---|
| **Gate 1** | GitHub Remote Sync | **PENDING USER APPROVAL** | Code changes completed and regression-tested. |
| **Gate 2** | Remote Deployment (Server 1 & 2) | **PENDING GATE 1 PASS** | Requires explicit user authorization after Gate 1 remote SHA verification. |

**Strict Policy Invariant:** No deployment commands will be executed until both Gate 1 and Gate 2 are explicitly approved by the user via native `ask_question` dialogues.
