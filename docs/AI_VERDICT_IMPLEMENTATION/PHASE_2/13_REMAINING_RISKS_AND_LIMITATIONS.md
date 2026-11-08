# AI VERDICT — PHASE 2: REMAINING RISKS & LIMITATIONS
## 13. REMAINING RISKS & ARCHITECTURAL LIMITATIONS

---

### 1. Context & Scope Clarification
Phase 2 successfully remediates **AV-005** by introducing canonical evidence normalization, machine-verifiable contracts, preflight gating, claim grounding, and deterministic independent verdict validation.

However, in accordance with the five-phase program design, several distinct architectural areas remain to be addressed in **Phase 3** (Prompt Compiler & Semantic RAG) and **Phase 4** (Production Infrastructure & Enterprise Scaling).

---

### 2. Known Limitations & Remaining Risks

#### Risk 1: Prompt Synthesis & Structure (Target: Phase 3)
- **Current State:** The prompt generation logic in `PromptStudioService` still relies on basic string concatenation of baseline SOC instructions and indicator bullet points.
- **Risk:** Models may occasionally misinterpret unstructured guidelines or produce formatting deviations in complex multi-event incidents.
- **Remediation in Phase 3:** Dedicated Prompt Compiler with strict JSON-schema enforcement and dynamic few-shot retrieval.

#### Risk 2: Few-Shot RAG Semantic Matching (Target: Phase 3)
- **Current State:** Verified learning precedents in `ai_verdict_service.py` are retrieved using exact rule ID matching (`LearningRecord.rule_id == rule.id`) limited to the latest record.
- **Risk:** Incidents with novel behavior under an existing rule or across sibling rules cannot leverage semantic vector similarity to retrieve relevant historical analyst rationales.
- **Remediation in Phase 3:** Semantic vector embeddings, pgvector / Qdrant retrieval, and confidence calibration curves.

#### Risk 3: Single-Threaded SQLite Development Engine (Target: Phase 4)
- **Current State:** Development and local testing utilize SQLite (`aiosqlite`).
- **Risk:** High concurrent write volume during heavy SIEM event ingest can encounter database locking.
- **Remediation in Phase 4:** Full PostgreSQL enterprise migration, connection pooling, and Alembic migrations.

#### Risk 4: In-Memory / Synchronous Task Execution (Target: Phase 4)
- **Current State:** Batch evaluations and background triage execute via asyncio tasks within the main FastAPI process.
- **Risk:** Process restarts during backlog processing can interrupt pending evaluations.
- **Remediation in Phase 4:** Celery / Redis distributed task queue with persistent worker heartbeats.

---

### 3. Risk Mitigation Summary Matrix

| Risk ID | Risk Description | Current Mitigation (Phase 2) | Permanent Target |
|---|---|---|---|
| **R-P2-01** | Prompt formatting inconsistency | Strict regex entity extraction fallback in `ModelClaimExtractor` | Phase 3 (Prompt Compiler) |
| **R-P2-02** | Simple few-shot selection | Strict single-rule isolation (AV-008 remediated in Phase 1) | Phase 3 (Semantic RAG) |
| **R-P2-03** | Database concurrency | Thread safety checks in session fixtures | Phase 4 (PostgreSQL) |
| **R-P2-04** | Synchronous worker queuing | Batch size limits and offline backlogging | Phase 4 (Celery/Redis) |

