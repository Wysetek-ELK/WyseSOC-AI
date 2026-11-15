# Integrity and Execution Validation Report

**Document ID:** AIS-2.0-PROMPT-INSPECT-03  
**Feature:** Prompt Integrity Hardening & Execution Traceability  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`)  
**Date:** 2026-11-14  
**Author:** Antigravity AI Engine  
**Status:** VALIDATED & GREEN  

---

## 1. Executive Summary

A core objective of Actual LLM Prompt Inspector 1.1 is the strict mathematical and semantic separation of **Prompt Integrity** from **Execution Delivery Status**, and the prevention of false claims regarding Server 2 (Local LLM Cortex) receipt.

This document records the empirical validation of:
1. Canonical JSON representation and SHA-256 digest calculation.
2. Clear semantics for `PREPARED`, `SEND_ATTEMPTED`, `COMPLETED`, `FAILED`, and `NOT_DISPATCHED`.
3. Execution history and retry traceability across multiple provider attempts.
4. End-to-end pipeline validation with rule `Heavy TCP Host Scan On Fixed Port`.

---

## 2. Canonical JSON & SHA-256 Digest Verification

### 2.1 The Need for Canonical Representation
Standard JSON serialization produces non-deterministic byte sequences depending on dictionary key ordering, indentation, and space padding after colons and commas. Calculating hashes directly on uncanonicalized bytes results in false-positive mismatch errors whenever whitespace varies across environments.

### 2.2 Canonical JSON Specification
`ActualPromptCaptureService.canonical_serialize()` enforces:
```python
json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
```
- **Sorting:** All dictionary keys sorted lexicographically at every nesting level.
- **Separators:** Zero whitespace around commas (`,`) and colons (`:`).
- **Encoding:** Strict UTF-8 with ASCII escaping.

### 2.3 Empirical Validation
In `test_canonical_json_serialization_and_hashing`:
- Two payloads with identical semantic content but completely reversed key insertion orders and varying indentation produced identical SHA-256 digests.
- Any manual modification to the stored prompt payload (e.g., modifying system directives or injection of untrusted text) immediately causes `verify_integrity()` to transition from `VERIFIED` to `MISMATCH`.

---

## 3. Separation of Prompt Integrity from Delivery Status

Prior implementations frequently conflated whether a prompt payload was correctly recorded with whether the Local LLM actually processed it. The Inspector now strictly decouples these two concepts:

### 3.1 Delivery Status States
| Delivery Status | Definition | Meaning for Analysts |
|:---|:---|:---|
| `PREPARED` | Outbound request payload assembled in memory. | Not yet sent over the network. |
| `SEND_ATTEMPTED` | Dispatched to HTTP transport client towards Server 2. | In-flight or pending provider response. Does NOT prove Server 2 accepted it. |
| `COMPLETED` | HTTP 200 received from Server 2 with complete verdict. | Successfully evaluated by Local LLM. Response parsed. |
| `FAILED` | Network timeout, HTTP 5xx, or connection refused. | Request failed in transit. Prompt recorded for post-mortem debugging. |
| `NOT_DISPATCHED` | Intercepted by policy quality gate or unapproved rule. | Blocked by safety governance before reaching provider boundary. |
| `PREVIEW_ONLY` | Live simulated preview compiled on-the-fly. | Synthetic sample telemetry; not historical runtime execution. |

### 3.2 Prompt Integrity States
| Integrity Status | Definition | Criteria |
|:---|:---|:---|
| `VERIFIED` | Outbound payload matches canonical SHA-256 hash, boundary tags `<UNTRUSTED_INCIDENT_DATA>` present, approved policy snapshot verified. | High confidence in prompt authenticity and safety isolation. |
| `MISMATCH` | Cryptographic hash mismatch or missing instruction boundary delimiters detected. | Warning: Record has been altered or corrupted. |
| `UNVERIFIED` | Missing execution capture, early intercept, or preview-only compilation. | No claim of runtime cryptographic verification. |

> **Critical Safety Principle:** Prompt Integrity `VERIFIED` certifies that the prompt payload recorded is cryptographically authentic and compliant with safety delimiters. It does **NOT** imply that the Local LLM returned a correct or trustworthy verdict.

---

## 4. Execution History & Retry Traceability

When Server 2 encounters high GPU load, timeouts, or socket resets, the verdict pipeline initiates bounded retries. Previously, earlier attempts were overwritten.

### 4.1 Multi-Attempt Architecture
Each provider dispatch attempt creates an immutable `ActualLLMPromptCapture` record with:
- Unique `capture_id`
- Shared `execution_id` correlating all attempts for that incident verdict
- Explicit `attempt_number` (1, 2, ...) and `retry_count` (0, 1, ...)
- `is_active_verdict_capture`: `True` only for the decisive attempt that produced the active verdict

### 4.2 API & UI Verification
- Endpoint `GET /api/v1/prompts/actual-prompt/incident/{incident_id}/executions` returns all attempts in chronological sequence.
- The UI Inspector displays an **Execution Attempt Selector**:
  - `Run #1 (FAILED)` — Shows timeout error details and the exact payload that was attempted.
  - `Run #2 (COMPLETED - Active)` — Shows the successful retry that produced the verdict.

---

## 5. End-to-End Validation: Heavy TCP Host Scan On Fixed Port

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`)

### 5.1 Test Configuration
- **Rule ID:** `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`
- **Archetype:** `NETWORK_SCAN`
- **Detection Pattern:** `COUNT(DISTINCT destIpAddr) >= 50 AND destPort IS NOT NULL`
- **Policy Version Selected:** Version 2 (Status: `APPROVED`)
- **Incident Telemetry:** SMB Port 445 sweep from `192.0.2.105` across 65 unique destination hosts (Threshold: 50.0).

### 5.2 Verification Findings
1. **Policy Selection:** Pipeline verified active approved Version 2 without falling back to draft.
2. **Archetype Inclusion:** System prompt included all 9 core policy sections, plus Section 10 (Instruction Boundaries) and Section 11 (JSON Schema Contract).
3. **Detection Threshold:** SIEM rule threshold of 50.0 distinct hosts was preserved in Section 3.
4. **Telemetry Isolation:** User message contained `<UNTRUSTED_INCIDENT_DATA>` delimiters wrapping raw telemetry.
5. **Canonical SHA-256 Hash:** Match verified against `request_sha256`.
6. **Integrity Status:** `VERIFIED`.
7. **Delivery Status:** `COMPLETED`.
