# 04 — Rule-Specific Ground-Truth Certification Report

## Executive Summary

This report establishes the rule-specific adjudication criteria separating detection correctness from malicious compromise, enforces the cryptographic schema separating historical SIEM resolutions from verified ground truth, and audits the certification provenance of all 20 benchmark incidents.

---

## 1. Rule-Specific Adjudication Criteria

### 1.1 Crowdstrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)
- **Behavioral Archetype**: Remote Access Software / Dual-Use Administrative Utility (`UltraViewer_setup.exe`).
- **Detection Correctness (Alert Trigger)**: The detection rule correctly fired on the execution of an unapproved administrative remote access binary.
- **Compromise vs. Operational Policy**:
  - **Malicious Tradecraft (True Positive)**: Execution of remote tool accompanied by untrusted external C2, privilege escalation, credential dumping (`sekurlsa`), or encoded PowerShell downloaders.
  - **Benign Violation (False Positive / Operational Violation)**: An employee or IT administrator executing a known utility for internal support without prior ticket approval, with zero secondary attack indicators.
- **Historical SIEM Resolution**: Operational analysts tagged 9 of 10 as `True Positive` because policy prohibited UltraViewer, conflating an IT policy violation with an adversary intrusion.

### 1.2 Prisma SASE: Suspicious File Download (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`)
- **Behavioral Archetype**: Web Gateway Download of Executable/Script Assets.
- **Detection Correctness**: The perimeter gateway alerted on downloads of `.js` files from external domains (`surveysensum.com`, CDN mirrors).
- **Adjudication**:
  - **True Positive**: Drive-by download or weaponized script delivering malware.
  - **False Positive**: Legitimate customer feedback widgets, corporate analytics libraries, or jQuery dependencies.
- **Historical SIEM Resolution**: Analysts tagged all 10 as `False Positive` after verifying the domains were legitimate business services.

---

## 2. Ground-Truth Data Structure & Provenance Separation

To prevent label leakage and distinguish historical triage from verified truth, every manifest record carries distinct orthogonal fields:
```json
{
  "incident_id": "132474210",
  "historical_siem_resolution": "False Positive",
  "historical_siem_cleared_reason": "legitimate activity, nothing suspicious observed.",
  "historical_analyst_user": "security_analyst_3",
  "independent_human_certification_status": "PROVISIONAL_UNVERIFIED",
  "certification_provenance": "HISTORICAL_SIEM_RECORD_ONLY",
  "certified_label": null,
  "provisional_label": "FALSE_POSITIVE"
}
```

All 20 incidents are classified as `PROVISIONAL_UNVERIFIED`. Zero cases are falsely marked as certified.
