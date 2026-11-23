# AIS 2.3a — Guardrail Rejection Root Cause Analysis

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3a (Runtime Evidence, Guardrail & Accuracy Integrity Correction)  
**Date:** November 23, 2026  
**Status:** COMPLETED & CATEGORIZED  

---

## 1. Executive Summary

In Phase AIS 2.3, the local Qwen model (`Qwen/Qwen2.5-7B-Instruct-AWQ`) proposed `FALSE_POSITIVE` verdicts for **10 out of 10 Prisma SASE incidents**. However, the `IndependentVerdictValidator` intercepted and demoted all 10 proposals to `REQUIRES_ATTENTION`.

This audit investigated whether these 10 guardrail rejections were:
1. **Technical Validation Defects:** A parsing, normalization, or citation resolution bug in the pipeline rejecting an otherwise valid and grounded model verdict.
2. **Substantive Safety Guardrail Enforcement:** A necessary and sound security policy decision preventing autonomous closure of alerts lacking verifiable proof of authorization.

### Key Finding:
The rejections were driven by a **dual-layer mechanism**:
- **Layer 1 (Technical Defect):** Qwen attempted to cite `File Name` (`ss-widget.min.js`), but because `EvidenceCompactionService` evicted `process.file_name` from `canonical_evidence`, Qwen generated synthetic IDs (`EV-132499009-TOP-file_name`), causing `EVIDENCE_REFERENCE_NOT_FOUND`.
- **Layer 2 (Substantive Security Guardrail):** Even when citation resolution is corrected, `IndependentVerdictValidator` correctly rejects `FALSE_POSITIVE` because observing a common JavaScript file (`ss-widget.min.js`) or an internal IP address does **not** provide affirmative evidence of benign authorization (e.g., approved change ticket, clean VirusTotal/threat intel hash reputation, or verified cryptographic signature). Under Tier-3 SOC policy, closing a threat alert based on a recognizable filename alone introduces critical blind spots and false negative risks.

Therefore, demoting these 10 model proposals to `REQUIRES_ATTENTION` is **substantively correct and safe SOC behavior**.

---

## 2. Guardrail Rejection Taxonomy

Every model verdict evaluated by `IndependentVerdictValidator` is categorized under four rigorous classifications:

| Category Code | Classification Name | Definition | System Action |
| :--- | :--- | :--- | :--- |
| **G-TECH-01** | Technical Citation Mapping Defect | Model cited evidence that exists in raw telemetry but was dropped or mislabeled during compaction. | Bug fix required in normalization / compaction pipeline. |
| **G-SEC-01** | Insufficient Benign Corroboration | Model concluded FP based on common names or internal IPs without affirmative cryptographic or change proof. | Fail-safe demotion to `REQUIRES_ATTENTION`. |
| **G-SEC-02** | Unsupported Threat Claim | Model concluded TP without establishing actionable attacker tradecraft or malice indicators. | Fail-safe demotion to `REQUIRES_ATTENTION`. |
| **G-HALL-01** | Outright Hallucination | Model invented telemetry values (IPs, hashes, usernames) not present anywhere in raw events. | Immediate rejection and audit alert. |

---

## 3. Incident-by-Incident Rejection Analysis (All 10 Prisma SASE Incidents)

| Index | Incident ID | Proposed Verdict | Cited Evidence ID | Asserted Reason | Technical Defect Present? | Substantive Safety Reason | Authoritative Outcome |
| :---: | :---: | :---: | :--- | :--- | :---: | :--- | :---: |
| **1** | `132499009` | `FALSE_POSITIVE` | `EV-132499009-TOP-file_name` | "File ss-widget.min.js is a recognized SurveySensum analytics script downloaded over HTTPS." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Script name match is alert filter noise, not cryptographic authorization. | `REQUIRES_ATTENTION` |
| **2** | `132499023` | `FALSE_POSITIVE` | `EV-132499023-TOP-file_name` | "Legitimate web analytics asset from surveysensum-base application." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: No hash reputation or internal change management ticket verified. | `REQUIRES_ATTENTION` |
| **3** | `132499745` | `FALSE_POSITIVE` | `EV-132499745-TOP-file_name` | "survey-sensum telemetry widget from survey vendor." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Third-party script source unverified by EDR or sandbox. | `REQUIRES_ATTENTION` |
| **4** | `132578774` | `FALSE_POSITIVE` | `EV-132578774-TOP-file_name` | "survey widget javascript component." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Lacks signed certificate or verified SHA256 reputation. | `REQUIRES_ATTENTION` |
| **5** | `132591888` | `FALSE_POSITIVE` | `EV-132591888-TOP-file_name` | "Repeated download of ss-widget.min.js from cloudflare CDN." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Cloudflare CDN IP does not prove benign intent. | `REQUIRES_ATTENTION` |
| **6** | `132595592` | `FALSE_POSITIVE` | `EV-132595592-TOP-file_name` | "Standard web tracking pixel/script." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Insufficient evidence to rule out supply chain compromise. | `REQUIRES_ATTENTION` |
| **7** | `132644265` | `FALSE_POSITIVE` | `EV-132644265-TOP-file_name` | "Vendor script asset." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Missing internal corporate approval verification. | `REQUIRES_ATTENTION` |
| **8** | `132657422` | `FALSE_POSITIVE` | `EV-132657422-TOP-file_name` | "Web analytics library." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Absence of affirmative security authorization record. | `REQUIRES_ATTENTION` |
| **9** | `132715104` | `FALSE_POSITIVE` | `EV-132715104-TOP-file_name` | "JavaScript widget download." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Alert triggered on suspicious file; file was not detonated or hashed. | `REQUIRES_ATTENTION` |
| **10** | `132718386` | `FALSE_POSITIVE` | `EV-132718386-TOP-file_name` | "Known vendor analytics code." | YES (`File Name` evicted) | `FP_CRITERIA_UNSATISFIED`: Triage requires analyst review of origin host. | `REQUIRES_ATTENTION` |

---

## 4. Deep-Dive on Substantive Safety Invariant

Why can Verdictum AI never accept `FALSE_POSITIVE` without cryptographic or administrative corroboration?

### 4.1 Threat Context: Supply Chain & Script Smuggling
In modern enterprise environments, threat actors frequently name malicious loaders after familiar benign tools (e.g., `ss-widget.min.js`, `update.js`, `analytics.min.js`) or compromise legitimate third-party SaaS CDNs. A model that marks an alert `FALSE_POSITIVE` simply because the filename reads "ss-widget.min.js" would create an unacceptable false-negative blind spot.

### 4.2 Approved Policy v7 Invariant
Detection Policy v7 explicitly mandates:
> **False Positive Acceptance Standard:**
> A verdict of `FALSE_POSITIVE` requires at least ONE of the following affirmative criteria:
> 1. Verified Cryptographic Reputation: SHA256 matches an established clean reputation baseline in local cache or trusted whitelist.
> 2. Documented Administrative Authorization: An active change management ticket, maintenance window, or vulnerability assessment activity is documented for the host.
> 3. Verified System Binary Integrity: Binary originates from an OS vendor-signed, immutable directory with intact signature.
>
> In the absence of affirmative benign proof, alerts where suspicious indicators cannot be verified MUST be classified as `REQUIRES_ATTENTION`.

### 4.3 Evaluation of Historical Ground Truth
In the historical FortiSIEM dataset, the human analyst closed 7 of these incidents as "False Alarm" or "Cleared". However, the human analyst did so with the benefit of external context (knowing that the organization uses SurveySensum internally) that was **not** present in the FortiSIEM incident JSON.

Because Verdictum AI is evaluated in strict double-blind isolation without external threat intelligence feeds (such as live VirusTotal or CMDB APIs), the AI correctly and safely refrained from guessing, delegating the final determination to the human SOC analyst.

---

## 5. Conclusion

1. The technical defect (`EVIDENCE_REFERENCE_NOT_FOUND` on `File Name`) has been corrected by preserving `file.name` and adding canonical aliasing.
2. The substantive safety guardrail (`FP_CRITERIA_UNSATISFIED` $\rightarrow$ `REQUIRES_ATTENTION`) performed exactly as designed, preventing ungrounded autonomous closure.
3. The 10 Prisma SASE demotions represent **safe, resilient, fail-closed SOC triage**.
