# Phase 9 — System & Controlled Pilot Architecture

Phase 9 extends the existing AI Verdict platform without duplicating its triage engine, validation pipeline, investigation queue, or reporting framework.

---

## 1. High-Level Dual-Server + Pilot Architecture

```text
+-------------------------------------------------------------------------+
|                    SERVER 1 — APPLICATION & GOVERNANCE NODE             |
|  Nginx TLS Reverse Proxy -> Next.js UI (:3000) & FastAPI API (:8000)    |
|                                                                         |
|  [FortiSIEM Poller / Manual Ingest]                                     |
|           |                                                             |
|           v                                                             |
|  [PilotService Eligibility & Budget Check]                              |
|      | Mode = DISABLED -> Existing workflow untouched                   |
|      | Mode = SHADOW / ANALYST_ASSISTED                                 |
|      v                                                                  |
|  [DistributedLockManager] -> [VerdictTriageAgent]                       |
|      |   Policy Approval + Evidence Contract + Preflight                |
|      |   TokenBudgetService + RAG Precedents                            |
|      |   OpenAICompatibleProvider (LIVE forbids simulated fallback)     |
|      |   IndependentVerdictValidator + Guardrails + TrustEngine (<=6)   |
|      v                                                                  |
|  +---------------------------+      +-------------------------------+   |
|  | pilot_evaluations Table   |      | Authoritative Incident &      |   |
|  | (SHADOW/ASSISTED record,  |      | Investigation Tables          |   |
|  |  separate analyst review, |      | (Untouched in SHADOW mode;    |   |
|  |  supervisor verification) |      |  human remains final owner)   |   |
|  +---------------------------+      +-------------------------------+   |
|                                                                         |
|  PostgreSQL 16 (Alembic 008_soc_pilot) + Redis 7 + Celery Worker/Beat   |
+------------------------------------+------------------------------------+
                                     | Private VLAN (OpenAI /v1 HTTP(S))
                                     v
+-------------------------------------------------------------------------+
|                   SERVER 2 — DEDICATED LOCAL LLM GPU NODE               |
|  vLLM OpenAI-Compatible Endpoint (:8000 /v1/chat/completions, /health)  |
|  Offline in dev/CI -> Fail-closed SERVER2_OFFLINE / Auto-pause circuit  |
+-------------------------------------------------------------------------+
```

---

## 2. Phase 9 Structural Additions

- **Data Persistence (`backend/app/models/pilot.py`, `backend/alembic/versions/008_soc_pilot.py`)**
  - `pilot_configurations`: Singleton-active versioned pilot configuration (`DISABLED` default, `is_paused`, scope rules/archetypes/severities, budgets, concurrency, timeout, immutable `allow_external_writeback=False` and `allow_auto_incident_closure=False`).
  - `pilot_config_history`: Immutable snapshot table supporting deterministic version rollback (`POST /api/pilot/rollback`).
  - `pilot_evaluations`: Dedicated provenance store (`idempotency_key`, `execution_mode`, `source_type`, `proposed_verdict`, `validated_verdict`, `trust_score`, `policy_version_id`, `policy_digest`, `model_identifier`, `is_simulated`, token counts, latency, `evidence_snapshot_hash`, separate analyst feedback & independent supervisor verification fields).
- **Services**
  - `PilotService` (`backend/app/services/pilot_service.py`)
  - `HistoricalEligibilityService` (`backend/app/services/historical_eligibility_service.py`)
- **APIs**
  - `/api/pilot/*` (`backend/app/api/pilot.py`)
  - `/api/verdict-intelligence/eligibility-report` (`backend/app/api/verdict_intelligence.py`)
  - Extended `ai_assurance` & `action_type` on `/api/investigations/*` (`backend/app/api/investigations.py`)
- **Frontend UI**
  - `PilotControlAndDashboard.tsx` wired into `/verdict-intelligence` (`Dashboard F: SOC Pilot Control`).
  - `HistoricalEligibilityPanel.tsx` wired into `/verdict-intelligence` (`Dashboard G: Historical Data Eligibility`).
  - Extended `/human-review-queue` drawer (`AI Verdict Assurance & Provenance` + action buttons).
  - Compact live SOC Pilot status banner on `/agent-mission-control` and governance link in `/governance-access`.

