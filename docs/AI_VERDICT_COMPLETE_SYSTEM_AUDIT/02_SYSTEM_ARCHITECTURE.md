# AI Verdict — Complete System Audit: System Architecture

> **Audit Report Reference:** `02_SYSTEM_ARCHITECTURE.md`  
> **Audited System:** AI Verdict (Agentic SOC Intelligence Platform)  
> **Topology:** Two-Server Tiered Architecture (Platform Core & GPU Inference Node)  

---

## 1. High-Level Architectural Model

AI Verdict operates under an enterprise **Two-Server Topology** designed to isolate core SOC web services, REST APIs, SIEM continuous polling, and database persistence from GPU-accelerated local Large Language Model (LLM) inference workloads.

```mermaid
flowchart TB
    subgraph ClientTier["Analyst Workstation Tier"]
        Browser["Analyst Web Browser\n(Edge / Chrome / Firefox)\n- App Router UI\n- Blind Review Mode\n- Agent Policy Studio"]
    end

    subgraph Server1["Server 1: Platform & Application Server (Ubuntu 22.04 / 24.04 LTS)"]
        Nginx["Nginx Reverse Proxy (:80 / :443)\n- Modern TLS (1.2 / 1.3)\n- Security Headers (CSP, HSTS)\n- Proxy timeouts (300s)\n- Gzip & Rate Limiting"]
        
        subgraph FrontendLayer["Frontend Engine (:3000)"]
            NextJS["Next.js 16.4.5 (App Router)\n- React 19.3.0\n- Tailwind CSS v4\n- Dynamic AppContext"]
        end

        subgraph BackendLayer["Backend REST API Engine (:8000)"]
            FastAPI["FastAPI 0.110+ ASGI Engine\n(Python 3.13.13)"]
            Poller["Sentinel Ingest Worker\n(FortiSIEMSyncScheduler 180s Async Loop)"]
            ZipGuard["Payload Sanitization Guard\n(ZipGuard Traversal & Bomb Defense)"]
            Allowlist["Evidence Integrity Guardrail\n(model_payload_allowlist.py)"]
            PolicyEngine["Agent Policy Engine\n(PromptStudioService 9-Section Directives)"]
            TriageAgent["Verdict Triage Agent\n(AIVerdictService Dynamic Assembler)"]
            HealthMonitor["Inference Health Monitor\n(SystemMonitorService Telemetry)"]
        end

        subgraph StorageLayer["Persistent Storage Layer"]
            Database[("PostgreSQL 16+ / SQLite (ai_verdict.db)\n- SQLAlchemy 2.x Async Engine\n- 13 Relational Tables\n- Ground-Truth Segregated")]
        end
    end

    subgraph Server2["Server 2: Local AI Inference Node (Private GPU Host)"]
        InferenceDaemon["vLLM High-Throughput Engine / Ollama (:8000 / :11434)\n- OpenAI-Compatible REST API (/v1/chat/completions)\n- Strict JSON Generation Schema"]
        GPU["NVIDIA Tensor Core GPU (e.g. AWS T4 16GB / A10G 24GB)\n- PyTorch CUDA 12.x\n- Qwen 2.5 7B Instruct AWQ (4-bit Quantized)"]
    end

    subgraph SIEMTier["Enterprise SIEM Layer"]
        FortiSIEM["FortiSIEM Supervisor / Worker Cluster (:443)\n- REST API (/phoenix/rest/pub/incident)\n- XML/JSON Incident Telemetry\n- SIEM Detection Rule Definitions"]
    end

    %% Client Communication
    Browser <-->|HTTPS:443 / WSS| Nginx
    Nginx <-->|HTTP:3000 (Proxy Pass /*)| NextJS
    Nginx <-->|HTTP:8000 (Proxy Pass /api/*)| FastAPI
    NextJS <-->|JSON REST Fetch (Client/SSR)| FastAPI

    %% Server 1 Internal Communication
    FastAPI <-->|SQLAlchemy Async Sessions| Database
    Poller <-->|Async Ingestion & DB Upsert| Database
    FastAPI <-->|Payload Sanitization| Allowlist
    Allowlist <-->|Filtered Attributes| TriageAgent

    %% Ingestion & SIEM Integration
    Poller <-->|HTTPS:443 (Basic Auth / API Token)| FortiSIEM
    FastAPI <-->|On-Demand Pull / Rule Sync| FortiSIEM

    %% Inference Network Channel
    TriageAgent <-->|Private Network HTTP:8000 (/v1/chat/completions)| InferenceDaemon
    InferenceDaemon <-->|Tensor Execution & VRAM KV-Cache| GPU
```

---

## 2. Server Roles & Network Boundaries

### 2.1 Server 1: Core Platform & Application Node

- **Host Specifications (Target):** 4-8 vCPUs, 16-32 GB RAM, 100+ GB NVMe SSD.
- **Operating System:** Ubuntu 22.04 / 24.04 LTS (bare-metal or AWS EC2 `t3.xlarge` / `c6i.xlarge`).
- **Network Ingress:**
  - Port 80 (HTTP) -> Redirects 301 to Port 443.
  - Port 443 (HTTPS) -> Handled by Nginx reverse proxy.
  - Port 22 (SSH) -> Restricted to administrative bastion hosts.
- **Process Supervision:** Native Ubuntu `systemd` daemon managing two services:
  - `ai-verdict-backend.service`: Runs Uvicorn ASGI on `127.0.0.1:8000`.
  - `ai-verdict-frontend.service`: Runs Next.js node production server on `127.0.0.1:3000`.
- **Database Architecture:**
  - Default Local/Development: SQLite database via `aiosqlite` at `backend/ai_verdict.db`.
  - Production: Dedicated PostgreSQL 16+ instance via `asyncpg`.

### 2.2 Server 2: Local AI Inference Node

- **Host Specifications (Target):** AWS EC2 `g4dn.2xlarge` (1x NVIDIA T4 GPU with 16 GB VRAM, 8 vCPUs, 32 GB RAM).
- **Network Ingress:**
  - Port 8000 (vLLM) or Port 11434 (Ollama).
  - **Strict Security Group / Firewall Constraint:** Enforced by UFW (`ufw allow from <SERVER_1_PRIVATE_IP> to any port 8000 proto tcp`). Public internet access to port 8000 is blocked.
- **Inference Stack:**
  - Engine: `vLLM` high-throughput PagedAttention server.
  - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ` (4-bit activation-aware weight quantization).
  - Context Window: 4,096 tokens max; max output tokens capped at 350.

---

## 3. Communication Channels & Protocols

| Link | Protocol | Source | Target | Encryption & Auth | Timeout & Retries |
|---|---|---|---|---|---|
| **Analyst to Server 1** | HTTPS (HTTP/2) | Browser | Nginx (:443) | TLS 1.3 / Strict CSP / HttpOnly Cookie | 300s proxy timeout |
| **Nginx to Frontend** | HTTP/1.1 | Nginx | Next.js (:3000) | Localhost unencrypted loopback | 60s timeout |
| **Nginx to Backend** | HTTP/1.1 | Nginx | FastAPI (:8000) | Localhost unencrypted loopback | 300s timeout |
| **Backend to Database** | PostgreSQL / SQLite | FastAPI | DB Engine | Socket / TCP TLS (PostgreSQL) | Connection pool (size 20, max_overflow 10) |
| **Server 1 to Server 2** | HTTP/1.1 | FastAPI | vLLM (:8000) | Private IP plaintext / Bearer `LOCAL_LLM_API_KEY` | 60s timeout; 0 automatic retries |
| **Server 1 to FortiSIEM**| HTTPS | Poller / API | FortiSIEM (:443)| TLS (configurable `FORTISIEM_VERIFY_SSL`) / HTTP Basic | 25s timeout (configurable via `.env`) |

---

## 4. Blast Radius & Failure Isolation Analysis

1. **Server 2 (LLM Node) Crash or Network Severance:**
   - **Architectural Design:** If Server 2 goes offline, `AIVerdictService.is_local_llm_available()` evaluates to `False`. Incoming incidents from SIEM polling are ingested into persistent storage with `ai_verdict = None`.
   - **Audited Vulnerability (`AV-004`):** Because `.env` sets `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true`, connection drops trigger `SimulatedModelProvider`, emitting heuristic simulated verdicts instead of holding incidents in backlog.

2. **FortiSIEM Supervisor Unreachability:**
   - **Architectural Design:** If FortiSIEM returns 404, 500, or times out, the continuous poller catches the exception, logs a warning, and retries in 180 seconds.
   - **Audited Vulnerability:** The synchronous timeout of 25-30s in test and live queries blocks async event loops if multiple synchronous calls occur concurrently.

3. **Database Unavailability:**
   - **Architectural Design:** Ingestion jobs and API calls fail immediately with HTTP 500. No telemetry is dropped in memory queues without database confirmation.

4. **Frontend Crash:**
   - **Architectural Design:** Managed by systemd with `Restart=always`. The backend continues continuous SIEM ingestion and queue processing unimpeded.

---

## 5. Architectural Compliance vs Claims

| Architecture Directive | Claimed in Documentation | Code Verification | Gap / Audit Assessment |
|---|---|---|---|
| **No External Managed AI** | Zero OpenAI, Anthropic, Gemini calls. | **VERIFIED.** Source code contains no external LLM API client libraries (openai, anthropic, google-generativeai). | Fully compliant with local-only mandate. |
| **Two-Server Separation** | Platform on Server 1, GPU on Server 2. | **VERIFIED.** HTTP client connects across private IP boundaries to OpenAI-compatible server. | Fully compliant with physical separation mandate. |
| **Zero SIEM Write-Back** | System is read-only dry-run; no ticket modification in upstream SIEM. | **VERIFIED.** FortiSIEM service contains only `GET` and read endpoints; no `PUT`, `POST /incident/update`, or ticket closure writes exist. | Fully compliant with passive monitoring mandate. |
| **Zero External IP Probing**| Fully air-gapped / private operations. | **FAILED.** `LLMConfigService.get_server1_outbound_ip()` actively queries `api.ipify.org`, `ifconfig.me`, and `icanhazip.com`. | Violation of air-gap / boundary privacy (`AV-011`). |

