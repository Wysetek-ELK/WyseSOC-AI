# AIS 2.4b — Verdict Grounding & Validator Integrity

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `04_VERDICT_GROUNDING_AND_VALIDATOR_INTEGRITY.md`  
**Phase:** AIS 2.4b (Real GPU Acceptance, Runtime Integrity & Evidence-Based Verdict Validation)  
**Date:** November 23, 2026  
**Status:** REFINED, HARDENED & TESTED  

---

## 1. Executive Summary

Stage 4 of AIS 2.4b performs a comprehensive overhaul and hardening of `IndependentVerdictValidator.py`, specifically addressing affirmative `TRUE_POSITIVE` criteria, dual-use tool handling, benign administrative context refutation, and the elimination of overfitted heuristics.

### Critical Invariants Preserved & Hardened

1. **Anti-Escalation Invariant:** An IP address, file name, alert title, rule trigger, or EDR block alone can **never** establish malicious activity.
2. **Dual-Use Tool Corroboration Invariant:** Dual-use administrative tools and Living-off-the-Land Binaries (LOLBins) — such as `whoami`, `net user`, `certutil`, `rundll32`, `vssadmin`, `schtasks`, `reg add`, and unencoded scripts — support a *suspicious activity hypothesis*, but **cannot** automatically certify a malicious breach without corroborating evidence.
3. **Elimination of Overfitted Heuristics:** The hardcoded `known_benign` filename list (`ss-widget`, `clientlib-site`, `adrum`, etc.) introduced in AIS 2.4a has been completely eliminated. Tradecraft is evaluated on factual canonical values (`c.asserted_value`), not model assertions (`c.claim_text`), and static non-executable web assets are recognized generally.
4. **Benign Context Refutation:** If an incident contains affirmative benign administrative context (e.g. enterprise management agents like `ccmexec`, `backup_agent`, or approved change tickets), decisive `TRUE_POSITIVE` proposals are rejected with `BENIGN_CONTEXT_CONTRADICTION` and routed to Advisory Triage (`REQUIRES_ATTENTION`).
5. **Decisive Verdict Preservation:** Legitimate attacks with verified forensic tradecraft (e.g. Mimikatz credential dumping, ransomware shadow deletion without backup context, or external C2 downloads) continue to be accepted as decisive `TRUE_POSITIVE`. Legitimate authorized activities with verified change tickets continue to be accepted as decisive `FALSE_POSITIVE`. The validator does not blindly abstain on every incident.

---

## 2. Refined Decision Architecture in `Check 5` (IndependentVerdictValidator)

```
[Model Proposes TRUE_POSITIVE]
              │
              ▼
   [Check Benign Administrative Context]
   - Enterprise management binary (ccmexec, backup_agent)?
   - Authoritative change ticket (CHG/CR)?
              │
       Yes ───┴───► REJECT to REQUIRES_ATTENTION (BENIGN_CONTEXT_CONTRADICTION)
              │ No
              ▼
   [Classify Grounded Tradecraft in Canonical Evidence]
              │
              ├─► Definitive Attack Markers:
              │   - mimikatz / sekurlsa / lsass dump
              │   - cobaltstrike / meterpreter / beacon
              │   - vssadmin delete shadows / quiet (no backup agent)
              │   - powershell -enc / -encodedcommand
              │   - certutil / downloadstring from external URL
              │   - Verified Threat Intelligence / Malware Hit
              │         │
              │         └─► VALIDATE decisive TRUE_POSITIVE
              │
              ├─► Dual-Use Tools / LOLBins (whoami, net user, certutil, rundll32, reg add):
              │   - Corroborated by:
              │     * Untrusted external destination IP?
              │     * Suspicious execution path (\Temp\, \AppData\, /tmp/)?
              │     * Confirmed Threat Intelligence hit?
              │         │
              │        Yes ──► VALIDATE decisive TRUE_POSITIVE
              │         │
              │        No  ──► OVERRULE to REQUIRES_ATTENTION (TP_CRITERIA_UNSATISFIED)
              │                "Dual-use tool requires corroborating malicious indicators."
              │
              └─► Identifiers / Alert Triggers / Web Assets (.js, .css, .png, widget):
                        │
                        └─► OVERRULE to REQUIRES_ATTENTION (TP_CRITERIA_UNSATISFIED)
                            "Control blocks, binary names, or internal IPs alone do not confirm malice."
```

---

## 3. Detailed Rules for Decisive False Positive (FP) Acceptance

For a model-proposed `FALSE_POSITIVE` to be accepted as decisive, it must satisfy all 10 independent checks:
1. **Verified Telemetry:** Telemetry completeness $\ge 0.5$ and at least 1 grounded claim.
2. **No Invented Change Tickets:** Any ticket referenced in the model's reason must exist in canonical evidence.
3. **Authoritative Provenance:** Change tickets must originate from verified ITSM fields, not untrusted command-line parameters or raw syslog text.
4. **Active Maintenance Window:** Scheduled maintenance windows must be active, approved, and encompass the incident timestamp.
5. **Valid Digital Signature:** Digital signatures must be verified and valid; unsigned, revoked, or failed signatures cannot justify FP.
6. **No Adversary Tradecraft Contradiction:** Telemetry must not contain active adversary patterns (e.g. obfuscated PowerShell, credential access).
7. **No Process-Name Spoofing:** Allowlisted administrative binaries must execute from approved vendor paths (`\System32\`, `\Program Files\`), not user-writable paths (`\Temp\`, `\AppData\`).
8. **In-Scope Authorization:** The target asset in the change ticket must match the incident hostname.
9. **Substantive Grounds:** Cannot rely solely on internal IP address or user account existence.
10. **Absence of Authorization = Advisory Triage:** In the absence of independently verified affirmative authorization, decisive FP is rejected with `FP_CRITERIA_UNSATISFIED` and routed to Advisory Triage (`REQUIRES_ATTENTION`).

---

## 4. Regression & Verification Results

The test suite `backend/tests/test_ais_2_4b_validator_integrity.py` validates all 9 key integrity dimensions:

| Test Case | Scenario | Model Proposal | Validator Disposition | Authoritative Final Verdict | Reason Code | Status |
|---|---|---|---|---|---|---|
| `test_dual_use_lolbin_without_corroboration` | `whoami.exe /all` by DOMADMIN to internal IP | `TRUE_POSITIVE` (85%) | **OVERRULED** | `REQUIRES_ATTENTION` | `TP_CRITERIA_UNSATISFIED` | **PASS** |
| `test_dual_use_lolbin_with_external_corroboration` | `certutil.exe -urlcache` to external IP `203.0.113.55` | `TRUE_POSITIVE` (92%) | **ACCEPTED** | `TRUE_POSITIVE` | `EVIDENCE_VALIDATED` | **PASS** |
| `test_shadow_copy_deletion_with_benign_administrative_context` | `vssadmin delete shadows` with `backup_agent.exe` + ticket | `TRUE_POSITIVE` (95%) | **OVERRULED** | `REQUIRES_ATTENTION` | `BENIGN_CONTEXT_CONTRADICTION` | **PASS** |
| `test_credential_dumping_syntax_validated_as_tp` | `mimikatz.exe sekurlsa::logonpasswords` | `TRUE_POSITIVE` (99%) | **ACCEPTED** | `TRUE_POSITIVE` | `EVIDENCE_VALIDATED` | **PASS** |
| `test_tp_rejection_for_survey_widget_132499009` | `ss-widget.min.js` SurveySensum from internal IP | `TRUE_POSITIVE` (88%) | **OVERRULED** | `REQUIRES_ATTENTION` | `TP_CRITERIA_UNSATISFIED` | **PASS** |
| `test_filename_and_ip_alone_cannot_prove_tradecraft` | `update.exe` to `10.0.0.5` | `TRUE_POSITIVE` (85%) | **OVERRULED** | `REQUIRES_ATTENTION` | `TP_CRITERIA_UNSATISFIED` | **PASS** |
| `test_encoded_powershell_supports_tp` | `powershell.exe -nop -w hidden -enc ...` | `TRUE_POSITIVE` (92%) | **ACCEPTED** | `TRUE_POSITIVE` | `EVIDENCE_VALIDATED` | **PASS** |
| `test_benign_evidence_evaluated_under_fp_criteria` | `ccmexec.exe` under approved ticket `CHG-10293` | `FALSE_POSITIVE` (90%) | **ACCEPTED** | `FALSE_POSITIVE` | `EVIDENCE_VALIDATED` | **PASS** |
| `test_provenance_isolation_and_no_token_fabrication` | `PROVIDER_FAILURE` & `PREFLIGHT_ABSTENTION` | `None` | **ISOLATED** | `REQUIRES_ATTENTION` | `None` tokens preserved | **PASS** |
