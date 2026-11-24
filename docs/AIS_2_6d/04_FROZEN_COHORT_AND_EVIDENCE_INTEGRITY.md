# AIS 2.6d — Deliverable 04: Frozen Cohort Manifest & Evidence Integrity Audit

**Phase:** VERDICTUM AI — AIS 2.6d  
**Evaluator Roles:** Security Architect, AI Evaluation Scientist, SOC Detection Engineer, Deployment Governance Auditor  
**Date:** November 24, 2026  
**Status:** COMPLETE & CRYPTOGRAPHICALLY CERTIFIED  
**Target Repository:** `SOC-AI-Agent`  
**Referenced Workstream:** Workstream 3 (Frozen Incident Cohort Integrity)  

---

## 1. Executive Summary & Cohort Invariants

A central mandate of Phase AIS 2.6d is to enforce strict **evaluation cohort immutability**. In benchmark evaluations of machine learning models, altering or curating the evaluation dataset after observing model weaknesses artificially inflates accuracy and invalidates empirical conclusions.

To maintain unbroken scientific integrity across evaluation phases, the **frozen 20-incident development cohort** established in Phase AIS 2.6c is retained without modification. No difficult incidents have been removed, replaced, or substituted.

### Cohort Invariants:
1. **Population Size:** Exactly 20 real FortiSIEM production incidents.
2. **Detection Rule Distribution:**
   - **10 Incidents:** Crowdstrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`).
   - **10 Incidents:** Prisma SASE: Suspicious File Threat Detection (`Prisma_SASE_Suspicious_File_Threat_Detection_`).
3. **Cross-Mode Invariance:** Exactly identical raw telemetry and canonical evidence records are supplied to Mode A (Neutral Baseline), Mode B (Approved Policy), and Mode C (Independent Validator).
4. **Input Blinding:** Historical resolution labels and closure comments are 100% excluded from model-facing prompts and blind human review views.

---

## 2. Frozen Cohort Composition & Cryptographic Hash Manifest

| Incident ID | Rule Category | Target Asset / Source IP | Observed Entity / Artifact | Raw Evidence SHA-256 | Canonical Evidence SHA-256 | Cluster / Lineage Key |
|---|---|---|---|---|---|---|
| **`132438483`** | CrowdStrike | `DESKTOP-E0G2R49` | `UltraViewer_Service.exe` | `8c42a5c48b0a...` | `a9069d2f256a...` | `CS:UltraViewer` |
| **`132439932`** | CrowdStrike | `LAPTOP-V8G0M67` | `UltraViewer_Service.exe` | `c0cf8e815616...` | `019313a96860...` | `CS:UltraViewer` (near-dup) |
| **`132441815`** | CrowdStrike | `DESKTOP-490G5T1` | `UltraViewer_Service.exe` | `a1be43003eb8...` | `5c9f57262060...` | `CS:UltraViewer` (near-dup) |
| **`132461358`** | CrowdStrike | `DESKTOP-78M992B` | `UltraViewer_Service.exe` | `872e4ebdb314...` | `e98038d4177e...` | `CS:UltraViewer` (near-dup) |
| **`132461368`** | CrowdStrike | `DESKTOP-78M992B` | `UltraViewer_Service.exe` | `da7e8dcfcf46...` | `9840eb14c810...` | `CS:UltraViewer` (near-dup) |
| **`132472498`** | CrowdStrike | `DESKTOP-P32M5K9` | `UltraViewer_Service.exe` | `1e95cf28a506...` | `6c10eb3b1f9f...` | `CS:UltraViewer` (near-dup) |
| **`132474210`** | CrowdStrike | `PC-TSI-DC` | `UltraViewer_Service.exe` | `5614946d43f0...` | `7be33dc9e50f...` | `CS:UltraViewer` (DC server) |
| **`132501348`** | CrowdStrike | `DESKTOP-R290LK1` | `UltraViewer_Service.exe` | `dfad630040e3...` | `85a1efba8793...` | `CS:UltraViewer` (near-dup) |
| **`132502453`** | CrowdStrike | `DESKTOP-89M02L8` | `UltraViewer_Service.exe` | `5cbb6db53d9e...` | `375d0b9f5ef7...` | `CS:UltraViewer` (near-dup) |
| **`132527297`** | CrowdStrike | `DESKTOP-5M298P4` | `UltraViewer_Service.exe` | `10f9e160e10e...` | `d720b0b8c2df...` | `CS:UltraViewer` (near-dup) |
| **`132499009`** | Prisma SASE | `172.25.6.85` | `ss-widget.min.js` | `369a47d251d1...` | `6f60a927fa1a...` | `Prisma:WebScript` |
| **`132499023`** | Prisma SASE | `172.25.6.85` | `clientlib-site.min.js` | `1cbddf3214da...` | `484e56598379...` | `Prisma:WebScript` |
| **`132499745`** | Prisma SASE | `172.25.6.143` | `scripts-QBOKETIS.js` | `fa72459c5d01...` | `6027179045fb...` | `Prisma:WebScript` |
| **`132578774`** | Prisma SASE | `172.25.6.208` | `adrum22603859.js` | `2d49db23c713...` | `3f23a6358e0a...` | `Prisma:WebScript` |
| **`132591888`** | Prisma SASE | `172.25.6.208` | `update.exe` | `d720a22da054...` | `415c8986c757...` | `Prisma:BinaryExe` |
| **`132595592`** | Prisma SASE | `172.25.6.95` | `2005.70cb3d6bf67c91a7.js` | `88c3a10508a8...` | `a3ad3234d7f5...` | `Prisma:WebScript` |
| **`132596403`** | Prisma SASE | `172.25.6.101` | `review.es.system.js` | `beeaebf2fa2a...` | `a65a3962b9f6...` | `Prisma:WebScript` |
| **`132599145`** | Prisma SASE | `172.25.14.157` | `jquery.knob.js` | `90807661b369...` | `3780373e449a...` | `Prisma:WebScript` |
| **`132599146`** | Prisma SASE | `172.25.14.157` | `jquery.knob.js` | `5c84d728519c...` | `a5fbe4ef1ae0...` | `Prisma:WebScript` (near-dup) |
| **`132599330`** | Prisma SASE | `172.25.6.143` | `moment-with-locales.min.js` | `9848525b6823...` | `43798cf0c4fb...` | `Prisma:WebScript` |

*Full 64-character SHA-256 hashes are persisted in [EVIDENCE_HASH_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/EVIDENCE_HASH_MANIFEST.json).*

---

## 3. Near-Duplicate Analysis & Shared Lineage

The evaluation scientist audited the dataset for redundant incidents and shared operational event lineage:
1. **CrowdStrike UltraViewer Cluster:**
   - 9 incidents represent client workstations executing `UltraViewer_Service.exe` from `C:\Program Files (x86)\UltraViewer\`.
   - 1 incident (`132474210`) represents a Domain Controller (`PC-TSI-DC`) executing `UltraViewer_Service.exe`.
   - **Lineage Finding:** While the 9 workstation incidents share identical command lines, they occur on different endpoints with distinct timestamps. Incident `132474210` represents a significantly higher risk profile due to asset criticality (Domain Controller). All 10 cases are retained to measure model consistency across identical telemetry on different hosts.
2. **Prisma SASE jQuery Knob Near-Duplicates:**
   - Incidents `132599145` and `132599146` both observe `jquery.knob.js` downloaded by source IP `172.25.14.157` within minutes of each other.
   - **Lineage Finding:** These represent sequential HTTP requests during the same user web session. Both are tracked under cluster key `Prisma_SASE:jquery.knob.js`.
3. **Prisma SASE Executable Binary (`132591888`):**
   - Incident `132591888` is unique among the Prisma SASE population: it is the **sole incident involving a Portable Executable binary (`update.exe`)** rather than a JavaScript file.
   - It represents a distinct operational cluster (`Prisma:BinaryExe`).

---

## 4. Ground Truth Leakage Audit

A comprehensive leakage audit was executed across all 20 incident payloads using `HistoricalGroundTruthValidator`:
- **Unsanitized Payloads:** Contained historical FortiSIEM closure keys: `resolution`, `clearedReason`, `clearedTime`, `clearedUser`.
- **Sanitized Model-Facing & Reviewer Payloads:** The `sanitize_incident_for_inference()` and `sanitize_blind_review_payload()` engines recursively stripped 100% of these keys.
- **Leakage Finding:** Zero leaked resolution tokens or ground-truth hints reached wire prompts or the double-blind review workspace.
- **Audit Result:** **100% PASS (Zero Data Leakage Observed)**.

---

*Machine-readable manifests:*  
- [FROZEN_COHORT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/FROZEN_COHORT_MANIFEST.json)  
- [EVIDENCE_HASH_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/EVIDENCE_HASH_MANIFEST.json)  
- [GROUND_TRUTH_LEAKAGE_AUDIT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/GROUND_TRUTH_LEAKAGE_AUDIT.json)
