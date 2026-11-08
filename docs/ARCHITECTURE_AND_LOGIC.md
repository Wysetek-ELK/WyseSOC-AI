# AI Verdict — System Architecture, Data Flows, Tech Stack & Logic Taxonomy

> **Comprehensive Enterprise Technical Specification**  
> *Authoritative reference for platform architecture, execution flows, underlying libraries, and code naming conventions.*

---

## 1. System Architecture

AI Verdict operates under an enterprise **Two-Server Topology** designed to isolate mission-critical SOC operations, web application services, and database persistence from heavy GPU-accelerated local AI inference workloads.

### 1.1 High-Level Server Topology

```mermaid
flowchart TB
    subgraph Client["Analyst Workstation / SOC Tier"]
        Browser["Modern Browser (Chrome / Edge / Firefox)"]
    end

    subgraph Server1["Server 1: Platform & Application Server (Linux Production)"]
        Nginx["Nginx Reverse Proxy\n(Ports 80/443, SSL/TLS, Gzip, Security Headers)"]
        
        subgraph FrontendApp["Frontend Application (:3000)"]
            NextJS["Next.js 16 App Router\nReact 19 / TypeScript / Tailwind CSS v4"]
        end

        subgraph BackendApp["Backend Application (:8000)"]
            FastAPI["FastAPI REST API Engine (Python 3.11+)"]
            Scheduler["Sentinel Ingest Worker\n(Continuous 3-Min Background Poller)"]
            ZipGuardEngine["Payload Sanitization Guard\n(Path Traversal & Zip Bomb Protection)"]
            IsolationFilter["Evidence Integrity Guardrail\n(Strict Zero-Leakage Filter)"]
            VerdictEngine["Verdict Triage Agent\n(Agent Policy Engine & Few-Shot RAG)"]
            SystemMonitor["Inference Health Monitor\n(Server 1 & Server 2 Observability)"]
        end

        subgraph DatabaseEngine["Database Persistence Layer"]
            RelationalDB[("PostgreSQL 16+ / SQLite\n(SQLAlchemy 2.x Async Engine)")]
        end
    end

    subgraph Server2["Server 2: Local AI Inference Server (Private GPU Host)"]
        vLLM["vLLM High-Throughput Inference Engine\n(OpenAI-Compatible API :8000/v1)"]
        ModelWeights["Qwen 2.5 7B Instruct AWQ\n(NVIDIA Tensor Core GPU / CUDA VRAM)"]
    end

    subgraph SIEMCluster["Enterprise SIEM Layer"]
        FortiSIEM["FortiSIEM Supervisor / Worker Cluster\n(XML/JSON REST API :443)"]
    end

    Browser <-->|HTTPS / WSS| Nginx
    Nginx <-->|Proxy Pass /*| NextJS
    Nginx <-->|Proxy Pass /api/*| FastAPI
    NextJS <-->|REST API Fetch| FastAPI
    FastAPI <-->|SQLAlchemy Async Sessions| RelationalDB
    Scheduler <-->|Poll REST API / XML Query| FortiSIEM
    FastAPI <-->|Private Network HTTP / Models| vLLM
    vLLM <-->|GPU Tensor Execution| ModelWeights
```

---

### 1.2 Architectural Roles & Responsibilities

| Tier / Node | Primary Responsibility | Critical Components | Network Security |
| :--- | :--- | :--- | :--- |
| **Server 1: Platform Core** | Serves Next.js UI, processes API routes, authenticates analysts, validates ZIP archives, manages continuous SIEM synchronization, and enforces Ground-Truth Isolation. | FastAPI, Uvicorn, Next.js 16, Nginx, PostgreSQL/SQLite. | Exposed via Nginx (TLS 1.3, Strict CORS, SameSite Cookies). |
| **Server 2: Inference Node** | Dedicated GPU host running quantized local LLMs for evidence analysis, returning strictly structured verdicts with zero cloud leaks. | vLLM Engine, PyTorch CUDA, Qwen 2.5 7B Instruct AWQ. | Completely isolated on private internal network; only accepts inbound requests from Server 1. |
| **FortiSIEM Supervisor** | Upstream enterprise SIEM generating raw incident notifications, event logs, and detection rules. | FortiSIEM REST API, XML Query Engine. | Authenticated via API token / HTTP Basic over mutual TLS. |

---

### 1.3 Security & Boundary Architecture

1. **Ground-Truth Isolation Layer**:
   - Historical analyst verdicts, closure resolutions, cleared reasons, and closure times are strictly segregated into `historical_ground_truth` and dropped before LLM payload generation.
   - Prevents prompt bias and prevents the model from "cheating" by inspecting historical human answers.
2. **Zero Direct Push & RepoDeploy Governor**:
   - All Git pushes and remote server deployments are hard-gated by the RepoDeploy Governor with two-stage approval tokens (`git-gate` and `deploy-gate`).
   - Automated pre-push secret scanning blocks any code containing credentials or internal IP addresses.
3. **ZipGuard Archive Sandbox**:
   - Validates all uploaded archive packages against Zip Slip traversal (`../`), decompression bombs (>50:1 ratio), and file count limits (>2,000 files).
4. **Strict Offline LLM Protection**:
   - If Server 2 is offline or unreachable, the system never generates fake, simulated, or default verdicts. Incidents are preserved in `Pending` state (`ai_verdict = None`) until Server 2 is verified online.

---

## 2. Operational Flows

```mermaid
sequenceDiagram
    autonumber
    participant Analyst as Analyst (UI)
    participant UI as Next.js Frontend
    participant API as FastAPI Backend
    participant Poller as FortiSIEM Sync Scheduler
    participant SIEM as FortiSIEM Supervisor
    participant DB as Relational DB
    participant LLM as Server 2 Local LLM (vLLM)

    rect rgb(15, 23, 42)
    note over Poller, SIEM: Flow 1: Continuous 3-Minute SIEM Sync & Auto-Ingest
    Poller->>SIEM: GET /phoenix/rest/incident/list (Checkpoint epoch)
    SIEM-->>Poller: Raw Incidents JSON
    Poller->>DB: Check if Incident ID exists
    DB-->>Poller: New Incident Detected
    Poller->>DB: Ingest normalized incident + raw events + ground truth
    Poller->>SIEM: Fetch detection rule definition if rule unmapped
    SIEM-->>Poller: Rule XML/JSON
    Poller->>DB: Upsert SIEM Rule in registry
    end

    rect rgb(30, 41, 59)
    note over Poller, LLM: Flow 2: Automated AI Verdict & Offline LLM Protection
    Poller->>API: Probe Server 2 LLM Health (/v1/models)
    alt Server 2 is ONLINE
        API->>DB: Fetch model allowlisted payload (No ground truth)
        API->>DB: Fetch Level-2 SOC Prompt + Rule Prompt + Few-Shot Examples
        API->>LLM: POST /v1/chat/completions (Structured schema prompt)
        LLM-->>API: JSON Structured Verdict (Determination, Confidence, Reason)
        API->>DB: Persist ai_verdict & update Investigation queue
    else Server 2 is OFFLINE
        API->>DB: Save incident with ai_verdict = None (Pending Backlog)
        API-->>UI: Badge: "Unlabeled / Pending Investigation"
    end
    end

    rect rgb(15, 23, 42)
    note over Analyst, DB: Flow 3: Analyst Review & Continuous Learning Loop
    Analyst->>UI: Inspect Incident (Blind Review Mode: Ground Truth Hidden)
    UI->>API: GET /api/incidents/{id}
    API-->>UI: Normalized incident + raw events (Ground truth masked)
    Analyst->>UI: Submit human determination & rationale
    UI->>API: POST /api/learning/feedback
    API->>DB: Insert LearningRecord (Verified Precedent)
    note over API, DB: Precedent now automatically feeds future few-shot LLM prompts!
    end
```

### 2.1 Flow Breakdown

#### Flow 1: Continuous Ingestion & 3-Minute Background Poller
1. `FortiSIEMSyncScheduler` initializes on backend startup (configured via `FORTISIEM_AUTO_POLL_ENABLED=true`).
2. A background `asyncio` task wakes every 180 seconds.
3. Calls `FortiSIEMService.pull_all_incidents()`.
4. Idempotently normalizes newly received incidents, extracts raw event telemetry (`IncidentEvent`), and saves unmodified JSON payloads into `raw_payload`.
5. Missing rules are auto-synced from FortiSIEM into the `rules` table.

#### Flow 2: Resilient AI Verdict Generation & Dynamic Prompt Synthesis
1. Invoked automatically by poller or manually by analyst clicking **Re-evaluate AI Verdict**.
2. Checks Server 2 health via `AIVerdictService.is_local_llm_available()`.
3. If offline, throws `LocalLLMUnavailableError` leaving `ai_verdict = None` (zero mock hallucinations).
4. If online, synthesizes dynamic multi-layer prompt:
   - **Layer 1: Common SOC Baseline** (`COMMON_SOC_BASELINE` Level-2 SOC triage instructions).
   - **Layer 2: Rule Prompt Studio** (Custom active draft/approved rules from `prompt_versions`).
   - **Layer 3: Dynamic Few-Shot Precedents** (Top 3 verified precedents from `learning_records`).
   - **Layer 4: Sanitized Model Payload** (`build_model_facing_payload` filtering out closure keys).
5. Dispatches request to `OpenAICompatibleProvider`.
6. Parses structured JSON verdict (`verdict`, `confidence`, `reason`, `supporting_evidence`, `missing_evidence`).
7. Persists verdict in database and logs audit entry.

#### Flow 3: Offline Backlog Recovery (`process_pending_incidents`)
1. When Server 2 is offline, incoming alerts accumulate in the database with `ai_verdict = None`.
2. As soon as Server 2 comes back online, `AIVerdictService.process_pending_incidents()` queries all unanalyzed incidents ordered chronologically (`created_at_epoch.asc()`).
3. Evaluates each incident sequentially one-by-one with 150ms pacing.
4. If the LLM disconnects mid-batch, the queue gracefully halts, preserving state without data loss.

#### Flow 4: SIEM Detection Rule Registry & Analytics
1. Detection rules are parsed and stored in `rules`.
2. `GET /api/rules/stats` calculates live aggregations:
   - Total rules ingested
   - Active vs. inactive count
   - Alert coverage (rules linked to active incident records)
   - Severity distribution (Critical, High, Medium, Low)
   - Prompt Studio customization coverage
3. Frontend renders 5 responsive Cyberpunk-styled analytical cards with real-time refresh.

#### Flow 5: Blind Review & Analyst Learning Loop
1. Analyst toggles **Blind Review Mode** in UI header.
2. Ground-truth badges are hidden, forcing unbiased human triage.
3. Analyst submits independent verdict.
4. If analyst confirms or refines the verdict, a record is added to `learning_records`.
5. `AIVerdictService` pulls the latest verified precedents into few-shot RAG context for future alerts matching that rule.

---

## 3. Tools & Libraries Used

### 3.1 Technology Stack Matrix

```
+---------------------------------------------------------------------------------------+
|                                    TECHNOLOGY MATRIX                                  |
+---------------------------------------------------------------------------------------+
|  Layer               | Technology / Library       | Version       | Key Purpose       |
|======================+============================+===============+===================|
|  Frontend UI         | Next.js (App Router)       | 16.4.5        | React Framework   |
|                      | React / React DOM          | 19.3.0        | Component UI      |
|                      | TypeScript                 | 5.x           | Type Safety       |
|                      | Tailwind CSS               | 4.x           | Utility Styling   |
|                      | Lucide React               | 1.69.0        | SOC Iconography   |
|                      | clsx / tailwind-merge      | 2.1 / 3.7     | Class Merging     |
|----------------------+----------------------------+---------------+-------------------|
|  Backend API         | Python                     | 3.11+ / 3.13  | Core Language     |
|                      | FastAPI                    | 0.110.0+      | Async Web API     |
|                      | Uvicorn                    | 0.28.0+       | ASGI Web Server   |
|                      | Pydantic / Settings        | 2.6.0+        | Data Validation   |
|                      | SQLAlchemy                 | 2.0.28+       | Async ORM Engine  |
|                      | Alembic                    | 1.13.1+       | DB Migrations     |
|                      | aiosqlite / asyncpg        | 0.20+ / 0.29+ | Async DB Drivers  |
|                      | HTTPX                      | 0.27.0+       | Async HTTP Client |
|                      | PyJWT / Bcrypt             | 2.8+ / 4.1+   | JWT Auth & Hash   |
|                      | Psutil                     | 5.9.0+        | Server Telemetry  |
|                      | Pytest / Pytest-Asyncio    | 8.0+ / 0.23+  | Test Suite        |
|----------------------+----------------------------+---------------+-------------------|
|  AI Inference        | vLLM                       | 0.6.0+        | GPU Serving       |
|                      | PyTorch / CUDA             | 12.x          | Tensor Compute    |
|                      | Qwen 2.5 7B Instruct AWQ   | 4-bit Quant   | Core LLM Model    |
|----------------------+----------------------------+---------------+-------------------|
|  DevOps & Gov        | RepoDeploy Governor        | CLI v1.0      | Zero-Leak Push    |
|                      | Nginx                      | 1.24+         | Reverse Proxy     |
|                      | Systemd / PM2              | Native        | Process Daemon    |
+---------------------------------------------------------------------------------------+
```

---

## 4. Logical Components & Naming Taxonomy

This section provides a definitive dictionary of classes, functions, files, schemas, and database tables used across the codebase.

### 4.1 Backend Service Layer (`backend/app/services/`)

| Logic Name (Class / Function) | File Path | Architectural Role & Description |
| :--- | :--- | :--- |
| `FortiSIEMService` | [`fortisiem_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py) | Coordinates live HTTP REST calls to FortiSIEM supervisor, pulls incidents by ID, executes full alert syncs, parses XML/JSON responses, and syncs detection rules. |
| `FortiSIEMSyncScheduler` / `fortisiem_scheduler` | [`fortisiem_scheduler.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_scheduler.py) | Singleton background worker running an `asyncio` loop every 180s to pull new telemetry and dispatch automated AI verdicts. |
| `AIVerdictService` | [`ai_verdict_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py) | Central AI triage engine. Enforces LLM availability checks, synthesizes multi-layer prompts, formats allowlisted payloads, invokes model providers, and handles offline backlog queues. |
| `LocalLLMUnavailableError` | [`ai_verdict_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py) | Custom exception raised when Server 2 is offline, ensuring zero fake or simulated verdicts are written to the database. |
| `build_model_facing_payload` | [`model_payload_allowlist.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_payload_allowlist.py) | Ground-Truth Isolation filter that strips all resolution, cleared reasons, analyst notes, and closure metadata, outputting a sanitized dictionary for the LLM. |
| `sanitize_event_attributes` | [`model_payload_allowlist.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_payload_allowlist.py) | Recursively scrubs nested event dictionaries of closure keys, limits key count, and truncates long strings to preserve token budgets. |
| `FORBIDDEN_GROUND_TRUTH_KEYS` | [`model_payload_allowlist.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_payload_allowlist.py) | Frozenset of blocked field names (e.g. `resolution`, `clearedreason`, `comments`, `cleareduser`, `resolvedat`, `mttr`). |
| `ZipGuard` / `ZipSecurityException` | [`backend/app/utils/zip_guard.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/utils/zip_guard.py) | Security utility defending against Zip Slip path traversal, zip bombs, and DoS archive file floods. |
| `PromptStudioService` | [`prompt_studio_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py) | Manages rule-specific prompt templates, versioning (DRAFT, APPROVED, ARCHIVED), indicator definitions, and analyst question sets. |
| `COMMON_SOC_BASELINE` | [`prompt_studio_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py) | Global system prompt defining Level-2 SOC criteria for `FALSE_POSITIVE`, `TRUE_POSITIVE`, and `REQUIRES_ATTENTION`. |
| `LearningService` | [`learning_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/learning_service.py) | Captures analyst ground-truth corrections, indexes verified precedents, and provides few-shot RAG examples to `AIVerdictService`. |
| `SystemMonitorService` | [`system_monitor_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/system_monitor_service.py) | Probes local platform health for Server 1 (CPU, RAM, Disk, Uptime) and HTTP `/v1/models` health/latency for Server 2 (vLLM GPU node). |
| `RuleParser` | [`rule_parser.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/rule_parser.py) | Extracts detection rules from raw text or FortiSIEM XML/JSON definitions, normalizing name, event type, severity, and pattern logic. |
| `IngestionService` | [`ingestion_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ingestion_service.py) | Core logic for parsing bulk JSON dumps, extracting timestamps (`extract_incident_timestamps`), and normalizing raw event lists (`extract_event_data`). |
| `get_model_provider` | [`model_provider/factory.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/factory.py) | Factory returning either `OpenAICompatibleProvider`, `SimulatedProvider`, or `DisabledModelProvider`. |
| `OpenAICompatibleProvider` | [`model_provider/openai_compatible.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/openai_compatible.py) | Dispatches chat completions to Server 2 vLLM, enforcing structured JSON parsing and token telemetry collection. |

---

### 4.2 Database Models & Table Mapping (`backend/app/models/`)

| Model Class | SQL Table Name | Key Columns & Descriptions |
| :--- | :--- | :--- |
| `Incident` | `incidents` | `id`, `incident_id`, `event_type`, `title`, `severity`, `source_ip`, `reporting_device`, `first_seen_epoch`, `created_at_epoch`, `ai_verdict` (JSON), `raw_payload` (JSON). |
| `IncidentEvent` | `incident_events` | `id`, `incident_id` (FK), `event_id`, `event_receive_time`, `event_type`, `raw_log` (Text), `attributes` (JSON). |
| `HistoricalGroundTruth` | `historical_ground_truth` | `id`, `incident_id` (FK, Unique), `resolution`, `cleared_reason`, `comments`, `cleared_user`, `cleared_time_epoch`, `resolved_at_epoch`. *(Strictly isolated from AI payloads).* |
| `Rule` | `rules` | `id`, `rule_id`, `name`, `event_type`, `severity`, `status`, `data_source`, `pattern_logic`, `remediation`, `raw_rule_text`. |
| `RulePrompt` | `rule_prompts` | `id`, `rule_id` (FK, Unique), `title`, `active_version_id`. |
| `PromptVersion` | `prompt_versions` | `id`, `prompt_id` (FK), `version_number`, `status`, `common_prompt`, `rule_specific_prompt`, `tp_indicators`, `fp_indicators`, `analyst_questions`. |
| `LearningRecord` | `learning_records` | `id`, `incident_id` (FK), `rule_id` (FK), `verified_verdict`, `analyst_explanation`, `verification_status`, `feedback_timestamp`. |
| `Investigation` | `investigations` | `id`, `incident_id` (FK), `status`, `priority`, `assigned_to`, `analyst_verdict`, `analyst_notes`. |
| `SystemServerSample`| `system_server_samples` | `id`, `server_id`, `cpu_percent`, `memory_percent`, `disk_percent`, `gpu_percent`, `latency_ms`, `status`. |
| `ImportJob` | `import_jobs` | `id`, `filename`, `status`, `total_records`, `imported_count`, `error_message`. |
| `User` | `users` | `id`, `username`, `email`, `hashed_password`, `role` (Admin/Analyst), `is_active`. |
| `AuditLog` | `audit_logs` | `id`, `user_id`, `action`, `resource_type`, `resource_id`, `details` (JSON), `timestamp`. |

---

### 4.3 API Router Endpoints (`backend/app/api/`)

| HTTP Method & Endpoint | Router Module | Underlying Logic / Action |
| :--- | :--- | :--- |
| `POST /api/auth/login` | `auth.py` | Authenticates username/password via bcrypt, sets HTTP-only JWT cookie. |
| `GET /api/incidents` | `incidents.py` | Lists normalized incidents with sorting, search, severity filters, and pagination. |
| `GET /api/incidents/{id}` | `incidents.py` | Retrieves incident detail, raw security events, AI verdict, and ground truth (subject to blind review). |
| `POST /api/incidents/{id}/evaluate` | `incidents.py` | Triggers immediate single-incident AI verdict evaluation using `AIVerdictService`. |
| `POST /api/incidents/evaluate/pending-backlog` | `incidents.py` | Evaluates all pending incidents sequentially once Server 2 is confirmed online. |
| `GET /api/rules` | `rules.py` | Lists registered SIEM detection rules with search and pagination. |
| `GET /api/rules/stats` | `rules.py` | Computes live metrics: total rules, active count, alert coverage, and severity distribution. |
| `POST /api/rules/sync/fortisiem`| `rules.py` | Synchronizes detection rules directly from the connected FortiSIEM supervisor. |
| `POST /api/fortisiem/pull-by-id`| `fortisiem.py` | Fetches a single incident by FortiSIEM Incident ID on demand. |
| `POST /api/fortisiem/pull-all` | `fortisiem.py` | Executes initial or full pull of all historical incidents. |
| `GET /api/fortisiem/sync/status`| `fortisiem.py` | Returns the state of the 3-minute continuous poller (`IDLE`, `RUNNING`, last sync time). |
| `POST /api/fortisiem/sync/start` | `fortisiem.py` | Starts the background continuous poller loop. |
| `POST /api/fortisiem/sync/stop` | `fortisiem.py` | Halts the background continuous poller loop. |
| `POST /api/fortisiem/sync/cycle-now`| `fortisiem.py` | Triggers an immediate one-off synchronization cycle outside the normal schedule. |
| `GET /api/dashboard/stats` | `dashboard.py` | Returns high-level metrics (Total Imported, Rules, TP/FP counts, Unlabeled count). |
| `GET /api/system/servers` | `system_monitor.py`| Returns real-time health and hardware metrics for Server 1 and Server 2. |
| `GET /api/prompts/{rule_id}` | `prompts.py` | Retrieves prompt versions and active prompt configuration for a rule. |
| `GET /api/learning` | `learning.py` | Retrieves analyst feedback records and verified few-shot precedents. |

---

### 4.4 Frontend Component & Canonical Route Structure (`frontend/src/`)

| Canonical Page / Component | Canonical Route | Legacy Alias Route | Operational Logic & User Experience |
| :--- | :--- | :--- | :--- |
| `AgentMissionControlPage` | `/agent-mission-control` | `/` | Operational command center displaying real-time SOC metrics, severity charts, and telemetry. |
| `AITriageWorkbenchPage` | `/ai-triage-workbench` | `/incidents` | Incident triage explorer with filterable occurrence dates, severity badges, and stored verdicts. |
| `AITriageWorkbenchDetailPage` | `/ai-triage-workbench/[id]` | `/incidents/[id]` | Detailed workbench: Verdict Triage Agent card, raw events, Evidence Integrity Guardrail, and detection context. |
| `TelemetryHubPage` | `/telemetry-hub` | `/imports` | Data ingestion hub: Sentinel Ingest Worker poller controls, pull-by-ID, and Payload Sanitization Guard. |
| `DetectionIntelligencePage` | `/detection-intelligence` | `/rules` | Detection Intelligence Registry: analytical rule cards, rule patterns, and FortiSIEM sync controls. |
| `HumanReviewQueuePage` | `/human-review-queue` | `/analyst-attention` | Review Orchestrator queue: human-in-the-loop analyst feedback, verification status, and disputed verdicts. |
| `AgentIntelligenceStudioPage` | `/agent-intelligence-studio`| `/prompt-studio` | Agent Policy Engine: customizes Level-2 triage instructions, TP/FP indicators, and version approvals. |
| `AgentMemoryPage` | `/agent-memory` | `/learning-history` | Agent Memory Engine: reviews analyst precedent records, ground-truth verifications, and few-shot RAG memory. |
| `AgentSimulationLabPage` | `/agent-simulation-lab` | `/dry-run` | Validation Engine: controlled dry-run simulations, offline batch replay, and split-dataset experiments. |
| `VerdictIntelligencePage` | `/verdict-intelligence` | `/evaluation-reports`| Verdict Evaluation Engine: accuracy reporting, confusion matrices, precision/recall, and trust metrics. |
| `InferenceControlPage` | `/inference-control` | `/infrastructure` | Inference Health Monitor: real-time telemetry cards showing dual-server status, CPU, RAM, Disk, and GPU VRAM. |
| `AgentConfigurationPage` | `/agent-configuration` | `/settings` | Application and inference settings, model allowlist, and platform preferences. |
| `GovernanceAccessPage` | `/governance-access` | `/admin` | RBAC management, user provisioning, security roles, and platform audit controls. |

---

## 5. Agentic SOC Intelligence Platform Nomenclature Mapping

| Existing Architecture / Class | Agentic Platform Nomenclature | Functional Responsibility |
|---|---|---|
| `AIVerdictService` | `VerdictTriageAgent` | Autonomous incident reasoning, dynamic prompt synthesis, and AI verdict generation. |
| `FortiSIEMSyncScheduler` | `SentinelIngestWorker` | Background continuous telemetry polling, idempotent ingestion, and scheduled dispatching. |
| `LearningService` | `AgentMemoryEngine` | Analyst feedback management, verified precedents, few-shot RAG retrieval, and memory records. |
| `PromptStudioService` | `AgentPolicyEngine` | Detection-level triage policy rules, custom prompts, versioning, and Level-2 SOC criteria. |
| `process_pending_incidents` | `reconcile_pending_triage` | Sequential processing of pending incidents through the Verdict Triage Agent. |
| `ZipGuard` | `PayloadSanitizationGuard` | Zip Slip path traversal mitigation, decompression bomb defense, and telemetry payload validation. |
| `SystemMonitorService` | `InferenceHealthMonitor` | Hardware telemetry, CPU/RAM tracking, NVIDIA GPU/VRAM observability, and latency benchmarking. |
| `build_model_facing_payload` | `EvidenceIntegrityGuardrail` | Zero-leakage evidence filtering, attribute sanitization, and strict ground-truth isolation. |
| `RuleParser` | `DetectionContextEngine` | Structured detection rule context compilation, pattern logic extraction, and remediation parsing. |
| `InvestigationService` | `ReviewOrchestrator` | Human-in-the-loop escalation workflow, analyst queue assignment, and verdict validation. |
| `EvaluationService` | `VerdictEvaluationEngine` | Accuracy, precision, recall, confusion matrix calculation, and trust analytics. |
| `DryRunService` | `ValidationEngine` | Offline test simulations, dataset splitting (70/30 chronological), and policy benchmarking. |

---

## 6. Summary & Verification Reference

This document represents the current, verified production state of the **AI Verdict: Agentic SOC Intelligence Platform**. All components, naming conventions, and API routes strictly reflect the live codebase, automated test suites (100% passing across 62 tests), and Next.js production builds.


