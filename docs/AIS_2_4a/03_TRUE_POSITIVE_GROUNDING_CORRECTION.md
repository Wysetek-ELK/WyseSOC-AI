# AIS 2.4a — True Positive Decision Grounding Correction

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `03_TRUE_POSITIVE_GROUNDING_CORRECTION.md`  
**Phase:** AIS 2.4a (Live Inference Provenance & TP Verdict Integrity)  
**Date:** November 23, 2026  
**Status:** REMEDIATED & REGRESSION TESTED  

---

## 1. Executive Summary

In AIS 2.4, incident `132499009`—a benign survey widget (`ss-widget.min.js`) from an internal enterprise host (`172.25.14.80`) categorized by certified historical analyst review as `FALSE_POSITIVE`—was improperly accepted by the independent validator as an authoritative `TRUE_POSITIVE`.

This critical defect compromised the safety model of the platform by allowing an alert without affirmative security tradecraft or malicious evidence to be certified as an active cyber attack.

This document details the root cause investigation, the programmatic corrections in `IndependentVerdictValidator.py`, and the positive/negative regression suites verifying the fix.

---

## 2. Root Cause Analysis: Incident 132499009

### 2.1 The Telemetry Signature
Incident `132499009` represents a Palo Alto Prisma SASE alert:
- **Event Name:** `Prisma SASE ss-widget.min.js Suspicious File Threat Detection from 172.25.14.80`
- **Observed File:** `ss-widget.min.js` (SurveySensum customer feedback web widget)
- **Observed Host / Source IP:** `172.25.14.80` (Internal enterprise network subnet)
- **Application:** `surveysensum-base`
- **Severity:** Low (Alert only, no containment or malicious execution observed)
- **Historical Analyst Resolution:** `False Positive` (Reason: *"file does not found suspicious hence marking as fp"*)

### 2.2 The Validation Failure in AIS 2.4
In AIS 2.4, `IndependentVerdictValidator.py` evaluated model propositions under Check 5 for `TRUE_POSITIVE`. The logic attempted to filter out non-probative fields:
```python
# Prior AIS 2.4 logic:
identifier_fields = {"process.name", "process.file_name", "file.name", "user.name", "endpoint.hostname"}
```
While `file.name` was listed under `identifier_fields`, `network.source_ip` (`172.25.14.80`) was **omitted**.

When the offline simulation (or a hallucinating model) proposed `TRUE_POSITIVE` citing:
1. `file.name` = `ss-widget.min.js`
2. `network.source_ip` = `172.25.14.80` (with `claim_type = "NETWORK_CONNECTION"`)

The validator checked whether any claim was grounded. Because `172.25.14.80` was indeed present in the telemetry, the claim was marked `is_grounded = True`. Because `network.source_ip` was not in `identifier_fields`, the validator treated a standard internal IP connection as proof of *"security tradecraft"*, satisfying Check 5 and accepting `TRUE_POSITIVE`.

---

## 3. Programmatic Correction in `IndependentVerdictValidator.py`

In `backend/app/services/independent_verdict_validator.py`, Check 5 was completely overhauled:

### 3.1 Expanded Control & Identifier Field Blacklists
Alert triggers, rule names, and entity identifiers are observed facts, not proof of adversary malice:
```python
control_action_fields = {
    "security.action", "endpoint.process_blocked", "endpoint.file_quarantined", "action",
    "security.alert_title", "security.event_type", "event.type", "alert.name", "rule.name",
    "event_type", "title", "eventname"
}
identifier_fields = {
    "process.name", "process.file_name", "file.name", "filename", "user.name", "endpoint.hostname",
    "network.source_ip", "network.destination_ip", "source_ip", "destination_ip", "dest_ip",
    "src_ip", "dst_ip", "network.port", "network.source_port", "network.destination_port",
    "device.ip", "reporting_ip", "url.domain", "url.hostname", "application.name",
    "application.category", "collector_name", "reporting_device", "collector.id"
}
```
If a model cites only identifiers or alert triggers, `has_grounded_security_tradecraft` remains `False`.

### 3.2 Affirmative Security Tradecraft Requirements
To accept a decisive `TRUE_POSITIVE`, the telemetry must provide affirmative forensic evidence satisfying at least one of the following deterministic criteria:

1. **Direct Forensic Attack Markers:** Verified LOLBin syntax, shadow copy deletion, command-line obfuscation, or persistence mechanisms in command lines or raw logs:
   - `vssadmin delete shadows`, `-enc`, `encodedcommand`, `mimikatz`, `downloadstring`, `invoke-webrequest`, `cobaltstrike`, `meterpreter`, `lsass`, `procdump`, etc.
2. **Corroborating Threat Intelligence / Malware Feeds:** Verified hits on `threat_intel.*`, `reputation.*`, `antivirus.*`, `virustotal.*`, `ioc.*`, or `malware.*`.
3. **Explicit Attack Semantics:** Specific attack types (`exploit`, `c2`, `beacon`, `trojan`, `ransomware`, `shellcode`, `lateral movement`) where the asserted value is not an excluded benign component (`ss-widget`, `clientlib-site`, `jquery`, `select2`, `adrum`, `surveysensum`).

### 3.3 Fail-Safe Action Directive
If a model proposes `TRUE_POSITIVE` without satisfying these criteria, the validator strictly overrules the proposition:
```python
if preflight.evidence_completeness < 0.6 or claim_grounding.grounded_claims == 0 or not has_grounded_security_tradecraft:
    final_verdict = "REQUIRES_ATTENTION"
    validation_status = "INSUFFICIENT_EVIDENCE"
    reason_codes.append("TP_CRITERIA_UNSATISFIED")
    action_directive = (
        "Insufficient grounded tradecraft or corroborating evidence to confirm malicious attack. "
        "Control blocks or binary names alone do not confirm malice."
    )
```

---

## 4. Verification & Regression Results

In `backend/tests/test_ais_2_4a_tp_grounding.py`:
1. `test_tp_rejection_for_survey_widget_132499009`: **PASSED.** When an adversarial model asserts TP on incident `132499009`, the validator rejects it with `final_verdict == "REQUIRES_ATTENTION"` and `"TP_CRITERIA_UNSATISFIED"`.
2. `test_filename_and_ip_alone_cannot_prove_tradecraft`: **PASSED.** A binary name (`update.exe`) and an IP address (`10.0.0.5`) alone do not prove tradecraft.
3. `test_direct_forensic_evidence_supports_tp_without_external_ti`: **PASSED.** `vssadmin.exe delete shadows /all /quiet` is accepted as `TRUE_POSITIVE` without requiring an external threat intel feed.
4. `test_encoded_powershell_supports_tp`: **PASSED.** Encoded PowerShell execution (`powershell.exe -enc ...`) is accepted as `TRUE_POSITIVE`.
5. `test_alert_trigger_alone_does_not_prove_tradecraft`: **PASSED.** An alert title alone does not justify decisive TP.
6. `test_benign_evidence_evaluated_under_fp_criteria`: **PASSED.** Benign administrative execution with approved change tickets (`CHG-10293`) is properly evaluated under FP rules.
