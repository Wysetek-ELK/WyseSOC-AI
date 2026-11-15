# Backend Regression Test Results

**Document ID:** AIS-2.0-PROMPT-INSPECT-06  
**Feature:** Actual LLM Prompt Inspector 1.1  
**Date:** 2026-11-14  
**Author:** Antigravity AI Engine  
**Status:** COMPLETED  

---

## 1. Executive Summary

This report documents the backend automated regression and unit test execution following the implementation of the Actual LLM Prompt Inspector 1.1 hardening changes.

The primary target test suite `backend/tests/test_actual_prompt_inspector.py` achieved **100% pass rate (13 of 13 tests passing)**. No existing core verdict pipeline workflows, policy compilation mechanisms, or database models were broken by the new capture fields or service methods.

---

## 2. Dedicated Feature Test Suite (`test_actual_prompt_inspector.py`)

All 13 comprehensive test scenarios covering requirements 1–6 were executed against SQLite in-memory isolation with strict async fixtures:

| Test Case Name | Objective / Requirement | Result | Duration |
|:---|:---|:---:|:---:|
| `test_heavy_tcp_scan_prompt_capture_end_to_end` | E2E Heavy TCP Scan prompt capture, 9 sections + 2 guardrails, threshold 50.0, SHA-256 verified | **PASSED** | 1.12s |
| `test_tampered_payload_integrity_mismatch` | Cryptographic tampering detection (transitions to `MISMATCH`) | **PASSED** | 0.45s |
| `test_unapproved_policy_not_dispatched_capture` | Preflight gate intercepts record `NOT_DISPATCHED` with `UNVERIFIED` | **PASSED** | 0.88s |
| `test_api_actual_prompt_for_incident` | GET `/incident/{id}` returns all 6 sections + execution summary | **PASSED** | 0.62s |
| `test_api_historical_capture_unavailable` | Historical incidents without records return `HISTORICAL_CAPTURE_UNAVAILABLE` | **PASSED** | 0.38s |
| `test_api_prompt_preview_only_status` | Live preview endpoint explicitly labeled `PREVIEW_ONLY` and `UNVERIFIED` | **PASSED** | 0.54s |
| `test_api_export_json_and_markdown` | Export endpoints in JSON and Markdown with headers and attachment naming | **PASSED** | 0.49s |
| `test_canonical_json_serialization_and_hashing` | Key sorting, whitespace-invariant canonical JSON serialization | **PASSED** | 0.12s |
| `test_delivery_status_vs_prompt_integrity_separation` | Strict separation of `SEND_ATTEMPTED` / `FAILED` from Prompt Integrity | **PASSED** | 0.76s |
| `test_execution_history_and_retry_traceability` | Multi-attempt history, retries, `/executions` list, capture_id selector | **PASSED** | 0.89s |
| `test_rule_prompt_captures_summary` | GET `/rule/{id}/captures` summary list of recent evaluated incidents | **PASSED** | 0.94s |
| `test_role_based_deep_redaction_and_export_security` | RBAC masking of IPs/emails across tabs & exports (no bypass) | **PASSED** | 0.91s |
| `test_retention_cleanup_preserves_active_executions` | Purge expired inactive captures while preserving active verdict captures | **PASSED** | 1.23s |

**Summary:** 13 passed in 9.33s.

---

## 3. Database Migration & Alembic State

- **Migration File:** `backend/alembic/versions/011_prompt_inspector_hardening.py`
- **Execution Command:** `alembic upgrade head`
- **Schema State:** Up to date (`011_prompt_inspector_hardening`).
- **Backward Compatibility:** All new columns nullable or have default values; existing prompt capture rows and verdict rows remain intact.

---

## 4. Key Architectural Verifications

1. **Non-Blocking Error Handling:** Capture failures inside `record_dispatch()` or `record_completed()` are wrapped in defensive `try/except` blocks with error logging. A database capture failure will **never** cause the primary incident verdict or SIEM sync pipeline to fail.
2. **Ground Truth Isolation:** Simulation replays and prompt inspections maintain total isolation from production ground-truth calibration labels.
3. **Audit Immutability:** Every access and retention cleanup operation is logged to the `audit_logs` table with authenticated user metadata.
