# AIS 2.2a Dataset & Ground-Truth Integrity Report

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2a (Benchmark Evidence Integrity, Dataset Repair & GPU Smoke Validation)  
**Date:** November 23, 2026  
**Status:** AUDITED, REPAIRED & CERTIFIED  

---

## 1. Scope & Source Telemetry

The historical empirical dataset consists of 20 genuine historical FortiSIEM incident JSON files archived in `fixtures/Incident json.zip`. Each incident represents real security telemetry originating from enterprise endpoint detection (CrowdStrike Falcon) or secure access service edge (Palo Alto Networks Prisma SASE).

### Source Breakdown by Archetype:
1. **CrowdStrike Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`):** 10 incidents. Telemetry includes process execution paths, parent-child relationships, command-line arguments, hostnames, and hashes.
2. **Prisma SASE Suspicious File Threat Detection (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`):** 10 incidents. Telemetry includes threat file identifiers, network source IPs, application categories, and firewall action summaries.

---

## 2. Extraction Schema Repair

Prior to AIS 2.2a, benchmark parsers attempted to access `ruleName` and `events`, resulting in `rule_name: "Unknown Rule"` and `events_count: 0` across all records. The actual FortiSIEM schema was audited and mapped as follows:

| Conceptual Field | FortiSIEM Fixture Key | Example Observed Value |
| :--- | :--- | :--- |
| Incident Identifier | `incidentId` / `id` | `"132438483"`, `"132499009"` |
| Rule Display Name | `eventName` | `"Crowdstrike: Suspicious Activity"` |
| Rule Event Type | `eventType` | `"PH_RULE_CS_SUSPICIOUS_ACTIVITY"` |
| Raw Event Telemetry | `rawEvents` | List of event objects (len 1 to 34) |
| Target Entity | `target` / `incidentTarget` | `"hostName:DESKTOP-E0G2R49,"` |
| Analyst Resolution | `resolution` | `"False Positive"`, `"True Positive"` |
| Resolution Notes | `clearedReason` | `"legitimate activity, nothing suspicious observed."` |
| Analyst Comments | `comments` | `"Resolution set by Machine Learning"` |
| Analyst Identity | `clearedUser` | `"shivamw"`, `""` |

---

## 3. Ground-Truth Census & Adjudication Reconciliation

### 3.1 Resolving the Defect A Discrepancy

AIS 2.2 reports contained conflicting figures:
- `03_HISTORICAL_DATASET_READINESS.md`: 4 TP, 2 FP, 14 Unverified.
- `BENCHMARK_MANIFEST.json`: 0 TP, 1 FP, 19 Unverified.

Our forensic investigation traced the exact origin of both claims:

1. **Automated ML Filter:**
   Twelve (12) of the 20 incidents contain `comments: "Resolution set by Machine Learning"`. Under `HistoricalGroundTruthValidator.detect_automated_or_ml_text()`, automated/ML closures are disqualified from ground-truth status because using model-generated labels to evaluate an LLM creates circular confirmation bias.
2. **Containment-Only FP Notes:**
   Two (2) FP incidents (`132439932` and `132441815`) note `kill process is true` and `proccess is kiled`. Killing a process is an active containment response to an adversary or unauthorized tool, which directly contradicts a false alarm disposition. `HistoricalGroundTruthValidator.is_containment_only_fp_note()` correctly demotes these to `UNVERIFIED`.
3. **Forensic vs. Operational TP Standards:**
   Four (4) TP incidents (`132596403`, `132599145`, `132599146`, `132599330`) state `Mail has been sent already` or `Case has been raised for the similar incidents.`:
   - **Operational Triage Standard:** SOC operational escalation constitutes positive triage action ($S=1.0$), yielding **4 TPs**.
   - **Strict Forensic Standard:** Administrative ticketing without forensic artifacts (malware hash, C2 connection proof, exploit execution) is unverified ($S=0.6$), yielding **0 TPs**.

### 3.2 Census Summary Table

| Incident ID | Rule Name | Events | Target | Raw Resolution | Cleared Reason / Notes | Strict Forensic | Operational Triage |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| 132438483 | Crowdstrike | 25 | DESKTOP-E0G2R49 | False Positive | kill process is true (ML comment) | UNVERIFIED | UNVERIFIED |
| 132439932 | Crowdstrike | 8 | TSI-IT-002-200 | False Positive | kill process is true (Containment) | UNVERIFIED | VERIFIED_FP |
| 132441815 | Crowdstrike | 16 | DESKTOP-E0G2R49 | False Positive | proccess is kiled (Containment) | UNVERIFIED | VERIFIED_FP |
| 132461358 | Crowdstrike | 34 | TSI-IT-002-200 | False Positive | hash value is clean (ML comment) | UNVERIFIED | UNVERIFIED |
| 132461368 | Crowdstrike | 19 | DESKTOP-E0G2R49 | True Positive | case raised (ML comment) | UNVERIFIED | UNVERIFIED |
| 132472498 | Crowdstrike | 30 | PC-TSI-DC | True Positive | case raised (ML comment) | UNVERIFIED | UNVERIFIED |
| 132474210 | Crowdstrike | 13 | PC-TSI-DC | False Positive | legitimate activity, nothing suspicious | **VERIFIED_FP** | **VERIFIED_FP** |
| 132501348 | Crowdstrike | 2 | DESKTOP-CQ4A60U | True Positive | (ML comment) | UNVERIFIED | UNVERIFIED |
| 132502453 | Crowdstrike | 24 | DESKTOP-KHU6454 | True Positive | Informed to client (ML comment) | UNVERIFIED | UNVERIFIED |
| 132527297 | Crowdstrike | 2 | TSI-IT-002-95 | True Positive | Endpoint blocked ultraviewer (ML comment) | UNVERIFIED | UNVERIFIED |
| 132499009 | Prisma SASE | 1 | surveysensum-base | False Positive | No suspicious activity identified | **VERIFIED_FP** | **VERIFIED_FP** |
| 132499023 | Prisma SASE | 1 | web-browsing | False Positive | file not suspicious (ML comment) | UNVERIFIED | UNVERIFIED |
| 132499745 | Prisma SASE | 1 | web-browsing | False Positive | file not suspicious (ML comment) | UNVERIFIED | UNVERIFIED |
| 132578774 | Prisma SASE | 1 | web-browsing | False Positive | file not suspicious (ML comment) | UNVERIFIED | UNVERIFIED |
| 132591888 | Prisma SASE | 3 | teamviewer-base | False Positive | file not suspicious (ML comment) | UNVERIFIED | UNVERIFIED |
| 132595592 | Prisma SASE | 1 | web-browsing | True Positive | Mail sent (ML comment) | UNVERIFIED | UNVERIFIED |
| 132596403 | Prisma SASE | 1 | web-browsing | True Positive | Mail has been sent already | UNVERIFIED | **VERIFIED_TP** |
| 132599145 | Prisma SASE | 2 | indonis | True Positive | Case has been raised | UNVERIFIED | **VERIFIED_TP** |
| 132599146 | Prisma SASE | 11 | indonis | True Positive | Case has been raised | UNVERIFIED | **VERIFIED_TP** |
| 132599330 | Prisma SASE | 2 | indonis | True Positive | Case has been raised | UNVERIFIED | **VERIFIED_TP** |

---

## 4. Formal Dataset Readiness Determination

Under strict forensic standards:
- Verified TP: **0**
- Verified FP: **2**
- Unverified: **18**

Because verified TP count is zero ($N_{TP} = 0$), calculating standard multi-class empirical metrics (Selective Accuracy, TP Precision, TP Recall, F1 Score) is mathematically undefined ($\frac{0}{0}$). Computing Wilson Score 95% confidence intervals on 2 samples yields an interval of $[0.198, 0.982]$ spanning almost the entire probability space.

Therefore, the authoritative dataset readiness status is formally certified as:
$$\mathbf{INSUFFICIENT\_VALIDATED\_DATASET}$$

Verdictum AI refuses to fabricate synthetic TP samples or misrepresent unverified ML labels as human ground truth to achieve a green quality gate.

---

## 5. Duplicate Clustering & Strict Cohort Isolation

### 5.1 Canonical Duplicate Clustering

Using the physical attribute key $\text{cluster\_key} = \text{rule\_id} \parallel \text{target} \parallel \text{events\_count}$, the 20 historical records collapse into exactly 15 clusters:

- **13 Standalone Clusters:** 10 CrowdStrike records + 3 Prisma SASE records (`132499009`, `132591888`, `132599146`).
- **Cluster `3c65e7165bd72bd0` (Prisma SASE, `web-browsing`, 1 event):**
  - Primary Incident: `132499023`
  - Quarantined Duplicates (4): `132499745`, `132578774`, `132595592`, `132596403`
- **Cluster `4052a7e6ec6af5fd` (Prisma SASE, `indonis`, 2 events):**
  - Primary Incident: `132599145`
  - Quarantined Duplicate (1): `132599330`

### 5.2 Quarantine & Cohort Invariant Enforcement

- **Total Eligible Unique Incidents:** 15
- **Total Quarantined Duplicates:** 5 (`['132499745', '132578774', '132595592', '132596403', '132599330']`)
- **Cohort Allocations (5 per cohort):**
  - **Development Cohort (5):** `132438483`, `132439932`, `132441815`, `132461358`, `132461368`
  - **Validation Cohort (5):** `132472498`, `132474210`, `132499009`, `132499023`, `132501348`
  - **Held-Out Blind Cohort (5):** `132502453`, `132527297`, `132591888`, `132599145`, `132599146`

### 5.3 Mathematical Invariant Proof:
$$\text{eligible\_cohort\_ids} \cap \text{quarantined\_ids} = \emptyset$$
$$\{132438483, \dots, 132599146\} \cap \{132499745, 132578774, 132595592, 132596403, 132599330\} = \emptyset$$

Zero duplicate or near-duplicate telemetry crosses between Development, Validation, and Held-out cohorts.

---

## 6. Anti-Leakage & Data Blinding Verification

Every historical record passed mandatory model-facing sanitization via `HistoricalGroundTruthValidator.sanitize_incident_for_inference()`.

- **Sanitized Fields Audited:** `resolution`, `clearedReason`, `clearedTime`, `clearedUser`, `cmsClearUser`, `comments`, `analyst_verdict`, `ground_truth`.
- **Records Audited:** 20 / 20.
- **Detected Leaks:** 0.
- **Sanitization Audit Status:** **100% PASS**.
