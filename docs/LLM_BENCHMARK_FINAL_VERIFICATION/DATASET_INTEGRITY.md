# Verdictum AI — Historical Dataset Integrity & Ground Truth Audit

**Document Version**: 2.0.0  
**Date**: November 2026  
**Status**: AUDITED & CLUSTER-RECONCILED  
**Data Sources**: `fixtures/Incident json.zip` & `backend/ai_verdict.db`  

---

## 1. Executive Summary

This document presents a comprehensive, item-by-item audit of the historical incident evaluation cohort used by Verdictum AI. It establishes data provenance, inspects ground truth adjudications, identifies duplicate alert clusters, and quarantines synthetic test fixtures from empirical accuracy denominators.

### Key Dataset Statistics:
- **Total Historical SIEM Incidents**: **20 incidents**
  - `PH_RULE_CS_SUSPICIOUS_ACTIVITY`: 10 incidents
  - `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`: 10 incidents
- **Duplicate Alerts**: **5 duplicate alerts** spanning **4 duplicate clusters**
- **Independent Unique Clusters**: **15 unique clusters**
- **Ground Truth Adjudication Framework**:
  - **Tier A (Strict Forensic Confirmation)**: **2 Verified FPs**, **0 Verified TPs**, **18 Unverified**
  - **Tier B (Operational Triage Escalation)**: **2 Verified FPs**, **4 Verified TPs**, **14 Unverified**
- **Synthetic Unit Test Fixtures (`INC-DEBUG-*`)**: **6 fixtures** quarantined from empirical accuracy denominators.

---

## 2. Complete Historical Incident Inventory (20 Real SIEM Alerts)

| # | Incident ID | Rule ID | Raw Resolution | Cleared Reason | Comments / Actor | Prompt Tokens | Context Status (<16k) | Cluster ID | Ground Truth Tier B | Ground Truth Tier A |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `132438483` | CS Suspicious Activity | False Positive | "kill process is true" | ML Comment | 48,433 | **EXCEEDED (48k)** | `d8e56c4626bd7cbe` | UNVERIFIED | UNVERIFIED |
| 2 | `132439932` | CS Suspicious Activity | False Positive | "kill process is true" | Analyst (containment note) | 17,643 | **EXCEEDED (17k)** | `d8e56c4626bd7cbe` (dup) | UNVERIFIED | UNVERIFIED |
| 3 | `132441815` | CS Suspicious Activity | False Positive | "proccess is kiled" | Analyst (containment note) | 31,773 | **EXCEEDED (31k)** | `68f813fcf1ac1b35` | UNVERIFIED | UNVERIFIED |
| 4 | `132461358` | CS Suspicious Activity | False Positive | "hash value is clean" | ML Comment | 62,392 | **EXCEEDED (62k)** | `a705e53bba481fd0` | UNVERIFIED | UNVERIFIED |
| 5 | `132461368` | CS Suspicious Activity | True Positive | "case raised and client are working on it" | ML Comment | 37,686 | **EXCEEDED (37k)** | `117b28ca799fe31f` | UNVERIFIED | UNVERIFIED |
| 6 | `132472498` | CS Suspicious Activity | True Positive | "case raised and client are working on it" | ML Comment | 54,998 | **EXCEEDED (55k)** | `117b28ca799fe31f` (dup) | UNVERIFIED | UNVERIFIED |
| 7 | `132474210` | CS Suspicious Activity | False Positive | "legitimate activity, nothing suspicious observed." | Human Analyst Adjudication | 26,367 | **EXCEEDED (26k)** | `d0ac1b022642311e` | **VERIFIED_FP** | **VERIFIED_FP** |
| 8 | `132501348` | CS Suspicious Activity | True Positive | (empty) | ML Compromise Comment | 13,188 | **FITS (13.1k)** | `unique_132501348` | UNVERIFIED | UNVERIFIED |
| 9 | `132502453` | CS Suspicious Activity | True Positive | "Informed to client, alert still generating" | ML Comment | 44,771 | **EXCEEDED (44k)** | `0afac968ce97e9e0` | UNVERIFIED | UNVERIFIED |
| 10 | `132527297` | CS Suspicious Activity | True Positive | "Endpoint security has blocked the ultraviewer.exe" | ML Comment | 11,691 | **FITS (11.6k)** | `2c79a48b158f06fc` | UNVERIFIED | UNVERIFIED |
| 11 | `132499009` | Prisma SASE Suspicious File | False Positive | "No suspicious activity was identified during the analysis" | Human Analyst Adjudication | 8,188 | **FITS (8.1k)** | `90797a40b38f1526` | **VERIFIED_FP** | **VERIFIED_FP** |
| 12 | `132499023` | Prisma SASE Suspicious File | False Positive | "file does not found suspicious hence marking as fp" | ML Comment | 8,229 | **FITS (8.2k)** | `68396109b54ad6fe` | UNVERIFIED | UNVERIFIED |
| 13 | `132499745` | Prisma SASE Suspicious File | False Positive | "file does not found suspicious hence marking as fp" | ML Comment | 8,182 | **FITS (8.1k)** | `68396109b54ad6fe` (dup) | UNVERIFIED | UNVERIFIED |
| 14 | `132578774` | Prisma SASE Suspicious File | False Positive | "file observed is not suspicious" | ML Comment | 8,269 | **FITS (8.2k)** | `fe1d28e33a7be6fe` | UNVERIFIED | UNVERIFIED |
| 15 | `132591888` | Prisma SASE Suspicious File | False Positive | "file observed is not suspicious" | ML Comment | 11,179 | **FITS (11.1k)** | `5d0a52504997be4c` | UNVERIFIED | UNVERIFIED |
| 16 | `132595592` | Prisma SASE Suspicious File | True Positive | "Mail has been sent already" | ML Comment | 8,275 | **FITS (8.2k)** | `bcb69e166d273984` | UNVERIFIED | UNVERIFIED |
| 17 | `132596403` | Prisma SASE Suspicious File | True Positive | "Mail has been sent already" | Human Analyst (notification) | 8,249 | **FITS (8.2k)** | `d8a299ecb62b3490` | **VERIFIED_TP** | UNVERIFIED |
| 18 | `132599145` | Prisma SASE Suspicious File | True Positive | "Case has been raised for the similar incidents." | Human Analyst (ticketing) | 9,964 | **FITS (9.9k)** | `fa6267a0b58bb3a9` | **VERIFIED_TP** | UNVERIFIED |
| 19 | `132599146` | Prisma SASE Suspicious File | True Positive | "Case has been raised for the similar incidents." | Human Analyst (ticketing) | 19,105 | **EXCEEDED (19k)** | `fa6267a0b58bb3a9` (dup) | **VERIFIED_TP** | UNVERIFIED |
| 20 | `132599330` | Prisma SASE Suspicious File | True Positive | "Case has been raised for the similar incidents." | Human Analyst (ticketing) | 9,963 | **FITS (9.9k)** | `fa6267a0b58bb3a9` (dup) | **VERIFIED_TP** | UNVERIFIED |

---

## 3. Duplicate Alert Clusters Analysis

### 3.1 Cluster Breakdown
1. **Cluster `d8e56c4626bd7cbe` (2 incidents)**:
   - Primary: `132438483`
   - Duplicate: `132439932`
   - Shared Rationale: *"kill process is true"*
2. **Cluster `117b28ca799fe31f` (2 incidents)**:
   - Primary: `132461368`
   - Duplicate: `132472498`
   - Shared Rationale: *"case raised and client are working on it"*
3. **Cluster `68396109b54ad6fe` (2 incidents)**:
   - Primary: `132499023`
   - Duplicate: `132499745`
   - Shared Rationale: *"file does not found suspicious hence marking as fp"*
4. **Cluster `fa6267a0b58bb3a9` (3 incidents)**:
   - Primary: `132599145`
   - Duplicate 1: `132599146`
   - Duplicate 2: `132599330`
   - Shared Rationale: *"Case has been raised for the similar incidents."*

### 3.2 Reconciliation Math
- Total Raw Incidents: **20**
- Duplicate Alerts Flagged: **5**
- Independent Unique Incident Clusters: **15** ($20 - 5 = 15$)
- Among Verified Incidents (Tier B): **6 incidents** represent **4 independent clusters** (2 FP clusters + 2 TP clusters).

---

## 4. Ground Truth Adjudication: Escalation vs Forensics

### 4.1 The Operational Escalation Dilemma
In SOC operations, analysts frequently close or escalate alerts by entering operational procedural notes:
- *"Mail has been sent already"* (Notification to user or customer)
- *"Case has been raised for the similar incidents."* (Ticketing escalation to Tier 2 or IR)

While these notes prove that the incident was escalated rather than dismissed as routine noise, **they do not prove that an attack actually succeeded or caused malicious harm**. A customer ticket might later be resolved as an approved test, a misconfigured script, or a false alarm.

### 4.2 Tiered Evaluation Framework
1. **Tier A (Strict Forensic Ground Truth)**:
   - Requires confirmed attack indicators (e.g., confirmed malware payload, verified C2 communication, unauthorized privilege escalation).
   - Classifies procedural notifications ("Mail sent", "Case raised") as `UNVERIFIED`.
   - **Result**: 0 Verified TPs, 2 Verified FPs, 18 Unverified.
2. **Tier B (Operational Triage Ground Truth)**:
   - Accepts analyst incident escalation as provisional operational ground truth for TP.
   - **Result**: 4 Verified TPs, 2 Verified FPs, 14 Unverified.

---

## 5. Synthetic Fixtures Quarantine Audit

In `backend/ai_verdict.db`, six synthetic fixtures were created during unit testing:
- `INC-DEBUG-01` (Resolution: "True Positive")
- `INC-DEBUG-02` (Resolution: "False Positive")
- `INC-DEBUG-03` (Resolution: None)
- `INC-DEBUG-04` (Resolution: "Under Investigation")
- `INC-DEBUG-05` (Resolution: None)
- `INC-DEBUG-06` (Resolution: "True Positive")

### Quarantine Verification:
- In `load_dataset_from_db(include_synthetic=False)`, any incident ID prefixed with `INC-DEBUG-`, `INC-TEST-`, or `SYNTHETIC-` is strictly excluded.
- Total records returned from DB: exactly **20** (matching the 20 real historical incidents in the zip archive).
- When `include_synthetic=True`, all 26 records are returned for functional testing.

---

## 6. Blinding & Anti-Leakage Verification

To prevent circular reasoning or data leakage during benchmark evaluation, `HistoricalGroundTruthValidator.sanitize_incident_for_inference` recursively strips the following fields from incident payloads prior to inference:
- `resolution`
- `clearedReason`
- `clearedTime`
- `clearedUser`
- `cmsClearUser`
- `comments`
- `analyst_verdict`
- `ground_truth`

The automated test `test_blinding_integrity_blocks_all_leakage` verified across all 20 historical incidents that **0 leakage keys** exist in the sanitized payloads.
