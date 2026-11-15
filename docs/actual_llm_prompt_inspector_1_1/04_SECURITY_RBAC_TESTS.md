# Security, RBAC & Redaction Validation Report

**Document ID:** AIS-2.0-PROMPT-INSPECT-04  
**Feature:** Role-Based Access Control, Redaction & Export Protection  
**Date:** 2026-11-14  
**Author:** Antigravity AI Engine  
**Status:** VALIDATED & COMPLIANT  

---

## 1. Executive Summary

Prompt payloads contain sensitive security telemetry, internal hostnames, private IP addresses, employee identifiers, and SOC investigative SOPs. Unrestricted exposure of raw LLM prompts poses serious confidentiality and reconnaissance risks.

The Actual LLM Prompt Inspector 1.1 enforces **Defense-in-Depth Security Controls**:
1. Role-Based Access Control (RBAC) across Administrator, SOC Analyst, and Read-Only Viewer roles.
2. Recursive Deep Redaction across all inspector modal tabs, raw JSON views, and API payloads.
3. Anti-Bypass Export Security: Redaction rules applied to JSON and Markdown downloads.
4. Comprehensive Audit Logging for every view and export transaction.
5. Zero Secret Storage: Credentials, API tokens, and authorization headers are never captured.

---

## 2. RBAC Permission Matrix

| Role | Incident-Level Prompt | Rule-Level Preview | Raw Unredacted Data | Export Prompts | Trigger Retention Cleanup |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Administrator** | Full Access | Full Access | Allowed | Unredacted | Allowed |
| **SOC Analyst** | Redacted | Full Access | Masked | Redacted | Denied (403) |
| **Read-Only Viewer** | Redacted | Full Access | Masked | Redacted | Denied (403) |
| **Unauthenticated** | Denied (401) | Denied (401) | Denied (401) | Denied (401) | Denied (401) |

---

## 3. Deep Redaction Engine

### 3.1 Masking Rules
`ActualPromptCaptureService.apply_role_redaction()` applies deterministic regular expression masking to all user-facing content when queried by non-administrators:

| Data Type | Detection Pattern | Replacement Mask |
|:---|:---|:---|
| **Passwords & API Keys** | `(?i)(password\|secret\|apikey\|token\|bearer)...` | `[REDACTED_SECRET]` |
| **RFC1918 & RFC5737 IPv4** | `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`, `192.0.2.x`, `198.51.100.x` | `[REDACTED_IP]` |
| **Email Addresses** | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | `[REDACTED_EMAIL]` |
| **Internal Endpoints** | `https?://(?:[a-zA-Z0-9_\-]+\.)+[a-zA-Z]{2,}...` | `http://[REDACTED_HOST]` |
| **Generation Settings** | `endpoint`, `api_base`, `host` | `//[REDACTED_HOST]:...` |

### 3.2 Recursive Scope
Redaction is not cosmetic UI masking. It is executed on the server before JSON serialization and sanitizes:
- `user_message` (telemetry string)
- `incident_payload` (formatted representation)
- `system_prompt` (compiled directives)
- `raw_request_payload["messages"]` (every role and content object)
- `technical_details["generation_settings"]` (model server endpoints)
- `response_raw` (model outputs containing sensitive extracted entities)

### 3.3 Anti-Bypass Export Protection
A critical security vulnerability in earlier prompt inspectors was that analysts could bypass on-screen masking by downloading the raw JSON or Markdown export.
In version 1.1:
- `GET /api/v1/prompts/actual-prompt/incident/{incident_id}/export?format=json`
- `GET /api/v1/prompts/actual-prompt/incident/{incident_id}/export?format=markdown`

Both endpoints run the active session user's credentials through `apply_role_redaction()`. If the user is a SOC Analyst or Viewer, the exported file contains the sanitized values (`[REDACTED_IP]`, `[REDACTED_EMAIL]`, `[REDACTED_HOST]`). Only authenticated Administrators receive unredacted export files.

---

## 4. Empirical Test Results

In `backend/tests/test_actual_prompt_inspector.py::test_role_based_deep_redaction_and_export_security`:
- **SOC Analyst Query:**
  - `data_analyst["is_redacted"] == True`
  - IP `192.0.2.105` replaced with `[REDACTED_IP]` (Pass)
  - Email `lead@soc.example` replaced with `[REDACTED_EMAIL]` (Pass)
  - Host `198.51.100.50` replaced with `[REDACTED_HOST]` (Pass)
- **SOC Analyst Export:**
  - Exported JSON contained `[REDACTED_IP]`, preventing export bypass (Pass)
- **Administrator Query:**
  - `data_admin["is_redacted"] == False`
  - Unmasked `192.0.2.105` and `lead@soc.example` delivered cleanly (Pass)
- **Retention Cleanup Gating:**
  - Analyst attempt to trigger cleanup received HTTP 403 Forbidden (Pass)
  - Administrator request executed cleanly (Pass)

---

## 5. Audit Logging Architecture

Every access to the Actual LLM Prompt Inspector generates an immutable record in `AuditLog`:
- **Action:** `VIEW_ACTUAL_LLM_PROMPT`
- **Resource Type:** `INCIDENT` / `RULE`
- **Resource ID:** `capture_id`
- **Metadata Captured:**
  - User ID and username
  - Role (`Administrator` vs `SOC Analyst`)
  - Redaction status (`is_redacted: True/False`)
  - Timestamp (UTC)
  - Target incident ID and rule ID
