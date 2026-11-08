# AI Verdict — Phase 1: Implementation Changelog

**Target Release:** Phase 1 (Critical Safety & Security Controls)  
**Branch:** `feat/phase-1-safety-controls`  
**Modified Files:** 17 Files  
**New Files:** 2 Files (`backend/app/api/dev.py`, `backend/tests/test_phase1_security_controls.py`)  

---

### Detailed File Changes

#### 1. `backend/app/config.py`
- **Added `APP_ENV`:** Configured application environment mode (`development`, `testing`, `staging`, `production`) defaulting to `development`.
- **Added `KNOWN_INSECURE_SECRETS`:** Denylist of known insecure keys (e.g. `ai-verdict-super-secure-enterprise-secret-key-phase1-2026`, `changeme`, `secret`, `admin`).
- **Implemented `validate_security()`:** Automatically invoked on startup. In `production`/`prod`, strictly raises `RuntimeError` if `SECRET_KEY` is empty, fewer than 32 characters, or is present in `KNOWN_INSECURE_SECRETS`.
- **Added Network Configuration:** Added `SERVER1_HOST` and `SERVER1_OUTBOUND_IP` configuration attributes.
- **Default Hardening:** Set `LOCAL_LLM_ALLOW_MOCK_FALLBACK: bool = False` by default.

#### 2. `backend/app/services/fortisiem_service.py`
- **Removed Plaintext Writes to `.env`:** In `update_config()`, completely eliminated disk mutation and writing of `FORTISIEM_PASSWORD` and connection settings to the `.env` file. Settings are updated in-memory for the running session.
- **Support Flexible Input Structures:** Modified `update_config()` to accept either Pydantic models (`FortiSIEMConfigUpdate`) or keyword arguments, returning a `ConfigDict` allowing both dictionary and attribute-level access.
- **Eliminated Auto-Promotion:** In `sync_rules_from_fortisiem()`, removed the assignment `rp.active_version_id = draft.id`. Newly ingested rules remain strictly in `DRAFT` status pending SOC lead approval in Agent Intelligence Studio.
- **Added Module Logger:** Initialized standard Python logger (`logger = logging.getLogger(__name__)`).

#### 3. `backend/app/services/ingestion_service.py`
- **Eliminated Auto-Promotion on Incident Ingestion:** In `get_or_create_rule()`, removed `rp.active_version_id = draft.id`. Rule prompts generated from newly ingested event types remain in `DRAFT` with `active_version_id = None`.

#### 4. `backend/app/services/ai_verdict_service.py`
- **Local LLM Health Pre-Check:** Pre-checks Server 2 reachability via `is_local_llm_available()` ahead of prompt synthesis when mock fallback is disabled.
- **Production Zero-Mock Enforcement:** In `production`/`prod` mode, unconditionally forces `allow_mock = False`. If Server 2 is offline, immediately halts and raises `LocalLLMUnavailableError` (HTTP 503). Never produces heuristic TP or FP verdicts.
- **Policy Approval Enforcement in Live Triage:** Enforces that in live incident triage (`allow_simulated_fallback=False` or production), if no approved version exists (`candidate.status == "APPROVED"`), the engine strictly abstains with:
  - `verdict: "REQUIRES_ATTENTION"`
  - `validation_status: "POLICY_NOT_APPROVED"`
  - `confidence: 0.0`
  - `reason: "DETECTION_POLICY_PENDING_APPROVAL: No approved investigation policy exists for this detection rule. Triage deferred to human analyst."`
- **Simulation Lab Sandbox Testing:** Only when `allow_simulated_fallback=True` in non-production environments is draft testing permitted, enabling analysts to evaluate draft policies safely inside the Simulation Lab before promotion.
- **Cross-Rule Poisoning Elimination:** In Few-Shot RAG query, removed the `lr_fallback` block. Learning records are strictly scoped to the exact rule: `LearningRecord.rule_id == rule.id`.

#### 5. `backend/app/services/incident_service.py`
- **Defined `FORBIDDEN_GROUND_TRUTH_KEYS`:** Added comprehensive set of ground-truth field names (`ground_truth`, `analyst_verdict`, `target_verdict`, `true_verdict`, `actual_verdict`, `ground_truth_label`, `analyst_label`, `expected_verdict`, `historical_verdict`, `incident_ground_truth`).
- **Implemented `sanitize_blind_review_payload()`:** Recursive sanitizer that traverses nested dictionaries and lists, stripping any key in `FORBIDDEN_GROUND_TRUTH_KEYS` (case-insensitive and normalized).
- **Hardened `get_incident()`:** When `blind_review=True`:
  - Strips top-level `ground_truth` and `analyst_verdict`.
  - Recursively sanitizes `raw_payload`.
  - Recursively sanitizes `attributes` across all linked `IncidentEvent` records.

#### 6. `backend/app/models/learning.py`
- **Updated Default Status:** Set default `verification_status = "PENDING_REVIEW"` on `LearningRecord` model (replacing auto-verified state).

#### 7. `backend/app/schemas/learning.py`
- **Schema Alignment:** Set default `verification_status = "PENDING_REVIEW"` on `LearningRecordCreate`.
- **Added `LearningRecordVerifyRequest`:** Added schema containing `status: str` (`VERIFIED` or `REJECTED`) and optional `review_notes: Optional[str]`.

#### 8. `backend/app/services/investigation_service.py`
- **Feedback Governance:** In `submit_analyst_feedback()`, analyst submissions are created with `verification_status = "PENDING_REVIEW"` instead of immediate auto-approval.

#### 9. `backend/app/services/learning_service.py`
- **Supervisor Verification Method:** Added `update_verification_status(record_id, status, reviewer_username, review_notes)` to manage formal approval or rejection of analyst feedback.

#### 10. `backend/app/api/learning.py`
- **Added Verification Route:** Mounted `PUT /api/learning/records/{id}/verify` with `require_role(["Administrator"])` to enforce two-person integrity.
- **Production Guard on Seed Route:** Guarded `POST /api/learning/seed-historical` to return `403 Forbidden` if `settings.APP_ENV in ("production", "prod")`.

#### 11. `backend/app/services/system_monitor_service.py`
- **Honest Metric Reporting:** In `_sample_server_2()`, if Prometheus scraping fails, Server 2 CPU, RAM, disk, GPU utilization, GPU temperature, and VRAM are returned as `None`.
- **Flag Metric Availability:** Explicitly sets `details["metrics_available"] = False` without injecting hardcoded synthetic numbers (such as 34.5% or 45.0%).

#### 12. `frontend/src/components/system/ServerInfrastructureMonitor.tsx`
- **Honest UI Representation:** Updated GPU load and VRAM metric cards to display "Unavailable" and "Metrics Unavailable" badges when metrics are `null` or `metrics_available === false`.

#### 13. `backend/app/services/llm_config_service.py`
- **Egress Removal:** In `get_server1_outbound_ip()`, eliminated external HTTP queries to `api.ipify.org`, `ifconfig.me`, and `icanhazip.com`.
- **Local Resolution:** Resolves IP via `settings.SERVER1_OUTBOUND_IP`, `settings.SERVER1_HOST`, or local UDP socket inspection (`socket.SOCK_DGRAM` connection to RFC 5737 documentation prefix `192.0.2.1`).
- **Disk Protection:** In `update_config()`, prevented rewriting `.env` in production.

#### 14. `backend/app/api/rules.py`
- **Route Alias Added:** Added `@router.post("/sync/fortisiem")` alias ahead of dynamic route parameters (`/{identifier}`) to conform to documented specification.

#### 15. `backend/app/api/dev.py` & `backend/app/main.py`
- **Created Dev API Module:** Extracted development test endpoints (`POST /api/dev/reset-test-data`) into `backend/app/api/dev.py`.
- **Conditional Mounting:** In `main.py`, dev router is mounted strictly when `settings.APP_ENV not in ("production", "prod")`.

#### 16. `backend/tests/test_phase1_security_controls.py`
- **New Test Suite:** Created dedicated comprehensive test suite with 12 async test cases covering REQ-01 through REQ-08.

