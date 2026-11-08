# 18. Gaps, Risks, and Failure Modes Audit

## 1. Executive Summary

This report establishes the centralized **Findings Register** for the AI Verdict technical audit. Every finding documented herein has been verified through direct source-code inspection and test suite validation. 

Each finding follows a strict structured schema defining severity, status, source evidence, execution flow, operational impact, and non-destructive remediation recommendations.

---

## 2. Master Findings Register Summary

| Finding ID | Title | Severity | Status | Affected Subsystem |
| :--- | :--- | :---: | :---: | :--- |
| **AV-001** | Auto-Activation of Unapproved Heuristic Policy Drafts | **CRITICAL** | IMPLEMENTED | Agent Intelligence Studio / Ingestion |
| **AV-002** | Unapproved Draft Execution in Live Inference | **HIGH** | IMPLEMENTED | Decision Engine / Policy Governance |
| **AV-003** | Partial Assembly of 9-Section Policy Framework | **MEDIUM** | IMPLEMENTED | Decision Engine / Prompt Assembly |
| **AV-004** | Silent Fallback to Heuristic Mock Simulator | **HIGH** | IMPLEMENTED | Local LLM Inference / Decision Engine |
| **AV-005** | Total Absence of Independent Deterministic Verification | **CRITICAL** | MISSING | Decision Engine / Evidence Verification |
| **AV-006** | Ground-Truth Leakage in Raw Payload During Blind Review | **HIGH** | IMPLEMENTED | Incident Service / Investigation Console |
| **AV-007** | Single-Record RAG Without Matching & Cross-Rule Injection | **HIGH** | IMPLEMENTED | RAG / Memory Engine |
| **AV-008** | Immediate Few-Shot RAG Poisoning via Self-Verification | **HIGH** | IMPLEMENTED | Feedback Subsystem / RAG Memory |
| **AV-009** | Aggressive Telemetry Truncation in Model Allowlist | **MEDIUM** | IMPLEMENTED | Allowlist Filter / Threat Detection |
| **AV-010** | Hardcoded Simulated Server 2 Hardware Telemetry | **MEDIUM** | IMPLEMENTED | System Monitor Service |
| **AV-011** | Outbound Public IP Probing to Third-Party Services | **MEDIUM** | IMPLEMENTED | LLM Config Service / Network Egress |
| **AV-012** | Incomplete Alembic Migrations & Runtime Lifespan Raw DDL | **HIGH** | IMPLEMENTED | Database Layer / Migrations |
| **AV-013** | Synchronous Replay Simulation in HTTP Request Handler | **MEDIUM** | IMPLEMENTED | Dry-Run Engine / Scalability |
| **AV-014** | Hardcoded Fallback Secret Key & Plaintext Credential Persistence | **HIGH** | IMPLEMENTED | Security / Configuration |
| **AV-015** | Detection Rule Ingestion Route Discrepancy | **LOW** | IMPLEMENTED | API Router / Documentation |

---

## 3. Detailed Technical Findings

### AV-001: Auto-Activation of Unapproved Heuristic Policy Drafts
- **Severity:** **CRITICAL**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Ingestion Service / Agent Intelligence Studio
- **Source Evidence:** [`backend/app/services/ingestion_service.py#L724-L726`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ingestion_service.py#L724-L726) and [`fortisiem_service.py#L233-L235`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L233-L235)
- **Current Behavior:** When an incident or rule is imported and has no existing policy, the system generates a draft prompt and immediately assigns `rp.active_version_id = draft.id`.
- **Expected Behavior:** Synthesized templates should remain in `DRAFT` status. A rule prompt must not have an `active_version_id` until an Administrator explicitly approves it.
- **Impact:** Circumvents human governance. Unreviewed heuristic prompts immediately dictate production triage decisions.
- **Recommendation:** Decouple template synthesis from active pointer assignment. Require explicit administrative approval via `POST /api/prompts/{id}/approve/{version_id}`.
- **Dependencies:** `ingestion_service.py`, `fortisiem_service.py`, `prompt_studio_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-002: Unapproved Draft Execution in Live Inference
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** AI Verdict Decision Engine
- **Source Evidence:** [`backend/app/services/ai_verdict_service.py#L133`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L133)
- **Current Behavior:** If `active_version_id` is `None`, the triage engine selects `rp.versions[0]`.
- **Expected Behavior:** If no approved version exists, the decision engine should either abstain (`REQUIRES_ATTENTION`) or refuse triage until a policy is approved.
- **Impact:** In-progress drafts authored by junior analysts execute in live production triage.
- **Recommendation:** Replace `rp.versions[0]` fallback with an explicit check: if `active_version_id` is missing, raise a policy exception or output `REQUIRES_ATTENTION`.
- **Dependencies:** `ai_verdict_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-003: Partial Assembly of 9-Section Policy Framework
- **Severity:** **MEDIUM**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Decision Engine / Prompt Studio
- **Source Evidence:** [`backend/app/services/ai_verdict_service.py#L135-L146`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L135-L146) and [`dry_run_service.py#L128,L138`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/dry_run_service.py#L128)
- **Current Behavior:** Live prompt assembly concatenates sections 1, 2, 4, 5, 6, 7 and omits sections 3, 8, and 9. Dry-run simulations assemble only sections 1 and 2.
- **Expected Behavior:** All 9 sections defined in the policy framework should be injected into the prompt, and simulations must match live prompt assembly.
- **Impact:** Critical operational directives (escalation conditions, detection prerequisites) configured in the UI are ignored by the model.
- **Recommendation:** Refactor prompt assembly into a single shared utility consumed identically by live triage and dry-runs.
- **Dependencies:** `ai_verdict_service.py`, `dry_run_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-004: Silent Fallback to Heuristic Mock Simulator
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Inference Layer / Decision Engine
- **Source Evidence:** [`backend/app/services/ai_verdict_service.py#L189,L225-L235`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L189)
- **Current Behavior:** If the LLM call times out or errors, and `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true` (the default in `backend/.env`), the system silently invokes `SimulatedModelProvider`, outputting 94-96% confident verdicts using fixture keywords.
- **Expected Behavior:** Hardware or network failures should fail loudly, log alerts, and output `REQUIRES_ATTENTION` with an explicit infrastructure failure flag.
- **Impact:** Critical GPU node failures go undetected; operators believe real AI triage is occurring while hardcoded fixture heuristics make decisions.
- **Recommendation:** Enforce `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false` in production. Raise an alert on LLM failure rather than synthesizing fake verdicts.
- **Dependencies:** `config.py`, `ai_verdict_service.py`, `simulated.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-005: Total Absence of Independent Deterministic Verification
- **Severity:** **CRITICAL**
- **Status:** MISSING
- **Affected Subsystem:** AI Verdict Decision Engine
- **Source Evidence:** [`backend/app/services/ai_verdict_service.py#L261-L285`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L261-L285)
- **Current Behavior:** Model JSON outputs (`verdict`, `confidence`, `reasoning`, `key_evidence`) are saved verbatim to the database without verification against raw telemetry.
- **Expected Behavior:** An independent deterministic validation engine should verify that cited evidence exists in raw events before committing verdicts.
- **Impact:** AI hallucinations (e.g. fabricated IP addresses, nonexistent commands) are permanently recorded as objective evidence.
- **Recommendation:** Implement a deterministic evidence verification step that checks model assertions against raw telemetry before committing verdicts.
- **Dependencies:** `ai_verdict_service.py`, `incident_service.py`
- **Confidence:** 100% (Confirmed by absence of validation logic in code)

---

### AV-006: Ground-Truth Leakage in Raw Payload During Blind Review
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Incident Service / API Router
- **Source Evidence:** [`backend/app/services/incident_service.py#L188-L229`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/incident_service.py#L188-L229) and [`incidents.py#L65-L91`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py#L65-L91)
- **Current Behavior:** Blind Review suppresses top-level `ground_truth` but passes `raw_payload` unredacted, exposing historical resolution and comments.
- **Expected Behavior:** Blind Review mode must sanitize `raw_payload` to strip all historical resolution fields (`clearedReason`, `resolution`, `clearedUser`, `comments`).
- **Impact:** Human analyst audit objectivity is compromised; analysts can cheat blind reviews.
- **Recommendation:** Apply `model_payload_allowlist` sanitization to `raw_payload` before returning it in blind mode API responses.
- **Dependencies:** `incident_service.py`, `incidents.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-007: Single-Record RAG Without Matching & Cross-Rule Injection
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** RAG / Memory Subsystem
- **Source Evidence:** [`backend/app/services/ai_verdict_service.py#L149-L180`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L149-L180)
- **Current Behavior:** Selects the single most recent record by timestamp without similarity matching. If none match the rule, it falls back to any rule across the database and truncates notes to 150 characters without telemetry.
- **Expected Behavior:** RAG should use semantic or IOC similarity matching within the same rule, and never inject precedents from unrelated rules.
- **Impact:** Injects misleading, cross-domain precedents that degrade verdict quality.
- **Recommendation:** Integrate the existing `find_similar_cases` similarity matcher and strictly enforce rule-boundary isolation.
- **Dependencies:** `ai_verdict_service.py`, `learning_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-008: Immediate Few-Shot RAG Poisoning via Self-Verification
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Feedback Subsystem / Investigation Console
- **Source Evidence:** [`backend/app/services/investigation_service.py#L303-L355`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/investigation_service.py#L303-L355)
- **Current Behavior:** Checking "is independently verified" sets status immediately to `VERIFIED`, instantly promoting the feedback into the active few-shot prompt.
- **Expected Behavior:** All feedback should require secondary approval or supervisor verification before status becomes `VERIFIED`.
- **Impact:** A single analyst mistake immediately corrupts the few-shot guidance for all subsequent alerts.
- **Recommendation:** Require an Administrator or Tier 3 Lead to verify feedback via `PUT /api/learning/{id}/verify`.
- **Dependencies:** `investigation_service.py`, `learning_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-009: Aggressive Telemetry Truncation in Model Allowlist
- **Severity:** **MEDIUM**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Model Payload Filter
- **Source Evidence:** [`backend/app/llm/model_payload_allowlist.py#L34,L96,L143-L158`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/llm/model_payload_allowlist.py#L34)
- **Current Behavior:** Slices telemetry to max 2 events, 8 attributes per event, and truncates strings at 180 characters.
- **Expected Behavior:** Dynamic budget allocation accommodating long encoded commands and multi-stage event chains.
- **Impact:** Encoded PowerShell commands and multi-hop lateral movement events are truncated, blinding the LLM.
- **Recommendation:** Implement dynamic token-aware budget packing rather than static slicing.
- **Dependencies:** `model_payload_allowlist.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-010: Hardcoded Simulated Server 2 Hardware Telemetry
- **Severity:** **MEDIUM**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** System Monitor Service
- **Source Evidence:** [`backend/app/services/system_monitor_service.py#L153-L200`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/system_monitor_service.py#L153-L200)
- **Current Behavior:** If Prometheus `/metrics` is unreachable, Server 2 CPU (18.2%), RAM (28.5%), GPU (8.5%), and VRAM (5.8 GB) are returned as static constants.
- **Expected Behavior:** Return explicit `UNAVAILABLE` or error status when telemetry cannot be gathered.
- **Impact:** Operators see healthy green GPU metrics on the dashboard when the GPU node is frozen or offline.
- **Recommendation:** Return `status: "OFFLINE"` with null values on telemetry failure.
- **Dependencies:** `system_monitor_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-011: Outbound Public IP Probing to Third-Party Services
- **Severity:** **MEDIUM**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** LLM Config Service
- **Source Evidence:** [`backend/app/services/llm_config_service.py#L89-L92`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/llm_config_service.py#L89-L92)
- **Current Behavior:** Queries `api.ipify.org`, `ifconfig.me/ip`, and `icanhazip.com` to discover external IP.
- **Expected Behavior:** Determine IP locally from network interfaces or configuration settings.
- **Impact:** Violates air-gap isolation and causes network timeouts in firewalled environments.
- **Recommendation:** Remove external HTTP probes; use local socket binding (`socket.gethostbyname`).
- **Dependencies:** `llm_config_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-012: Incomplete Alembic Migrations & Runtime Lifespan Raw DDL
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Database Layer / Lifespan
- **Source Evidence:** [`backend/app/main.py#L42-L135`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/main.py#L42-L135)
- **Current Behavior:** Lifespan executes raw SQL `CREATE TABLE` and `ALTER TABLE` commands.
- **Expected Behavior:** All schema definitions and migrations must be managed exclusively through Alembic version scripts.
- **Impact:** Schema drift between migration files and actual database state.
- **Recommendation:** Generate an Alembic migration (`004_consolidate_schema.py`) and remove raw DDL from `main.py`.
- **Dependencies:** `main.py`, `alembic/versions/`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-013: Synchronous Replay Simulation in HTTP Request Handler
- **Severity:** **MEDIUM**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Dry-Run Router / Scalability
- **Source Evidence:** [`backend/app/api/dry_run.py#L128-L133`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/dry_run.py#L128-L133)
- **Current Behavior:** Runs the simulation loop directly inside the FastAPI request handler without a task queue.
- **Expected Behavior:** Offload simulation execution to a background worker queue (Celery/ARQ).
- **Impact:** Client HTTP timeouts (504 Gateway Time-out) and GPU starvation during large simulations.
- **Recommendation:** Queue dry-run jobs and return a `job_id` for polling.
- **Dependencies:** `dry_run.py`, `dry_run_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-014: Hardcoded Fallback Secret Key & Plaintext Credential Persistence
- **Severity:** **HIGH**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** Security / Configuration
- **Source Evidence:** [`backend/app/config.py#L22`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/config.py#L22) and [`fortisiem_service.py#L1338-L1350`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L1338-L1350)
- **Current Behavior:** Default `SECRET_KEY` fallback allows JWT forgery; SIEM credentials are written directly to `.env` in plaintext.
- **Expected Behavior:** Application should fail to start if `SECRET_KEY` is not set; secrets must be encrypted at rest or stored in a secrets vault.
- **Impact:** Administrative token forgery and credential theft from compromised filesystem.
- **Recommendation:** Remove hardcoded fallback; enforce non-empty secret key at startup. Store credentials in an encrypted vault.
- **Dependencies:** `config.py`, `fortisiem_service.py`
- **Confidence:** 100% (Confirmed in source code)

---

### AV-015: Detection Rule Ingestion Route Discrepancy
- **Severity:** **LOW**
- **Status:** IMPLEMENTED
- **Affected Subsystem:** API Routing / Documentation
- **Source Evidence:** [`backend/app/api/fortisiem.py#L115`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/fortisiem.py#L115) vs documentation
- **Current Behavior:** Endpoint implemented as `POST /api/fortisiem/sync-rules`, while documentation specifies `POST /api/rules/sync/fortisiem`.
- **Expected Behavior:** API routes and technical documentation should match.
- **Impact:** Developer and integration confusion.
- **Recommendation:** Add an alias route or update API documentation.
- **Dependencies:** `rules.py`, `fortisiem.py`
- **Confidence:** 100% (Confirmed in source code)

