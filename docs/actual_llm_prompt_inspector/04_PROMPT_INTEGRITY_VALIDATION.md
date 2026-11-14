# 04 — Prompt Integrity Validation: Actual LLM Prompt Inspector

**Platform:** Verdictum AI — Agent Intelligence Studio 2.0  
**Feature:** View Actual LLM Prompt  
**Date:** November 14, 2026  
**Status:** Validated  

---

## 1. Multi-Point Prompt Integrity Architecture

A fundamental requirement of the Actual LLM Prompt Inspector is that **a valid request hash alone must not imply policy approval or verdict accuracy**. 

To deliver true provenance verification, the `ActualPromptCaptureService.verify_integrity` method executes a multi-point evaluation across four orthogonal dimensions:

```
+-----------------------------------------------------------------------------------+
|                           PROMPT INTEGRITY VERIFICATION                            |
+-----------------------------------------------------------------------------------+
|  1. Cryptographic Hash Validation                                                 |
|     SHA256(canonical_json(raw_request_payload)) == request_sha256                 |
|                                                                                   |
|  2. Policy Provenance & Approval Gating                                           |
|     policy_status == "APPROVED" AND policy_version_number >= 1                     |
|                                                                                   |
|  3. Untrusted Data Boundary Delimitation                                          |
|     "<UNTRUSTED_INCIDENT_DATA>" in user_message                                   |
|     "</UNTRUSTED_INCIDENT_DATA>" in user_message                                  |
|                                                                                   |
|  4. Incident Telemetry Correlation                                                |
|     incident.incident_id in user_message                                          |
|     source_ip in user_message (when present)                                      |
+-----------------------------------------------------------------------------------+
```

---

## 2. Integrity Status States

The evaluation outputs one of three mutually exclusive integrity states:

### 2.1 `VERIFIED`
- **Conditions:**
  - `hash_match == True`
  - `policy_approved == True`
  - `untrusted_data_boundaries_present == True`
  - `incident_match == True`
  - `dispatch_status in ("COMPLETED", "DISPATCHED")`
- **Meaning:** The captured request represents an unaltered outbound payload that complied with the approved policy governance and boundary isolation standards.
- **UI Presentation:** Green shield badge with `ShieldCheck` icon: `"Prompt Integrity: Verified"`.

### 2.2 `MISMATCH`
- **Conditions:**
  - `hash_match == False` (payload was modified in database after capture) **OR**
  - Prompt contains unapproved or tampered directives conflicting with governance records.
- **Meaning:** Cryptographic or structural divergence detected. The stored prompt cannot be trusted as the authoritative runtime payload.
- **UI Presentation:** Red pulsing alert badge with `ShieldAlert` icon: `"Prompt Integrity: Mismatch Detected"`.

### 2.3 `UNVERIFIED`
- **Conditions:**
  - `capture_status == "PREVIEW_ONLY"` **OR**
  - `capture_status == "HISTORICAL_CAPTURE_UNAVAILABLE"` **OR**
  - `dispatch_status == "NOT_DISPATCHED"` (request was intercepted by safety gates before dispatch) **OR**
  - Policy was in `DRAFT` status or archetype fallback without formal SOC Lead approval.
- **Meaning:** The prompt represents a preview, unapproved draft, or an execution that did not complete verified provider dispatch.
- **UI Presentation:** Slate/amber badge with `Shield` icon: `"Prompt Integrity: Unverified"`.

---

## 3. Test Cases for Integrity Verification

### Test 1: Bit-Level Tampering Detection (`test_tampered_payload_integrity_mismatch`)
- **Procedure:** A valid capture record is stored with `request_sha256 = ActualPromptCaptureService.canonical_hash(payload)`. The `raw_request_payload` is subsequently altered by replacing the system prompt with a simulated attacker directive `"tampered_override_directive"` without recalculating `request_sha256`.
- **Observed Result:**
  ```python
  status, details = ActualPromptCaptureService.verify_integrity(cap)
  assert status == "MISMATCH"
  assert details["hash_match"] is False
  ```
- **Outcome:** **PASSED.** Any retroactive modification to the captured payload immediately triggers `MISMATCH`.

### Test 2: Unapproved Policy Dispatch Intercept (`test_unapproved_policy_not_dispatched_capture`)
- **Procedure:** A production incident is processed against a rule with no approved policy version. The pipeline safety gate halts execution (`POLICY_NOT_APPROVED`).
- **Observed Result:**
  - Pipeline logs `early_exit = True`.
  - An immutable capture record is written with `dispatch_status = "NOT_DISPATCHED"`.
  - Integrity status is flagged as `UNVERIFIED`.
  - Explanation explicitly records: `"DISPATCH INTERCEPTED: Policy not approved for production use."`
- **Outcome:** **PASSED.** Unapproved policies are never falsely verified.

### Test 3: Heavy TCP Host Scan End-to-End Integrity (`test_heavy_tcp_scan_prompt_capture_end_to_end`)
- **Procedure:** Rule `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` is executed with approved Version 2 (`NETWORK_SCAN` archetype, FortiSIEM threshold: 50.0 distinct hosts).
- **Observed Result:**
  - Canonical hash matches outbound payload exactly.
  - Section 10 untrusted delimiters verified: `<UNTRUSTED_INCIDENT_DATA>`.
  - Status is evaluated as `VERIFIED`.
- **Outcome:** **PASSED.**

---

## 4. Summary Table

| Integrity Check | Evaluated Criterion | Failure State Result |
|---|---|---|
| Request Payload Hash | SHA-256 canonical digest equality | `MISMATCH` |
| Policy Status | Status must be `APPROVED` | `UNVERIFIED` |
| Untrusted Boundaries | `<UNTRUSTED_INCIDENT_DATA>` delimiters present | `MISMATCH` |
| Telemetry Matching | Incident ID & observed telemetry in user message | `MISMATCH` |
| Preview Exemption | Previews are never checked for historical hash | `UNVERIFIED` |
