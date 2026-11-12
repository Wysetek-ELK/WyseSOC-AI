# Verdictum AI — Server 1 Ground-Truth Readiness Report

**Report Date:** 2026-11-12T04:25:00Z  
**Database Host:** PostgreSQL on Server 1 (`ai_verdict`)  
**Scope:** 3,857 Audited Incidents & Historical Ground-Truth Records  
**Assessment Outcome:** **PROVENANCE AUDITED & ISOLATED (Review Queue Staged)**

---

## 1. Executive Ground-Truth Summary

The baseline audit identified that while 3,379 historical incidents contain resolution labels (3,355 True Positives, 24 False Positives), **exactly zero records** have `is_independently_verified = true` in the `investigations` table, and **3,367 records (99.64%)** were flagged as ML-generated.

This audit traced the complete data provenance path to understand the relationship between FortiSIEM ingestion, automated ML tagging, analyst review notes, and application verification flags.

```
+-----------------------------------------------------------------------------------------+
| Ground-Truth Ingestion & Provenance Architecture                                        |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [FortiSIEM Supervisor]                                                                 |
|         |                                                                               |
|         v (FortiSIEM Sync Ingestion)                                                    |
|  [HistoricalGroundTruth Table]                                                          |
|         |-- resolution ("True Positive" / "False Positive")                             |
|         |-- is_ml_generated = TRUE (Defaulted by batch sync on 3,367 records)           |
|         |-- cleared_user (Recorded on 2 incidents only: shivamw, Yash Mungekar)         |
|         |-- cleared_reason (Recorded on 33 incidents: e.g. "hash value is clean")       |
|         |                                                                               |
|         v (Investigation Initialization)                                                |
|  [Investigations Table]                                                                 |
|         |-- status: "PENDING_REVIEW" (100% of 3,857 records)                            |
|         |-- is_independently_verified: FALSE (Gated behind dual-analyst review API)     |
|         |-- is_disputed: FALSE                                                          |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Root Cause: Why Are Zero Incidents Independently Verified?

In Verdictum AI, an incident label is **not** considered "independently verified" merely because it was closed or labeled in FortiSIEM. 

The application enforces a strict two-stage verification lifecycle:
1. **Stage 1 (SIEM Ingestion):** The connector imports historical incidents into `incidents` and `historical_ground_truth`. When historical incidents are imported via batch scripts without explicit human cryptographic attribution, `is_ml_generated` defaults to `true`.
2. **Stage 2 (Investigation Workbench Dual Verification):** A record achieves `is_independently_verified = true` **only** when an analyst navigates to the Investigation Workbench and executes:
   ```http
   POST /api/investigations/{incident_id}/verify
   ```
   This action requires a secondary analyst confirmation, verifies that ground-truth evidence meets G1–G7 criteria, records the verifier's identity, and timestamps the verification.

Because historical records were imported en masse during initial setup and have not yet undergone formal review in the Verdictum AI Workbench, all 3,857 records remain in `status = PENDING_REVIEW` with `is_independently_verified = false`.

> [!IMPORTANT]
> **Data Provenance Rule:** The agent MUST NOT execute an automated database query to bulk-promote `is_independently_verified=true` or alter `is_ml_generated=false`. Fabricating verification provenance would corrupt the empirical integrity of G8 simulation evaluations.

---

## 3. Human-Attributed Historical Records

The audit isolated all historical records containing human analyst involvement:

### 3.1 Incidents with Authoritative `cleared_user` Attribution
1. **Incident ID `132461358`:**
   - **Rule:** `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (Crowdstrike: Suspicious Activity)
   - **Resolution:** `False Positive`
   - **Cleared User:** `shivamw`
   - **Cleared Reason:** `"hash value is clean"`
   - **Significance:** High-value benchmark control for crowdstrike FP suppression.
2. **Incident ID `132501348`:**
   - **Rule:** `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (Crowdstrike: Disable or Modify Tools)
   - **Resolution:** `True Positive`
   - **Cleared User:** `Yash Mungekar`
   - **Cleared Reason:** N/A (Standard confirmation)
   - **Significance:** High-value benchmark control for crowdstrike true intrusion detection.

### 3.2 Incidents with Authoritative `cleared_reason` Attribution (33 Records)
33 incidents contain explicit analyst closure rationale, including:
- `"hash value is clean"` (FP)
- `"Endpoint security has blocked the ultraviewer.exe"` (FP)
- `"No suspicious activity was identified during the analysis"` (FP)
- `"file does not found suspicious hence marking as fp"` (FP)
- `"legitimate activity, nothing suspicious observed."` (FP)
- `"kill process is true"` (TP)
- `"Case is created"` (TP)

---

## 4. Ground-Truth Classification Matrix

All 3,857 audited historical incidents are categorized into 6 distinct tiers:

| Tier | Category Name | Record Count | Description & Ingestion Action |
| :---: | :--- | :---: | :--- |
| **1** | **Independently Verified TP** | **0** | Awaiting dual-analyst workbench sign-off |
| **2** | **Independently Verified FP** | **0** | Awaiting dual-analyst workbench sign-off |
| **3** | **Human Review Candidates** | **35** | High-priority queue (contains cleared_user or cleared_reason) |
| **4** | **Automated ML Resolutions** | **3,344** | Machine-derived labels from batch SIEM sync |
| **5** | **Disputed / Ambiguous** | **0** | Zero incidents currently flagged as disputed |
| **6** | **Unlabeled Incidents** | **478** | Raw historical telemetry without ground-truth disposition |
| **TOTAL** | **Audited Dataset** | **3,857** | **100% of Database Accounted For** |

---

## 5. Structured Human Re-Adjudication Workflow

To establish verified benchmark controls for G8 policy simulation without compromising provenance:

1. **Step 1: Prioritize Human Review Candidates (35 Incidents)**
   - Target the 35 Category 3 incidents possessing analyst reasons or user tags.
   - Example: Incident `132461358` (`shivamw`, `"hash value is clean"`).
2. **Step 2: Analyst Review Action in Workbench**
   - The SOC Lead logs into Verdictum AI (`http://<server1_ip>:3000`).
   - Navigates to **Investigation Workbench** -> Filter by: `Has Human Notes`.
   - Inspects the telemetry payload, verifies the closure rationale against SIEM evidence.
   - Clicks **"Confirm Independent Verification"**.
3. **Step 3: Verification Endpoint Execution**
   - Backend sets `Investigation.is_independently_verified = true`.
   - Backend logs the action in `audit_logs` with cryptographic signature.
4. **Step 4: G8 Benchmark Activation**
   - Verified records become automatically eligible as "hard positive" and "hard negative" benchmark controls in AIS Simulation Lab.
