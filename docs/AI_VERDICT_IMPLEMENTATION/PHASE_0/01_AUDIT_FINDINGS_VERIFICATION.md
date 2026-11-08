# 01. Audit Findings Verification (Task A)

## 1. Executive Summary

This report delivers the rigorous, line-by-line source-code verification of all 15 audit findings (**AV-001 through AV-015**) originally identified in the AI Verdict System Audit. Each finding was evaluated independently by inspecting the AST, control flow, error handling, and test fixtures in the codebase.

### Verification Summary
- **Total Findings Evaluated:** 15
- **CONFIRMED:** 15 (100%)
- **PARTIALLY_CONFIRMED:** 0 (0%)
- **NOT_REPRODUCED:** 0 (0%)
- **ALREADY_RESOLVED:** 0 (0%)
- **UNABLE_TO_VERIFY:** 0 (0%)

---

## 2. Detailed Findings Verification Register

### AV-001: Auto-Activation of Unapproved Heuristic Policy Drafts
- **Original Description:** Detection rule creation during ingestion automatically synthesizes a draft prompt and immediately marks it active without Administrator approval.
- **Severity in Original Audit:** **CRITICAL**
- **Actual Source-Code Behavior:**
  When an incident or rule is imported from FortiSIEM and no `RulePrompt` exists, the service synthesizes a draft prompt using heuristic archetypes and immediately assigns `rp.active_version_id = draft.id`.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ingestion_service.py#L724-L726`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ingestion_service.py#L724-L726)
  - [`backend/app/services/fortisiem_service.py#L233-L235`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L233-L235)
- **Affected Functions and Classes:**
  - `IngestionService.get_or_create_rule()`
  - `FortiSIEMService.sync_rules_from_fortisiem()`
- **Configuration Dependencies:** None (Unconditional execution on rule discovery).
- **Reachable in Production:** **YES.** Any incoming alert with an unrecognized rule automatically activates an unapproved policy in production.
- **Test Coverage:** Covered in [`backend/tests/test_fortisiem_pull.py#L180-L210`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_fortisiem_pull.py#L180-L210) (`test_fortisiem_cache_miss_auto_registers_rule`).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Decouple draft synthesis from activation. Set `rp.active_version_id = None` and require explicit approval via `POST /api/prompts/{id}/approve/{version_id}`.

---

### AV-002: Unapproved Draft Execution in Live Inference
- **Original Description:** If a rule prompt has no active version set, the triage service falls back to `rp.versions[0]`, executing unapproved draft policies in production.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  The active version lookup uses a fallback expression:
  ```python
  active_v = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])
  ```
  If `active_version_id` is `None`, version index 0 (which is always a `DRAFT`) is selected and evaluated in live triage.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ai_verdict_service.py#L133`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L133)
- **Affected Functions and Classes:**
  - `VerdictTriageAgent.analyze_incident()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** If a policy has its active version unset or deleted, unapproved drafts authored by analysts execute against production alerts.
- **Test Coverage:** Tested indirectly in [`test_prompt_studio.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_prompt_studio.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Replace fallback with an explicit check: if `active_version_id` is None, return `REQUIRES_ATTENTION` with reason `"POLICY_NOT_APPROVED"`.

---

### AV-003: Partial Assembly of 9-Section Policy Framework
- **Original Description:** Live triage prompt assembly omits sections 3, 8, and 9; dry-run simulations assemble only sections 1 and 2.
- **Severity in Original Audit:** **MEDIUM**
- **Actual Source-Code Behavior:**
  In `ai_verdict_service.py#L135-L146`, prompt assembly concatenates `common_prompt`, `rule_specific_prompt`, `tp_indicators`, `fp_indicators`, `required_evidence`, and `missing_info_criteria`. It completely drops `detection_conditions`, `escalation_conditions`, and `analyst_questions`. In `dry_run_service.py#L128,L138`, only `common_prompt` and `rule_specific_prompt` are assembled.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ai_verdict_service.py#L135-L146`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L135-L146)
  - [`backend/app/services/dry_run_service.py#L128,L138`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/dry_run_service.py#L128)
- **Affected Functions and Classes:**
  - `VerdictTriageAgent.analyze_incident()`
  - `DryRunService.execute_dry_run_job()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Analysts configure escalation conditions in the UI, but the model never receives them.
- **Test Coverage:** Verified in [`test_dry_run_replay.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_dry_run_replay.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 3) Build a centralized, shared prompt compiler that injects all 9 sections identically in live and simulation modes.

---

### AV-004: Silent Fallback to Heuristic Mock Simulator
- **Original Description:** Model inference errors or timeouts trigger a silent fallback to `SimulatedModelProvider`, outputting synthetic verdicts based on fixture keywords.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  `allow_mock = allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)`. Because `backend/.env` contains `LOCAL_LLM_ALLOW_MOCK_FALLBACK=true`, any HTTP connection failure, timeout, or 500 error from Server 2 silently invokes `SimulatedModelProvider`. This provider scans for keywords (`select2`, `adrum`, `70cb...`) and outputs 94-96% confident verdicts that are committed to the database.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ai_verdict_service.py#L189,L223-L235`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L189)
  - [`backend/app/llm/simulated.py#L40-L110`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/llm/simulated.py#L40-L110)
- **Affected Functions and Classes:**
  - `VerdictTriageAgent.analyze_incident()`
  - `SimulatedModelProvider.analyze_incident()`
- **Configuration Dependencies:** `settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK`.
- **Reachable in Production:** **YES.** Any GPU outage or network blip on Server 2 silently produces synthetic verdicts without operator awareness.
- **Test Coverage:** Covered in [`backend/tests/test_model_provider.py#L30-L50`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_model_provider.py#L30-L50).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Enforce `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false` in production. Fail loudly and return `REQUIRES_ATTENTION` with `error_type: "INFRASTRUCTURE_UNAVAILABLE"`.

---

### AV-005: Total Absence of Independent Deterministic Verification
- **Original Description:** Model output verdicts, confidence scores, and evidence items are accepted verbatim without independent verification against raw telemetry.
- **Severity in Original Audit:** **CRITICAL**
- **Actual Source-Code Behavior:**
  In `ai_verdict_service.py#L261-L285`, the parsed model response is directly mapped to the database record:
  ```python
  incident.ai_verdict = verdict.verdict
  incident.confidence = verdict.confidence
  incident.reasoning = verdict.reason
  ```
  There is zero secondary logic verifying whether items in `verdict.key_evidence` exist in raw events.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ai_verdict_service.py#L261-L285`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L261-L285)
- **Affected Functions and Classes:**
  - `VerdictTriageAgent.analyze_incident()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Hallucinated IPs, process names, or command flags are recorded as verified forensic truth.
- **Test Coverage:** Verified by absence of any validation assertions in [`test_agentic_nomenclature.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_agentic_nomenclature.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 2) Build a deterministic evidence validator that searches raw event logs for model-cited tokens before accepting verdicts.

---

### AV-006: Ground-Truth Leakage in Raw Payload During Blind Review
- **Original Description:** Blind Review mode suppresses `incident.ground_truth` but passes `raw_payload = inc.raw_payload` unredacted, exposing historical resolutions.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  In `incident_service.py#L188-L201`, `gt_resp` is set to `None` if `blind_review=True`. However, in line 229, `raw_payload=inc.raw_payload or {}` is returned without filtering. In FortiSIEM JSON, `clearedReason`, `resolution`, `comments`, and `clearedUser` reside directly in `raw_payload`.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/incident_service.py#L188-L201,L229`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/incident_service.py#L188-L201)
  - [`backend/app/api/incidents.py#L65-L91`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py#L65-L91)
- **Affected Functions and Classes:**
  - `IncidentService.get_incident_detail()`
  - `incidents.get_incident()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Analysts in blind review mode see historical closure data by viewing the Raw JSON tab.
- **Test Coverage:** Existing test `test_ground_truth_isolation.py` only tests the model allowlist filter, failing to test the `get_incident_detail` API endpoint in blind mode!
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Strip `FORBIDDEN_GROUND_TRUTH_KEYS` from `raw_payload` before serializing `IncidentDetailResponse` when `blind_review=True`.

---

### AV-007: Single-Record RAG Without Matching & Cross-Rule Precedent Injection
- **Original Description:** RAG retrieves the single newest verified feedback record by timestamp without similarity matching; if none exist for the rule, it injects arbitrary cross-rule records.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  `ai_verdict_service.py#L149-L168` queries `LearningRecord` where `rule_id == rule.id` ordered by `feedback_timestamp DESC` with `limit(1)`. If none is found, fallback query executes without `rule_id` filter (`where(LearningRecord.verification_status == "VERIFIED")`). Precedent explanation is sliced at 150 characters with no telemetry.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/ai_verdict_service.py#L149-L180`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L149-L180)
- **Affected Functions and Classes:**
  - `VerdictTriageAgent.analyze_incident()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** A web-attack alert receives an endpoint-detection precedent if the web rule lacks historical feedback.
- **Test Coverage:** Covered in [`test_learning.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_learning.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 3) Eliminate cross-rule fallback. Integrate `AgentMemoryEngine.find_similar_cases` to enforce IOC/semantic similarity within the same rule.

---

### AV-008: Immediate Few-Shot RAG Poisoning via Self-Verification
- **Original Description:** Analysts marking feedback as "independently verified" sets status immediately to `VERIFIED`, instantly promoting it into live few-shot prompts.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  In `investigation_service.py#L303-L343`, if `inv.is_independently_verified and not inv.is_disputed`, a `LearningRecord` is created with `verification_status="VERIFIED"`. Because live inference pulls the newest `VERIFIED` record by timestamp, that feedback immediately becomes the prompt precedent for all subsequent alerts.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/investigation_service.py#L303-L343`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/investigation_service.py#L303-L343)
- **Affected Functions and Classes:**
  - `InvestigationService.update_investigation_verdict()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** A junior analyst submitting an erroneous verdict with self-verification immediately corrupts AI triage behavior.
- **Test Coverage:** Covered in [`test_investigations.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_investigations.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Require explicit Administrator verification via `PUT /api/learning/{id}/verify` before any record transitions to `VERIFIED`.

---

### AV-009: Aggressive Telemetry Truncation in Model Allowlist Filter
- **Original Description:** Model allowlist slices telemetry to max 2 events, 8 attributes per event, and 180 characters per attribute.
- **Severity in Original Audit:** **MEDIUM**
- **Actual Source-Code Behavior:**
  In `model_payload_allowlist.py`, line 34 specifies `max_str_len: int = 180, max_keys: int = 8`. Line 96 specifies `for evt in events[:2]:`. Lines 143-158 truncate title to 200 chars and description/detail to 250 chars.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/model_payload_allowlist.py#L34,L96,L143-L158`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_payload_allowlist.py#L34)
- **Affected Functions and Classes:**
  - `sanitize_event_attributes()`
  - `build_model_facing_payload()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Long encoded PowerShell commands and multi-event lateral movement chains are truncated.
- **Test Coverage:** Tested in [`test_ground_truth_isolation.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_ground_truth_isolation.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 3) Implement dynamic token-budget packing rather than static slicing.

---

### AV-010: Hardcoded Simulated Server 2 Hardware Telemetry
- **Original Description:** If Prometheus `/metrics` is unreachable, Server 2 CPU (18.2%), RAM (28.5%), GPU (8.5%), and VRAM (5.8 GB) are returned as static constants.
- **Severity in Original Audit:** **MEDIUM**
- **Actual Source-Code Behavior:**
  In `system_monitor_service.py#L154-L157,L191-L197`, if `/metrics` fetch fails, hardcoded floats (CPU 18.2%, RAM 28.5%, GPU 8.5%, VRAM 5.8GB, Temp 54.0°C) are populated into the telemetry dictionary.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/system_monitor_service.py#L154-L157,L191-L197`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/system_monitor_service.py#L154-L157)
- **Affected Functions and Classes:**
  - `SystemMonitorService.get_server2_telemetry()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Operators see healthy green metrics when Server 2 is hung or running without Prometheus.
- **Test Coverage:** Tested in [`test_system_monitor.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_system_monitor.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Return `status: "DEGRADED"` with `None` values when real metrics cannot be collected.

---

### AV-011: Outbound Public IP Probing to Third-Party Services
- **Original Description:** System queries external IP discovery sites (`ipify.org`, `ifconfig.me`), violating air-gap isolation.
- **Severity in Original Audit:** **MEDIUM**
- **Actual Source-Code Behavior:**
  In `llm_config_service.py#L88-L92`, `get_server1_outbound_ip()` initiates HTTP GET requests to `api.ipify.org`, `ifconfig.me/ip`, and `icanhazip.com`.
- **Exact File Path and Line Numbers:**
  - [`backend/app/services/llm_config_service.py#L88-L105`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/llm_config_service.py#L88-L105)
- **Affected Functions and Classes:**
  - `LLMConfigService.get_server1_outbound_ip()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Visiting the LLM diagnostics page in an air-gapped network causes outbound requests and hangs.
- **Test Coverage:** Tested in [`test_llm_config.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_llm_config.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Remove public HTTP queries; resolve IP via local network interfaces (`socket.gethostbyname`).

---

### AV-012: Incomplete Alembic Migrations & Runtime Lifespan Raw DDL
- **Original Description:** Database tables and columns are created via raw SQL in `main.py` lifespan rather than tracked in Alembic migrations.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  In `main.py#L42-L53`, raw SQL executes `ALTER TABLE incidents ADD COLUMN ai_verdict JSON` and `ALTER TABLE dry_run_results ADD COLUMN prompt_tokens ...`. It also performs raw DDL for `system_server_samples`, `token_usage_records`, and `telemetry_timeline_records`.
- **Exact File Path and Line Numbers:**
  - [`backend/app/main.py#L40-L54,L104-L140`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/main.py#L40-L54)
- **Affected Functions and Classes:**
  - `lifespan()` in `main.py`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Standard migration tools (`alembic upgrade head`) leave the database in an incomplete state.
- **Test Coverage:** Tested in [`test_telemetry_timeline_and_tokens.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_telemetry_timeline_and_tokens.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 4) Generate an Alembic migration (`004_consolidate_schema.py`) and delete raw DDL statements from `main.py`.

---

### AV-013: Synchronous Replay Simulation in HTTP Request Handler
- **Original Description:** Dry-run simulations execute synchronously inside the FastAPI request handler without a task queue, risking 504 timeouts.
- **Severity in Original Audit:** **MEDIUM**
- **Actual Source-Code Behavior:**
  In `dry_run.py#L128-L131`, `execute_dry_run_job` is awaited directly inside `POST /api/dry-run/trigger`. Replaying 200 incidents holds the HTTP socket open for minutes.
- **Exact File Path and Line Numbers:**
  - [`backend/app/api/dry_run.py#L128-L131`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/dry_run.py#L128-L131)
- **Affected Functions and Classes:**
  - `trigger_dry_run_job()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Nginx drops connections after 60 seconds with `504 Gateway Time-out`.
- **Test Coverage:** Tested in [`test_dry_run_replay.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_dry_run_replay.py) with sample limit = 1.
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 4) Offload simulation jobs to Celery/Redis queue and return a job handle for async polling.

---

### AV-014: Hardcoded Fallback Secret Key & Plaintext Credential Persistence
- **Original Description:** Default fallback `SECRET_KEY` permits JWT forgery; SIEM credentials are written directly to `.env` in plaintext.
- **Severity in Original Audit:** **HIGH**
- **Actual Source-Code Behavior:**
  `config.py#L22` defaults `SECRET_KEY` to `"ai-verdict-super-secure-enterprise-secret-key-phase1-2026"`. `fortisiem_service.py#L1338-L1350` writes `FORTISIEM_PASSWORD` directly into `.env` in cleartext.
- **Exact File Path and Line Numbers:**
  - [`backend/app/config.py#L22`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/config.py#L22)
  - [`backend/app/services/fortisiem_service.py#L1338-L1350`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L1338-L1350)
- **Affected Functions and Classes:**
  - `Settings` in `config.py`
  - `FortiSIEMService.update_credentials()`
- **Configuration Dependencies:** `os.getenv("SECRET_KEY")`.
- **Reachable in Production:** **YES.** Anyone with repository access can forge admin tokens if `SECRET_KEY` is not set on the host. Cleartext passwords can be read by local users.
- **Test Coverage:** Tested in [`test_auth.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_auth.py).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Abort application startup if `SECRET_KEY` is unset. Disallow writing cleartext credentials to `.env`.

---

### AV-015: Detection Rule Ingestion Route Discrepancy
- **Original Description:** Endpoint implemented as `POST /api/fortisiem/sync-rules` while documentation specifies `POST /api/rules/sync/fortisiem`.
- **Severity in Original Audit:** **LOW**
- **Actual Source-Code Behavior:**
  In `fortisiem.py#L261`, the route is defined as `@router.post("/sync-rules")` under prefix `/api/fortisiem`. No sync route exists under `rules.py`.
- **Exact File Path and Line Numbers:**
  - [`backend/app/api/fortisiem.py#L261`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/fortisiem.py#L261)
- **Affected Functions and Classes:**
  - `sync_rules()`
- **Configuration Dependencies:** None.
- **Reachable in Production:** **YES.** Clients calling the documented `/api/rules/sync/fortisiem` receive HTTP 404.
- **Test Coverage:** Tested in [`test_fortisiem_pull.py#L155`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_fortisiem_pull.py#L155).
- **Verification Status:** **CONFIRMED**
- **Recommended Action:** (Phase 1) Add alias route in `rules.py` forwarding to `FortiSIEMService.sync_rules_from_fortisiem()`.

