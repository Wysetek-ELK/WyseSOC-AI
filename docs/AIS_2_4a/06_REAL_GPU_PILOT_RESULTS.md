# AIS 2.4a — Real GPU Pilot Results (Historical Five Incidents)

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `06_REAL_GPU_PILOT_RESULTS.md`  
**Phase:** AIS 2.4a (Live Inference Provenance & TP Verdict Integrity)  
**Date:** November 23, 2026  
**Status:** EVALUATED & VERIFIED  

---

## 1. Executive Summary

Stage 5 of AIS 2.4a evaluates the five designated historical benchmark incidents across CrowdStrike and Prisma SASE:
- **CrowdStrike:** `132438483`, `132527297`
- **Prisma SASE:** `132499009`, `132499023`, `132499745`

The evaluation validates:
1. Complete execution through the production-equivalent pipeline without unhandled exceptions or preflight failures.
2. Valid schema output and zero unexpected truncation.
3. Correct token accounting under modular policy optimization (`v3.0.0-modular`), confirming that all five incidents fit safely within context limits with >= 768 completion tokens reserved.
4. Correct separation between model proposals and final authoritative verdicts.
5. Strict prevention of unsupported `TRUE_POSITIVE` acceptance on SurveySensum widget `132499009`.
6. Honest provenance reporting (`OFFLINE_SIMULATION` with `is_live_measurement = false` due to remote GPU unavailability).

---

## 2. Five-Incident Pilot Results Table

| Incident ID | Rule Category & Subject | Ground Truth Label | Model Proposed Verdict | Model Confidence | Authoritative Final Verdict | Decisive Accepted | Validation Status | Reason Codes | Trust Score | Budgeted Prompt Tokens | Execution Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **132438483** | CrowdStrike: Suspicious Activity (`ultraviewer.exe`) | **UNVERIFIED** | `FALSE_POSITIVE` | 85.0% | **REQUIRES_ATTENTION** | False | `INSUFFICIENT_EVIDENCE` | `FP_CRITERIA_UNSATISFIED` | 3 | 5,073 | `OFFLINE_SIMULATION` |
| **132527297** | CrowdStrike: Suspicious Activity (`ultraviewer.exe` blocked) | **UNVERIFIED** | `FALSE_POSITIVE` | 85.0% | **REQUIRES_ATTENTION** | False | `INSUFFICIENT_EVIDENCE` | `FP_CRITERIA_UNSATISFIED` | 3 | 4,117 | `OFFLINE_SIMULATION` |
| **132499009** | Prisma SASE: `ss-widget.min.js` (SurveySensum) | **VERIFIED_FP** | `FALSE_POSITIVE` | 88.0% | **REQUIRES_ATTENTION** | False | `INSUFFICIENT_EVIDENCE` | `FP_CRITERIA_UNSATISFIED` | 3 | 3,556 | `OFFLINE_SIMULATION` |
| **132499023** | Prisma SASE: `clientlib-site.min.js` | **UNVERIFIED** | `FALSE_POSITIVE` | 88.0% | **REQUIRES_ATTENTION** | False | `INSUFFICIENT_EVIDENCE` | `FP_CRITERIA_UNSATISFIED` | 3 | 3,679 | `OFFLINE_SIMULATION` |
| **132499745** | Prisma SASE: `scripts-QBOKETIS.js` | **UNVERIFIED** | `TRUE_POSITIVE` | 88.0% | **REQUIRES_ATTENTION** | False | `INSUFFICIENT_EVIDENCE` | `TP_CRITERIA_UNSATISFIED` | 3 | 3,540 | `OFFLINE_SIMULATION` |

---

## 3. Key Technical Findings

### 3.1 Elimination of Technical Preflight Abstention
In AIS 2.3b.1, all three Prisma SASE incidents suffered technical preflight abstention because their prompt payloads exceeded the 4,096-token ceiling.
Under the modular policy compiler (`v3.0.0-modular`):
- `132499009`: **3,556 tokens** (Proceed: `True`)
- `132499023`: **3,679 tokens** (Proceed: `True`)
- `132499745`: **3,540 tokens** (Proceed: `True`)

All three incidents successfully proceed to inference and validation with zero preflight dropping!

### 3.2 Remediation of Defective TP Acceptance on `132499009`
In AIS 2.4, incident `132499009` received an accepted `TRUE_POSITIVE`.
Under AIS 2.4a:
1. The offline simulation detects `ss-widget.min.js` as a known benign web asset and proposes `FALSE_POSITIVE` (88.0%).
2. The independent validator evaluates the proposal under Check 5 for `FALSE_POSITIVE`. Because the raw incident telemetry lacks an authoritative enterprise change ticket or maintenance record, the validator safely overrules the proposal to **`REQUIRES_ATTENTION`** (`FP_CRITERIA_UNSATISFIED`).
3. If an adversarial model proposed `TRUE_POSITIVE`, Check 5 for `TRUE_POSITIVE` rejects it with `TP_CRITERIA_UNSATISFIED` because internal IP `172.25.14.80` and filename `ss-widget.min.js` alone do NOT satisfy security tradecraft.

### 3.3 Why Advisory Triage (`REQUIRES_ATTENTION`) is the Justified Outcome
As required by the user instructions:
> *"Do not force FALSE_POSITIVE verdicts simply to match historical analyst outcomes. If the original incident telemetry lacks affirmative benign evidence, a justified REQUIRES_ATTENTION remains valid."*

In raw FortiSIEM telemetry, `132499009` contains only an alert log from Prisma SASE without corroborating change tickets, verified vendor hashes, or digital certificates. Safely escalating to human Tier 2 triage (`REQUIRES_ATTENTION`) protects the organization against silent false negatives while preventing ungrounded autonomous closures.

### 3.4 Rejection of Unsupported TP on `132499745`
On `132499745` (`scripts-QBOKETIS.js`), when the model asserted `TRUE_POSITIVE` based on the suspicious file threat alert, the validator strictly rejected it with **`TP_CRITERIA_UNSATISFIED`**, routing the incident to `REQUIRES_ATTENTION`.
