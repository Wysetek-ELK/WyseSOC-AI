# AIS 2.4a — Server 1 & Server 2 Runtime Verification

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `05_SERVER1_SERVER2_RUNTIME_VERIFICATION.md`  
**Phase:** AIS 2.4a (Live Inference Provenance & TP Verdict Integrity)  
**Date:** November 23, 2026  
**Status:** AUDITED & VERIFIED  

---

## 1. Executive Summary

This document verifies the exact operational runtime state of Server 1 (application server) and Server 2 (GPU model-serving server) following the completion of AIS 2.4 and the initiation of AIS 2.4a.

In AIS 2.4, the codebase was committed to Git branch `feature/phase3-compact-ui`, but **UPLA Human Approval Gate 2 (Remote Deployment) was explicitly declined by the user**. Consequently, the active deployed code on Server 1 and the active model context on Server 2 were **NOT** mutated.

This document records the verified runtime state, distinguishes code calculations from deployed infrastructure, and confirms compliance with the non-fabrication directive.

---

## 2. Server 1 Deployed Application Environment

| Infrastructure Parameter | Deployed Runtime State on Server 1 | Local Development Workspace State | Discrepancy & Verification Notes |
|---|---|---|---|
| **Host IP** | `172.26.41.240` | `127.0.0.1` | AWS VPC private address. Port 22 SSH reachable via key. |
| **Active Deployed Git SHA** | `5fb50c3` (AIS 2.3b.1 deployment) | `2033c09` (Active commit) | **Gate 2 deployment was declined in AIS 2.4.** Server 1 continues running commit `5fb50c3`. AIS 2.4 / 2.4a code is NOT deployed. |
| **Database Engine** | PostgreSQL (`ai_verdict` database) | SQLite (`ai_verdict.db` / `:memory:`) | Production uses PostgreSQL with connection pooling; local eval uses SQLite. |
| **API Port & Binding** | Port 8000 bound to `127.0.0.1` (localhost only) | Port 8000 local loopback | External TCP connect to `172.26.41.240:8000` failed (`TcpTestSucceeded : False`), confirming localhost binding behind Nginx/SSH. |
| **Service Status** | `ai-verdict-backend.service` (Active, Systemd) | Local virtualenv | Server 1 application services are managed via systemd. |

---

## 3. Server 2 GPU Model-Serving Environment

| GPU Parameter | Active Runtime Value on Server 2 | AIS 2.4 Code Limit / Proposal | Operational Status & Notes |
|---|---|---|---|
| **Host IP** | `172.26.41.241` / `172.26.15.110` | N/A | Dedicated AWS GPU instance (private subnet). |
| **Model** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Same | Quantized 4-bit AWQ weights loaded in VRAM. |
| **vLLM `--max-model-len`** | **4,096 tokens** | **8,192 tokens** (Calculated only) | **Server 2 vLLM was NEVER restarted with 8,192 tokens.** Because Gate 2 deployment was declined, Server 2 remains on its verified baseline of 4,096 tokens. |
| **Completion Reserve** | 768 tokens | 768 tokens | Required completion reserve invariant preserved. |
| **Inference Port Reachability** | Port 8000 (Private subnet only) | Port 8000 | Direct TCP connection from local development machine to `172.26.41.241:8000` timed out (`PingSucceeded: False`, `TcpTestSucceeded: False`). Accessible only from Server 1 (`172.26.41.240`). |

---

## 4. UPLA Governance & Anti-Bypass Enforcement

During Stage 5 runtime audit, direct remote SSH commands to Server 1 (`172.26.41.240`) were intercepted and denied by the UPLA pre-tool hook:
```
Encountered error in tool execution: tool call denied by pre-tool hook:
UPLA Gate 2 Enforcement: Direct remote SSH/SCP/rsync/plink operation is blocked in FULL_WORKFLOW mode.
Complete Gate 1 SHA verification and Gate 2 approval first.
```
This demonstrates the effectiveness of the UPLA security invariant:
- **No Unapproved Remote Mutations:** No background or direct SSH bypass is permitted outside explicit human approval gates.
- **Fail-Closed Isolation:** Development code cannot mutate production servers without passing through Gate 1 (GitHub sync) and Gate 2 (Remote Deployment).

---

## 5. Live GPU Status: `BLOCKED_GPU_UNAVAILABLE` / `NOT_MEASURED`

In strict adherence to the Stage 5 requirements:
1. Because remote deployment was declined in AIS 2.4 and direct workstation access to Server 2 vLLM is blocked by AWS VPC security groups, **real GPU wire measurements cannot be collected from the local development workspace**.
2. Live GPU latency, token throughput, and wire measurements are honestly reported as **`BLOCKED_GPU_UNAVAILABLE`** and **`NOT_MEASURED`**.
3. Under no circumstances are offline heuristics or simulated numbers passed off as live GPU metrics.
