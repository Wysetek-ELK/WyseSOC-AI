# Verdictum AI — LLM Verdict Reliability 1.3: Defects and Fixes
**Document ID:** `docs/LLM_VERDICT_RELIABILITY_1_3/DEFECTS_AND_FIXES.md`  
**Target:** Process Spoofing, Command-Line Parameter Abuse, and Authorization Integrity  
**Author:** Antigravity Agent  
**Date:** November 14, 2026  
**Status:** COMPLETED & VERIFIED

---

## 1. Overview

This document records the defects identified during the security audit of the False Positive (`FALSE_POSITIVE`) verification logic for **Verdictum AI — Reliability 1.3**, detailing the root causes, security risks, exact code fixes, and verification test cases.

---

## 2. Detailed Defects and Remediation

### Defect 1: Process-Name Allowlist Spoofing (Executable Name Blind Trust)
- **Locations:**
  - `backend/app/services/independent_verdict_validator.py:274–280`
  - `backend/app/services/verdict_guardrails_engine.py:182`
- **Root Cause:**
  In Reliability 1.2, if a process name matched any entry in `approved_management_binaries` (`ccmexec.exe`, `tanclient.exe`, `qualysagent.exe`, etc.), the validator set `has_grounded_authorization = True` without verifying the executable path, digital signature, or cryptographic hash.
- **Security Impact:**
  An attacker could rename a malicious payload (e.g. Cobalt Strike beacon or ransomware loader) to `ccmexec.exe` and execute it from `C:\Users\Public\ccmexec.exe` or `C:\Temp\ccmexec.exe`. The validator would treat the process as approved enterprise software and accept a `FALSE_POSITIVE` verdict.
- **Implemented Fix:**
  - Added detection of suspicious/user-writable directories (`\users\`, `\temp\`, `\tmp\`, `\appdata\`, `\downloads\`, `\perflogs\`, `/tmp/`, `/dev/shm/`). If an allowlisted binary executes from these paths, the validator flags `SPOOFED_ADMIN_BINARY` and rejects `FALSE_POSITIVE`.
  - Required rule-appropriate trusted binary evidence: approved installation directory (`\windows\ccm\`, `\program files\tanium\`, etc.), validated signature (`code_signature.status = "VALID"`), approved cryptographic hash, or active management agent confirmation. Lacking this evidence flags `UNVERIFIED_BINARY_PROVENANCE` and rejects decisive FP.
- **Verification:**
  - `backend/tests/test_verdict_reliability_1_3.py::test_reject_process_name_spoofing_suspicious_path`
  - `backend/tests/test_verdict_reliability_1_3.py::test_reject_process_name_allowlist_without_trusted_binary_evidence`

---

### Defect 2: Untrusted Command-Line Ticket Parameter Injection
- **Location:**
  - `backend/app/services/independent_verdict_validator.py:268–273`
- **Root Cause:**
  Previously, if `process.command_line` contained `--ticket`, `--scheduled`, `--maintenance`, or a ticket string, that command-line string was accepted as grounding affirmative authorization.
- **Security Impact:**
  Command-line arguments are untrusted process inputs directly controlled by the executing user or attacker. An adversary executing `powershell.exe -File script.ps1 --ticket CHG-7712` could fabricate a legitimate-looking change ticket flag to trick the validator into accepting an active attack as authorized maintenance.
- **Implemented Fix:**
  - Removed command-line ticket flags and parameters from being accepted as proof of authorization.
  - Enforced that ticket tokens cited by the model must exist in authoritative authorization fields (`authorization.ticket_id`, `itsm.ticket_id`, `policy.approved_baseline`).
  - If a ticket only exists as an argument inside `process.command_line` and has no corresponding authoritative ITSM record, the validator flags `UNVERIFIED_COMMAND_LINE_TICKET` and rejects `FALSE_POSITIVE`.
- **Verification:** `backend/tests/test_verdict_reliability_1_3.py::test_reject_forged_ticket_in_command_line_without_authoritative_auth`

---

### Defect 3: Acceptance of Invalid / Revoked Signatures and Metadata-Only Claims
- **Location:**
  - `backend/app/services/independent_verdict_validator.py:218–226`
- **Root Cause:**
  The validator checked `r.source_field in signature_fields`. If telemetry reported `code_signature.status: "REVOKED"` or `"INVALID"`, or if only `certificate.issuer: "CN=Untrusted"` was present, the check evaluated to `True`.
- **Security Impact:**
  Malware with revoked certificates, self-signed untrusted certificates, or failed signature checks was accepted as signed vendor software.
- **Implemented Fix:**
  - Added an invalid signature scan: if `code_signature.status` is in `{"invalid", "unsigned", "revoked", "expired", "failed", "untrusted", "malformed"}` or `signature.valid` is `False`, the validator flags `INVALID_DIGITAL_SIGNATURE` and immediately rejects `FALSE_POSITIVE`.
  - Required verified valid status: model claims asserting PKI or code-signing require `code_signature.status` in `{"valid", "trusted", "verified"}` or `signature.valid` is `True`. Certificate issuer metadata alone without valid status is rejected with `UNVERIFIED_SIGNATURE_CLAIM`.
- **Verification:**
  - `backend/tests/test_verdict_reliability_1_3.py::test_reject_invalid_digital_signature`
  - `backend/tests/test_verdict_reliability_1_3.py::test_reject_signature_metadata_only_without_verification_status`

---

### Defect 4: Out-of-Scope Authorization Tickets (Host Mismatch)
- **Location:**
  - `backend/app/services/independent_verdict_validator.py:350–360`
- **Root Cause:**
  When an authoritative change ticket was present, the system did not compare the ticket's designated target asset/host against the host where the alert was triggered.
- **Security Impact:**
  A legitimate, approved change ticket for a low-criticality database server (`host-db-01`) could be used to justify unauthorized administrative execution on an active directory domain controller (`host-dc-01`).
- **Implemented Fix:**
  - Extracted ticket scope targets from `authorization.target_host`, `authorization.hostname`, `authorization.scope`, `itsm.target_host`.
  - Compared against incident hostnames (`host.name`, `endpoint.hostname`, `source_host`).
  - If a mismatch is detected, the validator flags `AUTHORIZATION_SCOPE_MISMATCH`, rejects `FALSE_POSITIVE`, and routes the incident to Tier-1 analysts.
- **Verification:** `backend/tests/test_verdict_reliability_1_3.py::test_reject_out_of_scope_maintenance_ticket`

---

### Defect 5: Unapproved and Inactive Authorization States
- **Location:**
  - `backend/app/services/independent_verdict_validator.py:342–355`
- **Root Cause:**
  The validator did not inspect the approval state of authoritative tickets, accepting tickets whose status was `PENDING_APPROVAL`, `DRAFT`, `REJECTED`, or `CANCELLED`.
- **Security Impact:**
  An unauthorized administrator or attacker submitting a change request could execute commands while the ticket was still pending review or had been explicitly rejected, with the AI closing the alert as authorized.
- **Implemented Fix:**
  - Added approval state validation against `authorization.status`, `itsm.status`, `change_ticket.status`.
  - Explicitly rejected unapproved states (`draft`, `pending`, `pending_approval`, `rejected`, `denied`, `cancelled`, `revoked`). Flags `AUTHORIZATION_STATE_UNAPPROVED`.
- **Verification:** `backend/tests/test_verdict_reliability_1_3.py::test_reject_unapproved_authorization_state`

---

### Defect 6: Expired Maintenance Windows
- **Location:**
  - `backend/app/services/independent_verdict_validator.py:360–370`
- **Root Cause:**
  Maintenance window telemetry was checked only for field presence, failing to verify whether the window was currently active or expired.
- **Security Impact:**
  Attacks executed outside designated maintenance windows (e.g., hours or days after a window closed) were classified as authorized maintenance activity.
- **Implemented Fix:**
  - Scanned `maintenance.active`, `authorization.is_expired`, `authorization.window_active`.
  - If `maintenance.active` is `False` or `authorization.is_expired` is `True`, flags `MAINTENANCE_WINDOW_EXPIRED` and rejects `FALSE_POSITIVE`.
- **Verification:** `backend/tests/test_verdict_reliability_1_3.py::test_reject_expired_maintenance_window`

---

### Defect 7: Inconsistent REQUIRES_ATTENTION Verdict Naming Discrepancy
- **Locations:**
  - `backend/app/schemas/verdict_intelligence.py:31–45`
  - `backend/app/services/independent_verdict_validator.py:45–58`
  - `backend/app/services/verdict_guardrails_engine.py:53–60`
- **Root Cause:**
  `UserVisibleVerdict` defined `REQUIRES_ANALYST_ATTENTION` while `IndependentVerdictValidator` expected `REQUIRES_ATTENTION`. Passing `REQUIRES_ANALYST_ATTENTION` into `validate_verdict` triggered `MODEL_OUTPUT_INVALID` and forced a fallback state.
- **Security Impact:**
  Inter-service contract mismatch could drop legitimate analyst routing or result in inconsistent audit log entries.
- **Implemented Fix:**
  - Added `REQUIRES_ATTENTION = "REQUIRES_ANALYST_ATTENTION"` enum alias and `_missing_` classmethod in `UserVisibleVerdict`.
  - Normalized `clean_prop_verdict` in `IndependentVerdictValidator` to accept `REQUIRES_ANALYST_ATTENTION` without error.
  - Enhanced `VerdictGuardrailResult.__eq__` to equate both string variants symmetrically.
- **Verification:** `backend/tests/test_verdict_reliability_1_3.py::test_consistent_verdict_naming_across_validators_and_guardrails`

---

## 3. Summary of Remediations

| Defect # | Vulnerability | Remediation Gate | Status |
| :---: | :--- | :--- | :---: |
| **Defect 1** | Process name allowlist spoofing in user-writable paths | Suspicious path scan & trusted binary evidence requirement | **`[FIXED]`** |
| **Defect 2** | Untrusted command-line `--ticket` argument injection | Command lines isolated; authoritative ITSM record required | **`[FIXED]`** |
| **Defect 3** | Revoked or metadata-only digital signatures | Invalid signature scan & verified valid status requirement | **`[FIXED]`** |
| **Defect 4** | Out-of-scope maintenance tickets (host mismatch) | Authoritative scope comparison against incident host | **`[FIXED]`** |
| **Defect 5** | Unapproved/pending authorization states | Approval state validation (`AUTHORIZATION_STATE_UNAPPROVED`) | **`[FIXED]`** |
| **Defect 6** | Expired maintenance windows | Inactive window detection (`MAINTENANCE_WINDOW_EXPIRED`) | **`[FIXED]`** |
| **Defect 7** | Inconsistent `REQUIRES_ATTENTION` verdict naming | Symmetrical aliases and normalization across validators | **`[FIXED]`** |
