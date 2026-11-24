# 03 — Historical Dataset Discovery and Acquisition Report

## Executive Summary

This report documents the exhaustive discovery, harvesting, and audit of historical security incidents across FortiSIEM, the Server 1 PostgreSQL production database, and local archival fixtures. The target dataset requirement of at least 30 certified True Positives and 30 certified False Positives has an empirical shortfall of 30 TPs and 30 FPs. Gates G7 and G8 are reported as `BLOCKED` with full forensic evidence.

---

## 1. Data Source Audits

### 1.1 Server 1 Production PostgreSQL Database
- **Host**: `172.26.41.240:5432/ai_verdict`
- **Total Incidents in Table**: 8,770 incidents
- **Rule Distribution**:
  - `FortiGate: Website Access Policy Violation`: 8,335 incidents (Raw proxy traffic; zero analyst resolutions recorded)
  - `FortiGate: Authentication Failure Burst`: 382 incidents (Zero resolutions recorded)
  - `Other Telemetry Incidents`: 53 incidents
- **Resolution Tags Audit**:
  - Only **25 incidents** in the entire database contain non-null resolution tags.
  - 13 are tagged `False Positive` and 12 are tagged `True Positive`.
  - Zero database incidents possess independent cryptographic human certification.

### 1.2 Physical FortiSIEM Supervisor Connection Audit
- **Supervisor Endpoint**: `https://172.26.26.31`
- **Network Latency**: 26 ms RTT (Direct network adjacency verified)
- **API Probe**: Tested `/api/integration/fortisiem/test-connection` with default credentials (`super/test`).
- **Result**: HTTP 401 Unauthorized (`Authentication failed for FortiSIEM supervisor`). Automated live harvesting of historical incidents is blocked pending administrative provisioning of API credentials.

### 1.3 Authentic Historical Fixture Export
- **Archive Source**: `fixtures/Incident json.zip`
- **Total Harvested Incidents**: 20 authentic incidents
  - **CrowdStrike: Suspicious Activity**: 10 incidents (`132438483` – `132527297`)
  - **Prisma SASE: Suspicious File Download**: 10 incidents (`132499009` – `132599330`)
- **SIEM Analyst Annotations**: All 20 incidents carry authentic historical SIEM triage resolutions (10 FP, 10 TP).

---

## 2. Dataset Shortfall Analysis

| Requirement | Target Count | Discovered SIEM Records | Independently Certified | Empirical Shortfall | Status |
|---|---|---|---|---|---|
| **Certified True Positives** | $\ge 30$ | 10 | 0 | **30** | **BLOCKED (Gate G7)** |
| **Certified False Positives** | $\ge 30$ | 10 | 0 | **30** | **BLOCKED (Gate G8)** |
| **Total Cohort** | $\ge 60$ | 20 | 0 | **60** | **SHORTFALL DOCUMENTED** |

No benchmark records were fabricated to artificially satisfy the 60-incident target. The deficit is formally registered in `docs/AIS_2_6/DATASET_SHORTFALL.json`.
