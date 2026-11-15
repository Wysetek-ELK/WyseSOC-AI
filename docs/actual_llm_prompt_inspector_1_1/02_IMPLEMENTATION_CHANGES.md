# Implementation Changes: Actual LLM Prompt Inspector 1.1

**Document ID:** AIS-2.0-PROMPT-INSPECT-02  
**Feature:** Actual LLM Prompt Inspector 1.1 Hardening  
**Date:** 2026-11-14  
**Author:** Antigravity AI Engine  
**Status:** COMPLETED & VERIFIED  

---

## 1. Scope of Changes

The Actual LLM Prompt Inspector 1.1 update hardens the capture pipeline at the provider boundary between Server 1 (Verdictum AI) and Server 2 (Local LLM Cortex), enforces canonical serialization, separates prompt integrity from execution delivery status, supports multiple execution attempts and retries, guarantees role-based data redaction across tabs and exports, and introduces configurable retention policies.

---

## 2. Backend & Database Schema Changes

### 2.1 Database Model: `ActualLLMPromptCapture`
**File:** `backend/app/models/actual_prompt_capture.py`

Enhanced the table `actual_llm_prompt_captures` with the following columns:
- `canonical_serialized_payload` (`Text`, nullable): Exact deterministic JSON string representation of outbound request.
- `payload_format` (`String(32)`, default `CANONICAL_JSON`): Explicit identifier for stored format.
- `policy_snapshot_hash` (`String(64)`, nullable): SHA-256 digest of the compiled policy instructions at compile time.
- `retry_count` (`Integer`, default `0`): Sequential zero-indexed retry count.
- `is_active_verdict_capture` (`Boolean`, default `True`): Distinguishes the authoritative active verdict capture from superseded retry attempts.
- `is_simulated` (`Boolean`, default `False`): Strict flag preventing simulated runs from masquerading as live Server 2 GPU dispatches.

### 2.2 Database Migration: Alembic Revision `011_prompt_inspector_hardening`
**File:** `backend/alembic/versions/011_prompt_inspector_hardening.py`

- Safely applies `ALTER TABLE actual_llm_prompt_captures ADD COLUMN` for all 6 new fields.
- Applied and verified via `alembic upgrade head`.

### 2.3 Configuration Settings
**File:** `backend/app/config.py`

Added:
- `PROMPT_CAPTURE_RETENTION_DAYS: int = 0`: Configurable retention period in days (default `0` = indefinite retention).
- `PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED: bool = False`: Automatic cleanup toggle.

---

## 3. Service Layer Enhancements

### 3.1 Prompt Capture Service: `ActualPromptCaptureService`
**File:** `backend/app/services/actual_prompt_capture_service.py`

- **Canonical Serialization & SHA-256 Hashing:**
  - Implemented `canonical_serialize(payload)`: compact whitespace-invariant, sorted key serialization (`separators=(",", ":")`, `sort_keys=True`).
  - Implemented `canonical_hash(payload)`: deterministic SHA-256 calculation.
- **Provider Boundary Capture:**
  - `record_dispatch()`: Captured at the HTTP client boundary right before dispatch to Server 2. Sets `dispatch_status="SEND_ATTEMPTED"`, `payload_format="CANONICAL_JSON"`.
  - `record_completed()`: Updates record with `dispatch_status="COMPLETED"`, response verdict, tokens, and latency.
  - `record_failed()`: Updates record with `dispatch_status="FAILED"`, records detailed error message, and retains attempted prompt payload without claiming delivery.
  - `record_non_dispatch()`: Intercepts preflight or policy gate failures (e.g. unapproved policy) and records `dispatch_status="NOT_DISPATCHED"`.
- **Integrity Verification:**
  - `verify_integrity()`: Separates delivery status (`COMPLETED`, `SEND_ATTEMPTED`, `FAILED`, `NOT_DISPATCHED`) from Prompt Integrity (`VERIFIED`, `MISMATCH`, `UNVERIFIED`). Validates payload hash, untrusted data boundary delimiters (`<UNTRUSTED_INCIDENT_DATA>`), and policy snapshot integrity.
- **Role-Based Deep Redaction:**
  - `apply_role_redaction()`: For SOC Analysts and Read-Only Viewers, applies regex masks to:
    - Passwords, tokens, API keys (`[REDACTED_SECRET]`)
    - RFC1918 Private IPv4 addresses (`[REDACTED_IP]`)
    - Email addresses (`[REDACTED_EMAIL]`)
    - Hostnames and server URLs (`[REDACTED_HOST]`)
    - Recursively redacts `raw_request_payload`, `user_message`, `compiled_system_prompt`, `generation_settings`, and `response_raw`.
    - Administrators retain unredacted access.
- **Retention Cleanup:**
  - `cleanup_expired_captures()`: Deletes captures older than `PROMPT_CAPTURE_RETENTION_DAYS` while strictly protecting all captures with `is_active_verdict_capture=True`. Emits `PROMPT_CAPTURE_RETENTION_CLEANUP` audit log.

### 3.2 Shared Verdict Pipeline Integration
**File:** `backend/app/services/verdict_pipeline.py`

- Integrated `policy_snapshot_hash` and `is_simulated` capture in `run_shared_verdict_pipeline`.
- Unified `intercept_reason` / `reason` handling during early gate exits.

---

## 4. API Endpoints

**File:** `backend/app/api/prompts.py`

| Method | Endpoint | Access Level | Description |
|:---|:---|:---|:---|
| `GET` | `/api/v1/prompts/actual-prompt/incident/{incident_id}` | Analyst / Admin | Retrieves actual prompt with all 6 sections. Supports `?capture_id=` and `?execution_id=` queries. |
| `GET` | `/api/v1/prompts/actual-prompt/incident/{incident_id}/executions` | Analyst / Admin | Lists all execution attempts and retries for an incident. |
| `GET` | `/api/v1/prompts/actual-prompt/rule/{rule_id}/captures` | Analyst / Admin | Lists recent captured incidents for a rule. |
| `GET` | `/api/v1/prompts/actual-prompt/rule/{rule_id}/preview` | Analyst / Admin | Generates live compiled prompt preview tagged `PREVIEW_ONLY` and `UNVERIFIED`. |
| `GET` | `/api/v1/prompts/actual-prompt/incident/{incident_id}/export` | Analyst / Admin | Exports prompt in JSON or Markdown with role redaction applied. |
| `POST` | `/api/v1/prompts/actual-prompt/retention/cleanup` | Admin Only (403 for others) | Triggers retention cleanup preserving active verdict records. |

---

## 5. Frontend Components

### 5.1 API Client: `frontend/src/lib/api.ts`
- Added TypeScript interfaces: `ExecutionHistoryItem`, `RuleCaptureSummaryItem`, `RetentionCleanupResponse`, and updated `ActualPromptResponse`.
- Added API helper methods:
  - `getActualPromptForIncident(incidentId, captureId?, executionId?)`
  - `getIncidentActualPromptExecutions(incidentId)`
  - `getRulePromptCaptures(ruleId, limit?)`
  - `getPromptPreviewForRule(ruleId, versionId?, incidentId?)`
  - `exportActualPrompt(incidentId, format)`

### 5.2 Inspector Modal: `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx`
- **Dual Mode Switch:** Seamless toggle between **Runtime Captures** and **Compiled Preview**.
- **Delivery Status vs. Integrity Status Badges:** Distinct badges for delivery (`COMPLETED`, `SEND_ATTEMPTED`, `FAILED`, `NOT_DISPATCHED`, `PREVIEW_ONLY`) and integrity (`VERIFIED`, `MISMATCH`, `UNVERIFIED`).
- **Execution Attempt History Selector:** Interactive selector strip displaying Run #1, Run #2 (Retry), etc., with active verdict indicators.
- **Recent Rule Captures Carousel:** Quick navigation bar showing recent real incidents evaluated under this rule.
- **Deep Redaction Indicator:** Clear indicator showing whether the view is role-redacted or unrestricted.
- **Export Menu:** 1-click download of JSON and Markdown reports with active RBAC masking.

### 5.3 Rule Details & Overview: `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`
- Added **View Actual LLM Prompt** button in Quick Actions Strip (Section 1).
- Added **Preview Compiled Prompt** button in Quick Actions Strip.

### 5.4 Studio Page & Routing: `frontend/src/app/agent-intelligence-studio/page.tsx`
- Mounted `<ActualPromptInspectorModal />` in both `viewMode === "table"` and `viewMode === "studio"` to eliminate DOM omission.
- Added prompt inspection buttons to Rule Directory table rows and header.
- Added prompt inspection buttons to Legacy 7-Tab action column.
- Added prompt inspection buttons to Simulation Results rows and simulation drilldown modal.

### 5.5 AI Triage Workbench: `frontend/src/app/ai-triage-workbench/[id]/page.tsx`
- Added **View Actual LLM Prompt** trigger in the authoritative AI Verdict banner.
