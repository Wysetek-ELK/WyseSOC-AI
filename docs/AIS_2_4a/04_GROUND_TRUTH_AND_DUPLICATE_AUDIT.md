# AIS 2.4a — Ground Truth Quality & Duplicate Cluster Audit

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `04_GROUND_TRUTH_AND_DUPLICATE_AUDIT.md`  
**Phase:** AIS 2.4a (Live Inference Provenance & TP Verdict Integrity)  
**Date:** November 23, 2026  
**Status:** AUDITED & DEDUPLICATED  

---

## 1. Executive Summary

In AIS 2.4, the historical benchmark cohort of 20 FortiSIEM incidents was reported as having 4 Verified True Positives and 4 Verified False Positives. Furthermore, the cohort was described as "deduplicated" even though identical batch-closure clusters existed in the dataset.

This audit evaluates all 20 historical incidents against strict forensic standards:
1. Operational escalation tickets (e.g., *"Mail has been sent already"*, *"Case has been raised for the similar incidents."*) do NOT constitute confirmed malicious compromise.
2. Under `strict_forensic_only = True`, incidents lacking affirmative forensic confirmation of attack are preserved as `UNVERIFIED`.
3. Duplicate closure clusters are explicitly tracked and evaluated separately to prevent multi-event duplicate batches from inflating statistical sample sizes.

---

## 2. Complete 20-Incident Ground Truth Audit Table

| Incident ID | Rule Category / Name | Original FortiSIEM Resolution | Analyst Comments / Cleared Reason | Cleared User | Strict Forensic Ground Truth | Certification Rationale & Notes | Cluster Key | Duplicate Status |
|---|---|---|---|---|---|---|---|---|
| **132438483** | CrowdStrike: Suspicious Activity | False Positive | `kill process is true` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | Automated/ML closure without human provenance. | `d8e56c4626bd` | Primary (False) |
| **132439932** | CrowdStrike: Suspicious Activity | False Positive | `kill process is true` | (None) | **UNVERIFIED** | Containment-only note ("kill process is true") without affirmative benign proof. | `d8e56c4626bd` | Duplicate (True) |
| **132441815** | CrowdStrike: Suspicious Activity | False Positive | `proccess is kiled` | (None) | **UNVERIFIED** | Containment-only note ("proccess is kiled") without affirmative benign proof. | `68f813fcf1ac` | Primary (False) |
| **132461358** | CrowdStrike: Suspicious Activity | False Positive | `hash value is clean` (Comments: "Resolution set by Machine Learning") | `shivamw` | **UNVERIFIED** | Machine Learning label override; unverified provenance. | `a705e53bba48` | Primary (False) |
| **132461368** | CrowdStrike: Suspicious Activity | True Positive | `case raised and client are working on it` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated + operational ticketing action only. | `117b28ca799f` | Primary (False) |
| **132472498** | CrowdStrike: Suspicious Activity | True Positive | `case raised and client are working on it` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated + operational ticketing action only. | `117b28ca799f` | Duplicate (True) |
| **132474210** | CrowdStrike: Suspicious Activity | False Positive | `legitimate activity, nothing suspicious observed.` | (None) | **VERIFIED_FP** | Certified human analyst finding: legitimate activity confirmed. | `d0ac1b022642` | Primary (False) |
| **132501348** | CrowdStrike: Suspicious Activity | True Positive | (Comments: "Resolution set by Machine Learning / compromise using Disable or Modify Tools") | `Yash Mungekar` | **UNVERIFIED** | Automated ML text; no forensic confirmation or human adjudication. | (None) | Primary (False) |
| **132502453** | CrowdStrike: Suspicious Activity | True Positive | `Informed to client, alert still generating` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated + client notification action only. | `0afac968ce97` | Primary (False) |
| **132527297** | CrowdStrike: Suspicious Activity | True Positive | `Endpoint security has blocked the ultraviewer.exe` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated; EDR block alone does not establish malicious attack tradecraft. | `2c79a48b158f` | Primary (False) |
| **132499009** | Prisma SASE: `ss-widget.min.js` | False Positive | `file does not found suspicious hence marking as fp` / `No suspicious activity was identified` | (None) | **VERIFIED_FP** | Certified human finding: SurveySensum feedback widget verified non-suspicious. | `8d234186d820` | Primary (False) |
| **132499023** | Prisma SASE: `clientlib-site.min.js` | False Positive | `file does not found suspicious hence marking as fp` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated label without independent human verification. | `e4d6906d0cab` | Primary (False) |
| **132499745** | Prisma SASE: `scripts-QBOKETIS.js` | False Positive | `file does not found suspicious hence marking as fp` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated label without independent human verification. | `e4d6906d0cab` | Duplicate (True) |
| **132578774** | Prisma SASE: `adrum22603859.js` | False Positive | `file observed is not suspicious` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated label without independent human verification. | `cbb3aaa6abb2` | Primary (False) |
| **132591888** | Prisma SASE: `update.exe` | False Positive | `file observed is not suspicious` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated label without independent human verification. | `e2bd6fe9949f` | Primary (False) |
| **132595592** | Prisma SASE: `2005.70cb...js` | True Positive | `Mail has been sent already` (Comments: "Resolution set by Machine Learning") | (None) | **UNVERIFIED** | ML generated + operational notification email only. | `bd2422ed3605` | Primary (False) |
| **132596403** | Prisma SASE: `review.es.system.js` | True Positive | `Mail has been sent already` | (None) | **UNVERIFIED** | Operational notification email only; zero forensic attack confirmation. | `56a2b5b065d5` | Primary (False) |
| **132599145** | Prisma SASE: `jquery.knob.js` | True Positive | `Case has been raised for the similar incidents.` | (None) | **UNVERIFIED** | Ticketing action only; open-source jQuery library, no compromise evidence. | `59c03e3e980b` | Primary (False) |
| **132599146** | Prisma SASE: `exporting.js` | True Positive | `Case has been raised for the similar incidents.` | (None) | **UNVERIFIED** | Ticketing action only; Highcharts exporting JS, duplicate cluster. | `59c03e3e980b` | Duplicate (True) |
| **132599330** | Prisma SASE: `select2.min.js` | True Positive | `Case has been raised for the similar incidents.` | (None) | **UNVERIFIED** | Ticketing action only; Select2 UI dropdown library, duplicate cluster. | `59c03e3e980b` | Duplicate (True) |

---

## 3. Analysis of Ground Truth Quality

### 3.1 Certified Ground Truth Cohort (N = 2)
Only **2 incidents** satisfy rigorous ground-truth certification:
1. `132474210` (CrowdStrike: Suspicious Activity): Certified False Positive (`legitimate activity, nothing suspicious observed.`).
2. `132499009` (Prisma SASE Suspicious File Threat Detection): Certified False Positive (`file does not found suspicious hence marking as fp`).

### 3.2 Zero Certified True Positives in Available Historical Telemetry
Not a single historical incident labeled "True Positive" contained forensic compromise evidence:
- 6 cases were flagged `Resolution set by Machine Learning` without human investigation notes.
- 4 cases were operational ticketing actions (*"Mail has been sent already"*, *"Case has been raised for the similar incidents."*). In fact, three of these incidents were standard open-source web libraries (`jquery.knob.js`, `exporting.js`, `select2.min.js`).

### 3.3 Duplicate Cluster Analysis
The 20 incidents collapse into **15 unique clusters**:
- **Cluster `d8e56c4626bd`:** `132438483` (Primary), `132439932` (Duplicate)
- **Cluster `117b28ca799f`:** `132461368` (Primary), `132472498` (Duplicate)
- **Cluster `e4d6906d0cab`:** `132499023` (Primary), `132499745` (Duplicate)
- **Cluster `59c03e3e980b`:** `132599145` (Primary), `132599146` (Duplicate), `132599330` (Duplicate)

Reporting duplicate batch closures as independent statistical evaluations produces misleading coverage and sample size claims. The benchmark harness now calculates `unique_cluster_metrics` separately to isolate statistical independence.

---

## 4. Double-Blind Isolation Verification

To prevent ground-truth leakage into prompts or validators:
1. `HistoricalGroundTruthValidator.sanitize_incident_for_inference` deeply strips `resolution`, `clearedReason`, `comments`, `clearedUser`, `clearedTime`, `statusName`, and all analyst annotations.
2. The sanitized payload is verified via `leakage_detected` checks during dataset loading. Zero leakage keys were detected across all 20 records (`leakage_detected_count = 0`).
