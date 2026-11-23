# AIS 2.4 — Multi-Rule Historical Benchmark Results

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.4 (Scalable Multi-Rule Verdict Evaluation & Context Expansion)  
**Date:** November 23, 2026  
**Status:** COMPLETED ACROSS 20 HISTORICAL INCIDENTS  

---

## 1. Executive Summary

Stage 6 evaluated the complete historical multi-rule benchmark corpus consisting of **20 deduplicated FortiSIEM incidents** across CrowdStrike and Palo Alto Prisma SASE.

All evaluations were executed under double-blind ground-truth isolation, with prompt inputs sanitized by `HistoricalGroundTruthValidator.sanitize_incident_for_inference`.

---

## 2. Complete 20-Incident Evaluation Roster

| # | Incident ID | Detection Rule | Ground Truth Label | Model Proposed | Conf | Authoritative Verdict | Accepted? | Status | Grounding Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `132438483` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 2 | `132439932` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 3 | `132441815` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 4 | `132461358` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 5 | `132461368` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 6 | `132472498` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 7 | `132474210` | Crowdstrike: Suspicious Activity | **VERIFIED_FP** | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 8 | `132501348` | Crowdstrike: Suspicious Activity | UNVERIFIED | `TRUE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 9 | `132502453` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 10 | `132527297` | Crowdstrike: Suspicious Activity | UNVERIFIED | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | No | `INSUFFICIENT_EVIDENCE` | 1.00 |
| 11 | `132499009` | Prisma SASE: Suspicious File Threat | **VERIFIED_FP** | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 12 | `132499023` | Prisma SASE: Suspicious File Threat | UNVERIFIED | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 13 | `132499745` | Prisma SASE: Suspicious File Threat | UNVERIFIED | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 14 | `132578774` | Prisma SASE: Suspicious File Threat | UNVERIFIED | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 15 | `132591888` | Prisma SASE: Suspicious File Threat | UNVERIFIED | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 16 | `132595592` | Prisma SASE: Suspicious File Threat | UNVERIFIED | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 17 | `132596403` | Prisma SASE: Suspicious File Threat | **VERIFIED_TP** | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 18 | `132599145` | Prisma SASE: Suspicious File Threat | **VERIFIED_TP** | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 19 | `132599146` | Prisma SASE: Suspicious File Threat | **VERIFIED_TP** | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |
| 20 | `132599330` | Prisma SASE: Suspicious File Threat | **VERIFIED_TP** | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **Yes** | `VALIDATED` | 1.00 |

---

## 3. Ground Truth Cohort Adjudication

Historical incident resolutions were strictly adjudicated according to forensic audit standards:
- **Verified Ground Truth Cohort ($N = 6$):**
  - **Verified TP ($N = 4$):** `132596403`, `132599145`, `132599146`, `132599330` (Human analyst confirmed incident ticket raised with client).
  - **Verified FP ($N = 2$):** `132474210`, `132499009` (Analyst verified legitimate non-suspicious activity).
- **Unverified / Provisional Cohort ($N = 14$):**
  - Incidents carrying containment notes (e.g. *"kill process is true"*, *"proccess is kiled"*, *"Endpoint security has blocked the ultraviewer.exe"*) do NOT provide proof of benign nature and are classified as UNVERIFIED to avoid ground-truth contamination.
