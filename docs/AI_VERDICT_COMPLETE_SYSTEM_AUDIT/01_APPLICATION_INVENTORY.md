# AI Verdict — Complete System Audit: Application Inventory

> **Audit Report Reference:** `01_APPLICATION_INVENTORY.md`  
> **Classification:** Technical Inventory & Component Catalog  
> **Audited System:** AI Verdict (Agentic SOC Intelligence Platform)  
> **Repository Location:** `c:\Users\amit\OneDrive\Documents\SOC-AI-Agent`  
> **Working Tree State:** Clean (Zero uncommitted code changes)  

---

## 1. Repository Directory Structure

```text
SOC-AI-Agent/
├── .gitignore                          # Standard git ignore definitions
├── ai_verdict.db                       # Root SQLite development database (empty in root; active in backend/)
├── ARCHITECTURE.md                     # Legacy Phase 1 architecture reference
├── DATABASE_SCHEMA.md                  # Database schema design documentation
├── DEPLOYMENT.md                       # Ubuntu Server LTS bare-metal deployment guide
├── PHASE_PROGRESS.md                   # Phase deliverable tracking document
├── README.md                           # Project top-level documentation and quickstart
├── TEST_PLAN.md                        # Verification plan and automated test specifications
│
├── backend/                            # FastAPI REST API & Core Engine
│   ├── .env                            # Backend environment variable configurations
│   ├── alembic.ini                     # Alembic migration engine configuration
│   ├── requirements.txt                # Python backend package dependencies
│   ├── alembic/
│   │   ├── env.py                      # Alembic async migration environment
│   │   ├── script.py.mako              # Migration script template
│   │   └── versions/
│   │       ├── 001_initial_schema.py   # Migration 001: Phase 1 tables
│   │       ├── 002_phase2_investigation_and_learning.py # Migration 002: Phase 2 tables
│   │       └── 003_phase3_dryrun_and_evaluation.py      # Migration 003: Phase 3 tables
│   ├── app/
│   │   ├── cli.py                      # CLI tool (admin user creation, data import)
│   │   ├── config.py                   # Pydantic Settings & environment variable loader
│   │   ├── database.py                 # Async SQLAlchemy engine & session factory
│   │   ├── main.py                     # FastAPI application entry point & lifespan handler
│   │   ├── api/                        # REST API Routers
│   │   │   ├── audit.py                # Audit log inspection endpoints
│   │   │   ├── auth.py                 # User authentication & cookie sessions
│   │   │   ├── dashboard.py            # High-level SOC metrics & LLM status
│   │   │   ├── deps.py                 # Dependency injection & RBAC role guards
│   │   │   ├── dry_run.py              # Offline replay & simulation endpoints
│   │   │   ├── evaluations.py          # Mathematical evaluation & rule maturity endpoints
│   │   │   ├── fortisiem.py            # FortiSIEM live pulling & poller scheduler control
│   │   │   ├── imports.py              # ZIP/JSON telemetry ingestion endpoints
│   │   │   ├── incidents.py            # Incident explorer, detail, & on-demand AI verdict
│   │   │   ├── investigations.py       # Human review queue & Q&A investigations
│   │   │   ├── learning.py             # Knowledge base & precedent matching
│   │   │   ├── llm_config.py           # Server 2 runtime configuration & connectivity testing
│   │   │   ├── prompts.py              # Agent Intelligence Studio prompt governance
│   │   │   ├── rules.py                # SIEM detection rule registry & analytics
│   │   │   ├── system_monitor.py       # Dual-server hardware telemetry endpoints
│   │   │   ├── telemetry.py            # Global historical telemetry timeline
│   │   │   ├── tokens.py               # Bifurcated token consumption analytics
│   │   │   └── users.py                # Administrator user provisioning & role management
│   │   ├── models/                     # SQLAlchemy Relational Models
│   │   │   ├── audit.py                # AuditLog model
│   │   │   ├── dry_run.py              # DryRunConfig, DryRunJob, DryRunResult models
│   │   │   ├── import_job.py           # ImportJob model
│   │   │   ├── incident.py             # Incident, IncidentEvent, HistoricalGroundTruth models
│   │   │   ├── investigation.py        # Investigation, InvestigationQuestion, InvestigationEvidence
│   │   │   ├── learning.py             # LearningRecord model
│   │   │   ├── maturity.py             # RuleMaturityEvaluation model
│   │   │   ├── prompt.py               # RulePrompt, PromptVersion models
│   │   │   ├── rule.py                 # Rule model
│   │   │   ├── system_metric.py        # SystemServerSample model
│   │   │   ├── telemetry_timeline.py   # TelemetryTimelineRecord model
│   │   │   ├── token_usage.py          # TokenUsageRecord model
│   │   │   └── user.py                 # User model
│   │   ├── schemas/                    # Pydantic Request/Response DTOs
│   │   │   ├── audit.py
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── dry_run.py
│   │   │   ├── evaluation.py
│   │   │   ├── fortisiem.py
│   │   │   ├── import_job.py
│   │   │   ├── incident.py
│   │   │   ├── investigation.py
│   │   │   ├── learning.py
│   │   │   ├── llm_config.py
│   │   │   ├── prompt.py
│   │   │   └── rule.py
│   │   ├── services/                   # Business Logic & Integration Services
│   │   │   ├── agent_memory_engine.py  # Compatibility alias for learning_service
│   │   │   ├── agent_policy_engine.py  # Compatibility alias for prompt_studio_service
│   │   │   ├── ai_verdict_service.py   # VerdictTriageAgent (AI evaluation & backlog processing)
│   │   │   ├── audit_service.py        # Centralized audit logger
│   │   │   ├── dashboard_service.py    # Metric aggregation engine
│   │   │   ├── detection_context_engine.py # Compatibility alias for rule_parser
│   │   │   ├── dry_run_service.py      # ValidationEngine (replay execution & splitting)
│   │   │   ├── evaluation_service.py   # VerdictEvaluationEngine (metrics & confusion matrix)
│   │   │   ├── evidence_integrity_guardrail.py # Compatibility alias for model_payload_allowlist
│   │   │   ├── fortisiem_scheduler.py  # Background 180s continuous ingestion poller
│   │   │   ├── fortisiem_service.py    # FortiSIEM REST supervisor client & fixture loader
│   │   │   ├── incident_service.py     # Incident query, detail, and repair service
│   │   │   ├── inference_health_monitor.py # Compatibility alias for system_monitor_service
│   │   │   ├── ingestion_service.py    # ZIP/JSON archive ingestion & deduplication
│   │   │   ├── investigation_service.py# ReviewOrchestrator (analyst queue management)
│   │   │   ├── learning_service.py     # AgentMemoryEngine (knowledge base & precedent RAG)
│   │   │   ├── llm_config_service.py   # Dynamic Server 2 IP/port management
│   │   │   ├── maturity_service.py     # 5-tier rule automation state machine
│   │   │   ├── model_payload_allowlist.py # Ground-Truth Isolation filter
│   │   │   ├── prompt_studio_service.py# AgentPolicyEngine (template synthesis & versioning)
│   │   │   ├── review_orchestrator.py  # Compatibility alias for investigation_service
│   │   │   ├── rule_parser.py          # SIEM rule text parser
│   │   │   ├── sentinel_ingest_worker.py # Compatibility alias for fortisiem_scheduler
│   │   │   ├── system_monitor_service.py# InferenceHealthMonitor (hardware telemetry)
│   │   │   ├── telemetry_timeline_service.py # Telemetry timeline milestone tracker
│   │   │   ├── token_analytics_service.py # Input/Output token bifurcation analytics
│   │   │   ├── validation_engine.py    # Compatibility alias for dry_run_service
│   │   │   ├── verdict_evaluation_engine.py # Compatibility alias for evaluation_service
│   │   │   ├── verdict_triage_agent.py # Compatibility alias for ai_verdict_service
│   │   │   └── model_provider/         # Inference Provider Abstraction
│   │   │       ├── base.py             # BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict
│   │   │       ├── disabled.py         # DisabledModelProvider
│   │   │       ├── factory.py          # Provider factory (get_model_provider)
│   │   │       ├── openai_compatible.py# Client for vLLM/Ollama OpenAI endpoints
│   │   │       └── simulated.py        # Deterministic offline heuristic simulator
│   │   └── utils/
│   │       ├── payload_sanitization_guard.py # Compatibility alias for zip_guard
│   │       ├── security.py             # Password hashing (bcrypt) & JWT token utilities
│   │       └── zip_guard.py            # Zip Slip & decompression bomb defense
│   └── tests/                          # Automated Pytest Test Suite
│       ├── conftest.py                 # In-memory SQLite async test fixtures
│       ├── test_agentic_nomenclature.py
│       ├── test_api_endpoints.py
│       ├── test_auth.py
│       ├── test_dry_run_replay.py
│       ├── test_evaluation_metrics.py
│       ├── test_fortisiem_continuous_sync.py
│       ├── test_fortisiem_pull.py
│       ├── test_ground_truth_isolation.py
│       ├── test_ingestion.py
│       ├── test_investigations.py
│       ├── test_learning.py
│       ├── test_llm_config.py
│       ├── test_llm_offline_backlog.py
│       ├── test_model_provider.py
│       ├── test_prompt_studio.py
│       ├── test_rule_maturity.py
│       ├── test_rule_parser.py
│       ├── test_system_monitor.py
│       ├── test_telemetry_timeline_and_tokens.py
│       └── test_zip_guard.py
│
├── deployment/                         # Bare-Metal Linux Deployment Artifacts
│   ├── nginx/
│   │   └── ai-verdict.conf             # Nginx reverse proxy, SSL/TLS, gzip, headers
│   ├── scripts/
│   │   ├── backup_db.sh                # PostgreSQL database backup utility
│   │   ├── install_llm_server.sh       # AWS g4dn.2xlarge vLLM installation script
│   │   ├── install_ollama_llm.sh       # Ollama lightweight inference installation script
│   │   ├── install_ubuntu.sh           # Bare-metal Ubuntu setup for Server 1
│   │   ├── start_services.sh           # Systemd service startup wrapper
│   │   └── stop_services.sh            # Service shutdown wrapper
│   └── systemd/
│       ├── ai-verdict-backend.service  # Systemd service for FastAPI Uvicorn
│       └── ai-verdict-frontend.service # Systemd service for Next.js production server
│
├── docs/                               # System Documentation
│   ├── AGENT_INTELLIGENCE_STUDIO.md    # Specification for Agent Policy Engine
│   ├── ARCHITECTURE_AND_LOGIC.md       # Full architecture & logic taxonomy
│   ├── LOCAL_LLM_DRY_RUN_WORKFLOW.md   # Dry-run workflow specification
│   ├── Accuracy Optimization/
│   │   └── ACCURACY_ENGINEERING_GUIDE.md # Prompt & indicator optimization guide
│   └── Local LLM/
│       └── INSTALLATION_GUIDE.md       # Server 2 vLLM/Ollama setup manual
│
├── fixtures/                           # Real SIEM Ingestion Fixtures
│   └── Incident json.zip               # Real archive containing 20 incidents & 2 rules
│
└── frontend/                           # Next.js 16 Web Application
    ├── package.json                    # Frontend package dependencies & scripts
    ├── tsconfig.json                   # TypeScript configuration
    ├── next.config.ts                  # Next.js configuration
    ├── src/
    │   ├── context/
    │   │   └── AppContext.tsx          # Auth state, theme, blind review mode provider
    │   ├── lib/
    │   │   └── api.ts                  # Centralized REST API client (1,590 lines)
    │   ├── components/
    │   │   ├── common/PhasePlaceholder.tsx
    │   │   ├── layout/Header.tsx       # Top navigation, user status, blind review toggle
    │   │   ├── layout/Sidebar.tsx      # Grouped SOC navigation & dual-server badges
    │   │   ├── layout/Shell.tsx        # Responsive dashboard layout wrapper
    │   │   ├── system/ServerInfrastructureMonitor.tsx # Server 1 & Server 2 live telemetry widget
    │   │   └── telemetry/
    │   │       ├── HistoricalTelemetryTimeline.tsx   # Milestone timeline component
    │   │       └── TokenBifurcationWidget.tsx        # Prompt vs Completion token chart
    │   └── app/                        # Next.js App Router Pages
    │       ├── layout.tsx              # Root HTML wrapper with AppContext & Theme
    │       ├── globals.css             # Tailwind v4 utility styles
    │       ├── page.tsx                # Canonical: / (Agent Mission Control Dashboard)
    │       ├── login/page.tsx          # Authentication login screen
    │       ├── agent-mission-control/page.tsx # Alias -> page.tsx
    │       ├── ai-triage-workbench/
    │       │   ├── page.tsx            # Canonical: /ai-triage-workbench (Incident Explorer)
    │       │   └── [id]/page.tsx       # Canonical: /ai-triage-workbench/[id] (Incident Workbench)
    │       ├── incidents/
    │       │   ├── page.tsx            # Alias -> /ai-triage-workbench
    │       │   └── [id]/page.tsx       # Alias -> /ai-triage-workbench/[id]
    │       ├── telemetry-hub/page.tsx  # Canonical: /telemetry-hub (Data Ingestion Hub)
    │       ├── imports/page.tsx        # Alias -> /telemetry-hub
    │       ├── human-review-queue/page.tsx # Canonical: /human-review-queue (Analyst Queue)
    │       ├── analyst-attention/page.tsx  # Alias -> /human-review-queue
    │       ├── agent-intelligence-studio/page.tsx # Canonical: /agent-intelligence-studio
    │       ├── prompt-studio/page.tsx  # Alias -> /agent-intelligence-studio
    │       ├── detection-intelligence/
    │       │   ├── page.tsx            # Canonical: /detection-intelligence (Rules Registry)
    │       │   └── [id]/page.tsx       # Canonical: /detection-intelligence/[id] (Rule Detail)
    │       ├── rules/
    │       │   ├── page.tsx            # Alias -> /detection-intelligence
    │       │   └── [id]/page.tsx       # Alias -> /detection-intelligence/[id]
    │       ├── agent-memory/page.tsx   # Canonical: /agent-memory (Learning Records)
    │       ├── learning-history/page.tsx # Alias -> /agent-memory
    │       ├── agent-simulation-lab/page.tsx # Canonical: /agent-simulation-lab (Dry-Run Console)
    │       ├── dry-run/page.tsx        # Alias -> /agent-simulation-lab
    │       ├── verdict-intelligence/page.tsx # Canonical: /verdict-intelligence (Evaluation Dashboard)
    │       ├── evaluation-reports/page.tsx   # Alias -> /verdict-intelligence
    │       ├── inference-control/page.tsx # Canonical: /inference-control (Hardware Telemetry)
    │       ├── infrastructure/page.tsx # Alias -> /inference-control
    │       ├── agent-configuration/page.tsx # Canonical: /agent-configuration (Settings)
    │       ├── settings/page.tsx       # Alias -> /agent-configuration
    │       ├── governance-access/page.tsx # Canonical: /governance-access (User & RBAC Admin)
    │       └── admin/page.tsx          # Alias -> /governance-access
```

---

## 2. Technology Stack & Framework Inventory

### 2.1 Backend Platform (Server 1)

| Technology | Declared Version | Verified Runtime Version | Purpose | Source Evidence |
|---|---|---|---|---|
| **Python** | 3.11+ / 3.12+ | 3.13.13 | Primary backend runtime environment | System runtime |
| **FastAPI** | `>=0.110.0` | Installed | Async REST API routing and request validation | `backend/requirements.txt:1` |
| **Uvicorn** | `>=0.28.0` | Installed | ASGI web server hosting FastAPI | `backend/requirements.txt:2` |
| **Pydantic** | `>=2.6.0` | Installed | Data validation, type enforcement, schema parsing | `backend/requirements.txt:3` |
| **Pydantic Settings**| `>=2.2.0` | Installed | Centralized environment variable management | `backend/requirements.txt:5` |
| **SQLAlchemy** | `>=2.0.28` | Installed | Async ORM mapping and database abstraction | `backend/requirements.txt:6` |
| **Alembic** | `>=1.13.1` | Installed | Relational database schema migrations | `backend/requirements.txt:8` |
| **aiosqlite** | `>=0.20.0` | Installed | Async SQLite driver for local development & testing | `backend/requirements.txt:9` |
| **asyncpg** | `>=0.29.0` | Installed | Async PostgreSQL driver for production deployments | `backend/requirements.txt:10` |
| **bcrypt** | `>=4.1.2` | Installed | Secure password hashing (Blowfish cipher) | `backend/requirements.txt:12` |
| **PyJWT** | `>=2.8.0` | Installed | JSON Web Token encoding and signature verification | `backend/requirements.txt:13` |
| **HTTPX** | `>=0.27.0` | Installed | Async HTTP client for FortiSIEM & Server 2 calls | `backend/requirements.txt:17` |
| **psutil** | `>=5.9.0` | Installed | Hardware process and server telemetry polling | `backend/requirements.txt:19` |
| **Pytest** | `>=8.0.0` | Installed | Unit, integration, and security test runner | `backend/requirements.txt:15` |
| **Pytest-Asyncio** | `>=0.23.5` | Installed | Asynchronous test execution runner | `backend/requirements.txt:16` |

### 2.2 Frontend Platform (Server 1)

| Technology | Declared Version | Purpose | Source Evidence |
|---|---|---|---|
| **Next.js** | `16.4.5` | React application framework (App Router architecture) | `frontend/package.json:14` |
| **React** | `19.3.0` | Core UI component library | `frontend/package.json:15` |
| **React DOM** | `19.3.0` | Web DOM rendering for React 19 | `frontend/package.json:16` |
| **TypeScript** | `^5` | Strict static type definitions | `frontend/package.json:28` |
| **Tailwind CSS** | `^4` | Utility-first styling framework | `frontend/package.json:27` |
| **Lucide React** | `^1.69.0` | Cybersecurity and operational SOC iconography | `frontend/package.json:13` |
| **clsx / tailwind-merge** | `^2.1.1` / `^3.7.0` | Dynamic CSS class merging | `frontend/package.json:12,17` |

### 2.3 Local LLM Inference Node (Server 2)

| Technology | Deployment Type | Intended Configuration | Operational Role |
|---|---|---|---|
| **vLLM** | Native Linux Service | `:8000/v1` (OpenAI-compatible) | High-throughput GPU inference engine |
| **Qwen 2.5 7B Instruct AWQ**| 4-bit Quantized Weights | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Primary Level-2 SOC incident triage model |
| **Ollama** | Optional Alternative | `:11434/v1` (`qwen2.5:7b`) | Lightweight standalone local inference daemon |
| **NVIDIA CUDA / PyTorch**| System Driver / CUDA 12.x | AWS EC2 `g4dn.2xlarge` (T4 16GB) | GPU Tensor Core execution environment |

---

## 3. Application Entry Points

### 3.1 Backend Entry Points

1. **FastAPI Web Service (`backend/app/main.py`):**
   - Executed via: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Initializes FastAPI application instance with lifespan context manager.
   - Executes database schema initialization (`Base.metadata.create_all`) and dynamic raw DDL migrations.
   - Auto-creates default administrator account if users table is empty.
   - Launches `fortisiem_scheduler` continuous background polling loop if `FORTISIEM_AUTO_POLL_ENABLED=true`.
   - Registers CORS middleware and mounts 17 REST API routers under prefix `/api`.

2. **Command Line Interface (`backend/app/cli.py`):**
   - Executed via: `python -m app.cli [command]`
   - Subcommand `create-admin`: Seeds admin credentials (`username`, `email`, `password`, `full_name`).
   - Subcommand `import-data`: Ingests a local ZIP archive of SIEM incident JSONs and rule text files directly into the database.

### 3.2 Frontend Entry Points

1. **Next.js Root Layout (`frontend/src/app/layout.tsx`):**
   - Wraps entire application in HTML document structure.
   - Mounts `AppContextProvider` (`frontend/src/context/AppContext.tsx`) to supply global auth status, user role, theme preferences (dark/light), and Blind Review Mode toggle state.
   - Injects `Shell` layout component (`frontend/src/components/layout/Shell.tsx`) consisting of `Sidebar` and `Header`.

2. **Root Landing Route (`frontend/src/app/page.tsx`):**
   - Canonical URL: `/` (and `/agent-mission-control`).
   - Loads aggregate dashboard metrics from `GET /api/dashboard/metrics` and live hardware telemetry from `GET /api/system/servers/live`.

---

## 4. Architectural Nomenclature Mapping

To maintain backward compatibility while supporting modernized SOC terminology, the codebase implements systematic class and route aliasing:

| Documented Agentic Nomenclature | Concrete Source File Class / Module | Backward Compatibility Alias |
|---|---|---|
| `VerdictTriageAgent` | `backend/app/services/ai_verdict_service.py` | `AIVerdictService` |
| `SentinelIngestWorker` | `backend/app/services/fortisiem_scheduler.py` | `FortiSIEMSyncScheduler` |
| `AgentPolicyEngine` | `backend/app/services/prompt_studio_service.py` | `PromptStudioService` |
| `AgentMemoryEngine` | `backend/app/services/learning_service.py` | `LearningService` |
| `ValidationEngine` | `backend/app/services/dry_run_service.py` | `DryRunService` |
| `VerdictEvaluationEngine`| `backend/app/services/evaluation_service.py` | `EvaluationService` |
| `ReviewOrchestrator` | `backend/app/services/investigation_service.py`| `InvestigationService` |
| `DetectionContextEngine` | `backend/app/services/rule_parser.py` | `RuleParser` |
| `EvidenceIntegrityGuardrail`| `backend/app/services/model_payload_allowlist.py`| `build_model_facing_payload` |
| `PayloadSanitizationGuard`| `backend/app/utils/zip_guard.py` | `ZipGuard` |
| `InferenceHealthMonitor` | `backend/app/services/system_monitor_service.py` | `SystemMonitorService` |

---

## 5. Summary Inventory Assessment

The codebase contains:
- **17 REST API Routers** mounted under `/api` in `backend/app/api/`.
- **13 Relational Database Models** in `backend/app/models/`.
- **20 Business Service Modules** in `backend/app/services/`.
- **5 Inference Provider Modules** in `backend/app/services/model_provider/`.
- **21 Automated Test Modules** containing 62 test cases in `backend/tests/`.
- **14 Canonical Frontend Pages** and **11 Alias Routes** in `frontend/src/app/`.
- **8 Frontend Layout & Telemetry Components** in `frontend/src/components/`.
- **6 Production Deployment Scripts & Units** in `deployment/`.

