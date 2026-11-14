# Verdictum AI — Enterprise SOC Incident Analysis & Evidence-Grounded AI Platform

[![Phase](https://img.shields.io/badge/Phase-4%3A%20Production%20Hardening-emerald.svg)](#current-status)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2F%20SQLAlchemy%202.x-009688.svg)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015%2B%20%2F%20Tailwind-000000.svg)](https://nextjs.org)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20AsyncPG-336791.svg)](https://www.postgresql.org)
[![Queue](https://img.shields.io/badge/Task%20Queue-Celery%20%2F%20Redis%207-CC0000.svg)](https://docs.celeryq.dev)
[![Tests](https://img.shields.io/badge/Tests-166%20Passed%20(100%25)-brightgreen.svg)](#verification)

**Verdictum AI** is an enterprise-grade Security Operations Center (SOC) incident investigation, evidence grounding, and AI verdict platform designed for high-throughput enterprise environments processing up to 10,000+ daily SIEM incidents across 2,000+ detection rules.

---

## Current Status: Phase 4 Completed (Production Ready)

The complete five-phase engineering and governance program has been completed and empirically verified:
- **Phase 0: Audit Verification & Technical Baseline** (**COMPLETED**): Code audit of all 15 findings, baseline test establishment.
- **Phase 1: Critical Safety & Security Controls** (**COMPLETED**): Secrets validation (AV-014), unapproved policy gating (AV-002), simulated fallback ban in prod (AV-004), blind-review isolation (AV-003), learning governance (AV-009).
- **Phase 2: Evidence Grounding & Independent Verification Engine** (**COMPLETED**): Canonical evidence normalization (AV-011), machine-verifiable evidence contracts (AV-015), preflight gating (AV-016), independent factual claim grounding (AV-013).
- **Phase 3: Policy Framework, Semantic RAG & Model Optimization** (**COMPLETED**): Unified 9-section policy compilation (AV-017), live/simulation parity (AV-018), rule-specific verified semantic RAG (AV-019), deterministic token budgeting (AV-020), empirical calibration (AV-021).
- **Phase 4: Production Hardening, Scalability & Operational Readiness** (**COMPLETED**): Alembic migration hardening (AV-012), PostgreSQL connection pooling (AV-026), Celery/Redis task queues (AV-022), async simulation & cancellation (AV-023), GPU circuit breaking (AV-024), Prometheus observability (AV-025), audit HMAC (AV-027), non-Docker systemd deployment (AV-028).

---

## Strict Restrictions Compliance

1. **NO Docker / Docker Compose / Kubernetes**: Runs natively on bare metal / Ubuntu Server LTS via systemd and Nginx.
2. **NO Managed AI Services or External LLMs**: Zero external AI APIs (OpenAI, Anthropic, Gemini, Firebase, Supabase).
3. **NO Model Dependent Architecture**: Future local LLMs connect via provider-independent interfaces on a separate server (Server 2).
4. **NO SIEM Write-Back**: Read-only dry-run safety during Foundation.
5. **NO Mocked Verdicts Claimed as AI**: All metrics reflect actual database records.

---

## Architecture Overview (Two-Server Model)

- **Verdictum Core (`verdictum-core-01`) — Application Server (Server 1)**:
  - **Frontend**: Next.js 15+ App Router, TypeScript, Tailwind CSS, Dark SOC Theme.
  - **Backend**: Python 3.12/3.13 FastAPI REST API.
  - **Database**: PostgreSQL (production) with SQLAlchemy 2.x async ORM and Alembic migrations.
  - **Security**: Argon2id/Bcrypt password hashing, HttpOnly session cookies, role-based access control.
  - **Process Management**: Ubuntu systemd services & Nginx reverse proxy.
- **Verdictum Cortex (`verdictum-cortex-01`) — AI Inference Server (Server 2)**:
  - Dedicated GPU server (e.g. AWS `g4dn.2xlarge`) serving local quantized models (e.g., Qwen 2.5 7B AWQ) via private OpenAI-compatible API.
  - Hardened with concurrent GPU workload limiter and circuit breaker protection.
- **Verdictum Sentinel — AI SOC Investigation Copilot (`/soc-chatbot`)**:
  - Interactive conversational copilot powered by Verdictum Cortex for rapid incident investigation, MITRE ATT&CK mapping, and payload deobfuscation.

---

## Inspected Real SIEM Fixtures

Phase 1 was tested and verified using the provided `Incident json.zip` archive containing:
- **CrowdStrike Suspicious Activity** (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`): 10 incident JSONs, `Rule_info.txt`
- **Prisma SASE Suspicious File Threat Detection** (`Prisma_SASE_Suspicious_File_Threat_Detection_`): 10 incident JSONs, `Rule info.txt`

### Ground-Truth Separation Guarantee
Historical closure and resolution data (`resolution`, `clearedReason`, `comments`, `clearedUser`, `clearedTime`) are stored exclusively in the isolated `historical_ground_truth` table. An explicit allowlist `get_model_facing_payload()` guarantees 100% absence of closure or ground-truth leakage in future model inputs.

---

## Quickstart (Local Development)

### Prerequisites
- Python 3.12+
- Node.js 20+ / 22 LTS & npm

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run migrations and seed default administrator + real fixtures
python -m app.cli create-admin --username admin --email admin@verdictum-ai.internal --password "AdminPassword123!"
python -m app.cli import-data ../fixtures/Incident\ json.zip

# Start backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev -p 3000
```
Visit `http://localhost:3000` and sign in with `admin` / `AdminPassword123!`.

---

## Running the Automated Test Suite

```bash
cd backend
python -m pytest tests -v
```

All 18 automated tests pass 100%, covering:
- Authentication & RBAC permissions
- Password hashing & JWT validation
- Zip slip path traversal defense
- Decompression bomb defense
- SIEM rule text parser (CrowdStrike & Prisma)
- Zero-leakage ground-truth isolation
- Real fixture ZIP import (20 incidents, 2 rules)
- Duplicate incident detection
- Full REST API operations & Blind Review Mode

---

## Production Deployment (Ubuntu Server LTS)

Execute the non-interactive setup script on your Ubuntu server:
```bash
sudo bash deployment/scripts/install_ubuntu.sh
```

For manual deployment steps, systemd unit files, and Nginx reverse proxy configuration, consult [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md) — Complete Server 1 architecture, security boundaries, and data flow.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — PostgreSQL ER diagram, table schemas, and indexing strategy.
- [DEPLOYMENT.md](DEPLOYMENT.md) — Ubuntu Server LTS native deployment guide, systemd, Nginx, and backups.
- [TEST_PLAN.md](TEST_PLAN.md) — Phase 1 verification report and test specifications.
- [PHASE_PROGRESS.md](PHASE_PROGRESS.md) — Detailed tracking across Phase 1, Phase 2, and Phase 3 deliverables.

