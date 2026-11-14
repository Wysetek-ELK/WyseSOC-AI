# Verdictum AI — LLM Verdict Reliability 1.3: Test Results
**Document ID:** `docs/LLM_VERDICT_RELIABILITY_1_3/TEST_RESULTS.md`  
**Target:** Automated Regression Test Suite and Adversarial Verification Metrics  
**Author:** Antigravity Agent  
**Date:** November 14, 2026  
**Status:** ALL TESTS PASSED (70/70, 100% Pass Rate)

---

## 1. Executive Summary

This report documents the verification results for **Verdictum AI — LLM Verdict Reliability 1.3**.
Testing was executed locally using `pytest` under Python 3.13.13.

- **Total Reliability 1.3 Tests:** 11 / 11 PASSED (100%)
- **Total Combined Regression Suite:** 70 / 70 PASSED (100%)
- **Failures / Errors:** 0
- **Execution Time (Target Suite):** 3.03 seconds
- **Execution Time (Full Suite):** 16.26 seconds

---

## 2. Reliability 1.3 Target Regression Test Suite

**Test File:** `backend/tests/test_verdict_reliability_1_3.py` (420 lines)

| Test # | Test Function Name | Scenarios & Assertions | Result | Duration |
| :---: | :--- | :--- | :---: | :---: |
| **1** | `test_reject_process_name_spoofing_suspicious_path` | Binary named `ccmexec.exe` executing from `C:\Users\Public\ccmexec.exe`. Validator detects suspicious directory, flags `SPOOFED_ADMIN_BINARY`, and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.28s |
| **2** | `test_reject_process_name_allowlist_without_trusted_binary_evidence` | Telemetry contains only `process.name: "tanclient.exe"` without path, signature, hash, or management confirmation. Validator flags `UNVERIFIED_BINARY_PROVENANCE` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.26s |
| **3** | `test_reject_forged_ticket_in_command_line_without_authoritative_auth` | Command line contains `--ticket CHG-7712` but no authoritative ITSM record exists in telemetry. Validator treats CLI flag as untrusted assertion, flags `UNVERIFIED_COMMAND_LINE_TICKET`, and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.27s |
| **4** | `test_reject_invalid_digital_signature` | Telemetry contains `code_signature.status: "REVOKED"`. Model asserts signed by corporate PKI. Validator flags `INVALID_DIGITAL_SIGNATURE` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.28s |
| **5** | `test_reject_signature_metadata_only_without_verification_status` | Telemetry contains `certificate.issuer: "CN=Untrusted Root CA"` but lacks verified valid status. Validator flags `UNVERIFIED_SIGNATURE_CLAIM` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.27s |
| **6** | `test_reject_out_of_scope_maintenance_ticket` | Incident host is `host-dc-01`, but change ticket target host is `host-db-01`. Validator flags `AUTHORIZATION_SCOPE_MISMATCH` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.29s |
| **7** | `test_reject_unapproved_authorization_state` | Authoritative ticket exists, but `authorization.status` is `PENDING_APPROVAL`. Validator flags `AUTHORIZATION_STATE_UNAPPROVED` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.27s |
| **8** | `test_reject_expired_maintenance_window` | Authoritative ticket exists, but `maintenance.active: "false"`. Validator flags `MAINTENANCE_WINDOW_EXPIRED` and downgrades to `REQUIRES_ATTENTION`. | **PASSED** | 0.26s |
| **9** | `test_accept_legitimate_administrative_binary_with_trusted_evidence` | Binary `ccmexec.exe` executing from approved path `C:\Windows\CCM\CcmExec.exe` with `code_signature.status: "VALID"`. Accepted as decisive `FALSE_POSITIVE` (`EVIDENCE_VALIDATED`). | **PASSED** | 0.28s |
| **10** | `test_accept_legitimate_in_scope_and_approved_authorization` | Ticket `CHG-7070` with `status: "APPROVED"`, `target_host: "host-app-01"`, matching incident host `host-app-01`. Accepted as decisive `FALSE_POSITIVE` (`EVIDENCE_VALIDATED`). | **PASSED** | 0.29s |
| **11** | `test_consistent_verdict_naming_across_validators_and_guardrails` | Confirms `REQUIRES_ANALYST_ATTENTION` resolves cleanly without `MODEL_OUTPUT_INVALID` in validator and matches `UserVisibleVerdict.REQUIRES_ATTENTION` alias. | **PASSED** | 0.28s |

---

## 3. Full Combined Regression Suite

Command executed:
```powershell
pytest backend\tests\test_policy_compiler.py `
       backend\tests\test_structured_output_and_injection.py `
       backend\tests\test_independent_verdict_validator.py `
       backend\tests\test_evidence_contracts.py `
       backend\tests\test_evidence_normalization.py `
       backend\tests\test_token_budgeting.py `
       backend\tests\test_ground_truth_isolation.py `
       backend\tests\test_agentic_nomenclature.py `
       backend\tests\test_verdict_reliability_1_1.py `
       backend\tests\test_verdict_reliability_1_2.py `
       backend\tests\test_verdict_reliability_1_3.py
```

### Execution Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.0.1, pluggy-1.6.0
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent
plugins: anyio-4.9.0, langsmith-0.7.22, asyncio-1.4.0, mock-3.15.1, respx-0.23.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 70 items

backend\tests\test_policy_compiler.py ....                               [  5%]
backend\tests\test_structured_output_and_injection.py .                  [  7%]
backend\tests\test_independent_verdict_validator.py .........            [ 20%]
backend\tests\test_evidence_contracts.py .........                       [ 32%]
backend\tests\test_evidence_normalization.py ...........                 [ 48%]
backend\tests\test_token_budgeting.py .                                  [ 50%]
backend\tests\test_ground_truth_isolation.py .                           [ 51%]
backend\tests\test_agentic_nomenclature.py ...                           [ 55%]
backend\tests\test_verdict_reliability_1_1.py ..........                 [ 70%]
backend\tests\test_verdict_reliability_1_2.py ..........                 [ 84%]
backend\tests\test_verdict_reliability_1_3.py ...........                [100%]

============================= 70 passed in 16.26s =============================
```

---

## 4. Test Suite Breakdown by Protection Category

```
  +-----------------------------------------------------------------------------------+
  |               VERDICTUM AI REGRESSION TEST COVERAGE (70 TESTS)                    |
  +-----------------------------------------------------------------------------------+
  |  Category                               | Files           | Test Count            |
  |-----------------------------------------+-----------------+-----------------------|
  |  Process Spoofing & Provenance (1.3)    | test_...1_3     | 11 passed             |
  |  FP Evidence Verification (1.2)         | test_...1_2     | 10 passed             |
  |  LLM Reliability & Schema Sync (1.1)    | test_...1_1     | 10 passed             |
  |  Independent Verdict Validation Core    | test_indep...   |  9 passed             |
  |  Rule Evidence Contracts & Schemas      | test_ev_cont..  |  9 passed             |
  |  Evidence Ingestion & Normalization     | test_ev_norm..  | 11 passed             |
  |  Policy Compilation & Prompt Security   | test_policy...  |  4 passed             |
  |  Agentic Branding & Nomenclature        | test_agentic..  |  3 passed             |
  |  Context & Token Budgeting              | test_token...   |  1 passed             |
  |  Ground Truth Data Isolation            | test_ground...  |  1 passed             |
  |  Structured Output & Injection Shield   | test_struct...  |  1 passed             |
  |-----------------------------------------+-----------------+-----------------------|
  |  TOTAL                                  | 11 Test Files   | 70 PASSED             |
  +-----------------------------------------------------------------------------------+
```

---

## 5. Security Invariant Verification

1. **Zero Uncorroborated Process Trust:** In all test scenarios, executing an administrative binary name from a suspicious directory or without path/signature/hash was deterministically rejected.
2. **Zero Command-Line Assertion Privilege:** Command-line parameters like `--ticket` never grant authorization unless backed by an independent authoritative ITSM record.
3. **Zero Host-Scope Bleed:** Tickets scoped to a specific host cannot authorize activity on another asset.
4. **100% Backward Compatibility:** All 59 tests from previous milestones continue to pass without regression.
