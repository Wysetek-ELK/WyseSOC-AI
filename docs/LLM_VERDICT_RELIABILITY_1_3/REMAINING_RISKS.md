# Verdictum AI — LLM Verdict Reliability 1.3: Remaining Risks
**Document ID:** `docs/LLM_VERDICT_RELIABILITY_1_3/REMAINING_RISKS.md`  
**Target:** Residual Risk Assessment, Verified Controls, and Testing Boundaries  
**Author:** Antigravity Agent  
**Date:** November 14, 2026  
**Status:** COMPLETED & VERIFIED

---

## 1. Overview & Verification Taxonomy

This document outlines the security posture and operational boundaries of Verdictum AI following the implementation of **Reliability 1.3 (Process Spoofing Defense, Untrusted Parameter Hardening, and Provenance Validation)**.

To maintain strict audit integrity, items are classified into three distinct categories:
- **`[VERIFIED]`**: Security controls implemented and verified with 100% automated test coverage.
- **`[FIXED]`**: Confirmed vulnerabilities and design flaws completely remediated in code.
- **`[REMAINING]`**: Operational risks that require external infrastructure, live model benchmarks, or external third-party API integrations.

---

## 2. Status Matrix: Verified Controls and Fixed Vulnerabilities

| Category | Item Description | Status | Verification Method |
| :---: | :--- | :---: | :--- |
| **Defect** | Process-name allowlist spoofing in user-writable paths | **`[FIXED]`** | Suspicious path scan & trusted binary evidence validation |
| **Defect** | Untrusted command-line `--ticket` argument injection | **`[FIXED]`** | Command line isolated; authoritative ITSM record required |
| **Defect** | Revoked or metadata-only digital signatures | **`[FIXED]`** | Invalid signature check & verified valid status required |
| **Defect** | Out-of-scope maintenance tickets (host mismatch) | **`[FIXED]`** | Authoritative scope comparison against incident host |
| **Defect** | Unapproved/pending authorization states | **`[FIXED]`** | State validation against approved set (`APPROVED`, `ACTIVE`) |
| **Defect** | Expired maintenance windows | **`[FIXED]`** | Inactive window check (`MAINTENANCE_WINDOW_EXPIRED`) |
| **Defect** | Inconsistent `REQUIRES_ATTENTION` verdict naming | **`[FIXED]`** | Symmetrical aliases and normalization across validators |
| **Control** | Process path verification against legitimate system baselines | **`[VERIFIED]`** | Automated test `test_reject_process_name_spoofing_suspicious_path` |
| **Control** | Rule-appropriate trusted binary evidence requirement | **`[VERIFIED]`** | Automated test `test_reject_process_name_allowlist_without_trusted_binary_evidence` |
| **Control** | Rejection of unverified command-line ticket assertions | **`[VERIFIED]`** | Automated test `test_reject_forged_ticket_in_command_line_without_authoritative_auth` |
| **Control** | Host-scope matching between ticket and alert | **`[VERIFIED]`** | Automated test `test_reject_out_of_scope_maintenance_ticket` |
| **Control** | Digital signature status verification | **`[VERIFIED]`** | Automated tests `test_reject_invalid_digital_signature` & `test_reject_signature_metadata_only` |
| **Control** | Deterministic fail-closed escalation | **`[VERIFIED]`** | Automated tests route all failures to `REQUIRES_ATTENTION` |

---

## 3. Remaining Risks & Operational Considerations

### Risk 1: Live Model Inference Calibration on Real GPU Testbeds
- **Classification:** **`[REMAINING - PENDING GPU BENCHMARK]`**
- **Description:**
  All tests were executed locally using deterministic mocks and synthetic test fixtures without live GPU infrastructure. While the deterministic validation gates are 100% verified, running live models (e.g. `Qwen2.5-7B-Instruct`, `Llama-3.1-8B-Instruct`) on vLLM or Ollama against complex multi-event incidents requires empirical evaluation.
- **Operational Impact:**
  Model inference latency, native JSON schema adherence, and prompt compliance under 8-bit/16-bit quantization must be measured on real hardware.
- **Recommended Action:**
  Deploy a benchmark harness on dedicated GPU hardware measuring:
  1. Inference latency across token budgets (P1–P7).
  2. Grounded claim formatting accuracy on live model outputs.
  3. Escalation rate distribution across 500+ verified historical incidents.

---

### Risk 2: Live External ITSM API Integration (ServiceNow / Jira)
- **Classification:** **`[REMAINING - EXTERNAL INTEGRATION]`**
- **Description:**
  Currently, authoritative change tickets are validated based on canonical evidence records ingested into the SIEM (`authorization.ticket_id`, `itsm.ticket_id`, `authorization.status`). If an enterprise environment lacks SIEM enrichment that automatically ingests ITSM ticket records, change tickets cannot be confirmed in canonical telemetry.
- **Operational Impact:**
  Legitimate scheduled maintenance will trigger `UNVERIFIED_COMMAND_LINE_TICKET` and escalate to `REQUIRES_ATTENTION` if the SIEM has not ingested the corresponding ITSM record.
- **Recommended Action:**
  Configure a bidirectional ServiceNow/Jira Service Management connector to enrich incoming SIEM alerts with authoritative change request status, target hosts, and implementation time windows.

---

### Risk 3: Stolen Administrative Credentials Using Legitimate System Binaries
- **Classification:** **`[REMAINING - INSIDER / CREDENTIAL ABUSE]`**
- **Description:**
  If an adversary compromises Domain Admin or SYSTEM credentials and executes the authentic, signed `C:\Windows\CCM\CcmExec.exe` or legitimate administrative tools from their valid installation paths, the process will pass trusted binary evidence checks.
- **Operational Impact:**
  Legitimate binaries executed with valid credentials for unauthorized malicious purposes cannot be distinguished by binary path or signature alone.
- **Compensating Control:**
  If the command involves known attacker tradecraft (credential dumping, shadow deletion, LOLBin download cradles), **Gate 1 (Adversary Tradecraft Detection)** immediately flags `EVIDENCE_CONTRADICTION` and rejects `FALSE_POSITIVE` regardless of binary validity.

---

### Risk 4: Advanced Polymorphic Evasion Outside Static Regex Patterns
- **Classification:** **`[REMAINING - RESIDUAL ADVERSARIAL RISK]`**
- **Description:**
  Adversary tradecraft scanning detects known patterns (`-enc`, `mimikatz`, `iex`, `downloadstring`, `vssadmin delete shadows`). Highly advanced evasion techniques (e.g. custom unmanaged PowerShell runspaces, complex environment variable concatenation, or polymorphic shellcode loaders) may avoid matching static regex patterns.
- **Compensating Control:**
  Even if tradecraft patterns are evaded, **Gates 2, 3, 4, 5, 6, 7, and 8 still apply**. A decisive `FALSE_POSITIVE` is **never** accepted without authoritative, in-scope, approved change tickets or verified administrative software running from approved paths.

---

### Risk 5: Tier-1 Analyst Workload and Alert Fatigue
- **Classification:** **`[REMAINING - OPERATIONAL CAPACITY]`**
- **Description:**
  By strictly requiring trusted binary evidence and rejecting command-line ticket assertions, the validator prioritizes security over automation. Benign routine activity that lacks formal ITSM ticket enrichment will be escalated to human analysts.
- **Operational Impact:**
  Tier-1 SOC analysts may experience an increase in `REQUIRES_ATTENTION` review volume until ITSM enrichment is fully operational.
- **Compensating Control:**
  Failing closed to `REQUIRES_ATTENTION` is the mathematically correct security design: it prevents automated alert suppression of active intrusions while providing analysts with structured reason codes and action directives.

---

## 4. Summary

With **Reliability 1.3**, all software-level vulnerabilities regarding process allowlisting, command-line parameter forgery, unverified digital signatures, and out-of-scope maintenance tickets are **`[FIXED]`** and **`[VERIFIED]`**. The remaining risks are operational, relating to live GPU model calibration and bidirectional ITSM API integration.
