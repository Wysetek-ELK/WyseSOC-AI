# 03 — API and Database Changes: Actual LLM Prompt Inspector

**Platform:** Verdictum AI — Agent Intelligence Studio 2.0  
**Feature:** View Actual LLM Prompt  
**Date:** November 14, 2026  
**Status:** Migrated & Tested  

---

## 1. Database Schema Additions

A new database table `actual_llm_prompt_captures` was created via Alembic migration `010_actual_llm_prompt_inspector.py`.

### Table Schema: `actual_llm_prompt_captures`

| Column | Type | Constraints / Nullable | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PRIMARY KEY | Unique UUID identifier for the capture record |
| `execution_id` | VARCHAR(64) | NOT NULL, INDEX | Verdict execution UUID linking attempts |
| `incident_id` | VARCHAR(64) | NOT NULL, INDEX | FortiSIEM incident identifier |
| `rule_id` | VARCHAR(64) | NOT NULL, INDEX | Rule UUID |
| `rule_name` | VARCHAR(255) | NOT NULL | Human-readable rule title |
| `policy_version_id` | VARCHAR(36) | NULLABLE | PromptVersion UUID active at execution |
| `policy_version_number` | INTEGER | NULLABLE | Version number (e.g. 2) |
| `policy_status` | VARCHAR(32) | NOT NULL (default "DRAFT") | Policy status (`APPROVED`, `DRAFT`, `ARCHIVED`) |
| `policy_source` | VARCHAR(64) | NOT NULL (default "DATABASE") | Source: `DATABASE_APPROVED`, `DATABASE_DRAFT`, `ARCHETYPE_TEMPLATE`, `FALLBACK` |
| `dispatch_status` | VARCHAR(32) | NOT NULL (default "PENDING") | State: `DISPATCHED`, `COMPLETED`, `FAILED`, `NOT_DISPATCHED`, `PREVIEW_ONLY` |
| `attempt_number` | INTEGER | NOT NULL (default 1) | Sequence attempt number for retries |
| `captured_at` | DATETIME | NOT NULL | UTC timestamp of capture |
| `model_name` | VARCHAR(128) | NOT NULL | LLM model identifier |
| `provider_type` | VARCHAR(64) | NOT NULL | `OPENAI_COMPATIBLE` or `SIMULATED` |
| `generation_settings` | JSON | NOT NULL | Temperature, max_tokens, timeout settings |
| `compiled_system_prompt` | TEXT | NOT NULL | Complete 11-section system instructions |
| `user_message` | TEXT | NOT NULL | Full user message containing `<UNTRUSTED_INCIDENT_DATA>` |
| `rag_precedents` | JSON | NOT NULL | Array of precedents included during inference |
| `has_rag_precedents` | BOOLEAN | NOT NULL (default FALSE) | Flag for presence of RAG examples |
| `evidence_requirements` | JSON | NOT NULL | Evidence contract requirements |
| `verdict_schema` | JSON | NOT NULL | JSON schema enforced on LLM output |
| `raw_request_payload` | JSON | NOT NULL | Full canonical outbound JSON payload |
| `request_sha256` | VARCHAR(64) | NOT NULL, INDEX | SHA-256 hash of canonical outbound payload |
| `response_raw` | TEXT | NULLABLE | Raw LLM response string |
| `response_verdict` | VARCHAR(64) | NULLABLE | Parsed verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, etc.) |
| `response_confidence` | FLOAT | NULLABLE | Confidence percentage (0-100) |
| `prompt_tokens` | INTEGER | NOT NULL (default 0) | Prompt token usage from provider |
| `completion_tokens` | INTEGER | NOT NULL (default 0) | Completion token usage from provider |
| `total_tokens` | INTEGER | NOT NULL (default 0) | Total token count |
| `latency_ms` | INTEGER | NOT NULL (default 0) | Roundtrip latency in milliseconds |
| `error_message` | TEXT | NULLABLE | Error message if dispatch failed |
| `prompt_integrity_status`| VARCHAR(32) | NOT NULL (default "UNVERIFIED") | Integrity assessment: `VERIFIED`, `MISMATCH`, `UNVERIFIED` |
| `integrity_details` | JSON | NOT NULL | Breakdown of individual integrity checks |
| `l1_explanation` | JSON | NOT NULL | Precomputed plain-language L1 summary card |

### Indices Created:
- `ix_prompt_captures_incident_id` on `(incident_id)`
- `ix_prompt_captures_execution_id` on `(execution_id)`
- `ix_prompt_captures_rule_id` on `(rule_id)`
- `ix_prompt_captures_sha256` on `(request_sha256)`
- `ix_prompt_captures_inc_time` composite index on `(incident_id, captured_at)`

---

## 2. API Endpoints Specification

### 2.1 Get Actual Prompt for Incident
- **URL:** `GET /api/v1/prompts/actual-prompt/incident/{incident_id}`
- **Permissions:** Authenticated User (`require_analyst` for redacted, `require_admin` for unredacted)
- **Audit Event:** Emits `VIEW_ACTUAL_LLM_PROMPT`
- **Behavior:**
  - Queries `actual_llm_prompt_captures` for the latest capture linked to `incident_id`.
  - Runs `ActualPromptCaptureService.verify_integrity(capture, rule, prompt_version)`.
  - If user is not Administrator, applies IP and secret masking via `apply_role_redaction`.
  - If no capture record exists (legacy incident), inspects `incident.ai_verdict`. If evaluated historically, returns `capture_status = "HISTORICAL_CAPTURE_UNAVAILABLE"`.
- **Response Model:** `ActualPromptResponse` (HTTP 200)

### 2.2 Get Prompt Preview for Rule
- **URL:** `GET /api/v1/prompts/actual-prompt/rule/{rule_id}/preview`
- **Query Params:**
  - `version_id` (optional): Specific policy version to preview
  - `incident_id` (optional): Sample incident telemetry to embed
- **Permissions:** Authenticated Analyst (`require_analyst`)
- **Behavior:**
  - Dynamically compiles the prompt for the specified rule and version.
  - Labels response explicitly with:
    - `capture_status = "PREVIEW_ONLY"`
    - `integrity_status = "UNVERIFIED"`
    - `banner_message = "PREVIEW ONLY: This is a live compiled prompt specification..."`
- **Response Model:** `ActualPromptResponse` (HTTP 200)

### 2.3 Export Actual Prompt
- **URL:** `GET /api/v1/prompts/actual-prompt/incident/{incident_id}/export?format={json|markdown}`
- **Permissions:** Authenticated Analyst (`require_analyst`)
- **Query Params:**
  - `format`: `"json"` or `"markdown"` (default `"json"`)
- **Behavior:**
  - Generates downloadable file stream.
  - For JSON: Exports canonical outbound request payload and metadata.
  - For Markdown: Exports structured audit dossier formatted with system instructions, user telemetry, and execution report.
  - Sets `Content-Disposition: attachment; filename="actual_prompt_{incident_id}.{ext}"`.

---

## 3. Migration Verification

```bash
cd backend
alembic upgrade head
```
**Verification Evidence:**
- Alembic applied revision `010_actual_llm_prompt_inspector` cleanly.
- Database table `actual_llm_prompt_captures` verified in SQLite development and staging schemas.
- Backward compatibility: Zero columns altered on `incidents`, `rules`, or `prompt_versions`.
