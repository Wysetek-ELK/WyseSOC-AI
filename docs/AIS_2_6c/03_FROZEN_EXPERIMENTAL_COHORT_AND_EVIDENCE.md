# AIS 2.6c — Workstream 3: Frozen Experimental Development Cohort & Evidence Manifest
**Document ID:** `03_FROZEN_EXPERIMENTAL_COHORT_AND_EVIDENCE.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Cohort Scope:** Authentic 20-Incident Development Cohort (10 CrowdStrike, 10 Prisma SASE)  
**Artifacts Generated:**  
- `docs/AIS_2_6c/FROZEN_COHORT_MANIFEST.json`  
- `docs/AIS_2_6c/EXPERIMENT_EVIDENCE_MANIFEST.json`  
- `docs/AIS_2_6c/EVIDENCE_SUFFICIENCY_MATRIX.json`  

---

## 1. Frozen Cohort Definition & Provenance

The 20-incident evaluation cohort is strictly frozen to guarantee identical input conditions across experimental Modes A, B, and C. This population is an authentic development cohort derived from historical FortiSIEM production imports, not an independent holdout dataset.

### Cohort Composition Summary:
- **Total Incidents:** 20
- **Rule Family 1 (CrowdStrike):** `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (10 incidents)
  - 9 incidents involving `UltraViewer_Service.exe` (remote administration tool)
  - 1 incident involving `MEGAsync.exe` (`132501348`, cloud sync utility)
- **Rule Family 2 (Prisma SASE):** `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` (10 incidents)
  - 9 incidents involving static JavaScript web libraries (`jquery.knob.js`, `ss-widget.min.js`, `clientlib-site.min.js`, etc.)
  - 1 incident involving a portable executable binary (`132591888`, `update.exe`)

---

## 2. Frozen Incident Inventory

| Incident ID | Detection Rule | Target Host / IP | Observed Entity / Binary | Raw Evidence SHA-256 |
|---|---|---|---|---|
| **132438483** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `9098ef0d...` |
| **132439932** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `ac4ce163...` |
| **132441815** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `de63af26...` |
| **132461358** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `cc24912c...` |
| **132461368** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `b50dfa2c...` |
| **132472498** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `0e0cb955...` |
| **132474210** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `f59a9307...` |
| **132501348** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `MEGAsync.exe` | `f27f6167...` |
| **132502453** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `0d1c7f07...` |
| **132527297** | Crowdstrike: Suspicious Activity | `api.us-2.crowdstrike.com` | `UltraViewer_Service.exe` | `5e98eb79...` |
| **132499009** | Prisma SASE: Suspicious File Threat | `172.25.14.80` | `ss-widget.min.js` | `3780d6b4...` |
| **132499023** | Prisma SASE: Suspicious File Threat | `172.25.14.67` | `clientlib-site.min.js` | `915d3151...` |
| **132499745** | Prisma SASE: Suspicious File Threat | `172.25.14.80` | `scripts-QBOKETIS.js` | `88836ff7...` |
| **132578774** | Prisma SASE: Suspicious File Threat | `172.25.2.3` | `adrum22603859.js` | `9d5e305f...` |
| **132591888** | Prisma SASE: Suspicious File Threat | `172.25.6.208` | `update.exe` | `d720a22d...` |
| **132595592** | Prisma SASE: Suspicious File Threat | `172.25.6.95` | `2005.70cb3d6bf67c91a7.js` | `10be9e9a...` |
| **132596403** | Prisma SASE: Suspicious File Threat | `172.25.6.101` | `review.es.system.js` | `beeaebf2...` |
| **132599145** | Prisma SASE: Suspicious File Threat | `172.25.14.157` | `jquery.knob.js` | `0b749ee5...` |
| **132599146** | Prisma SASE: Suspicious File Threat | `172.25.14.157` | `exporting.js` | `f34ba5d7...` |
| **132599330** | Prisma SASE: Suspicious File Threat | `172.25.14.157` | `select2.min.js` | `9d020d2c...` |

---

## 3. Five-Dimensional Evidence Sufficiency Matrix

Each incident was independently evaluated across five distinct evidentiary dimensions:
1. **Detection Trigger Verification:** Did the detection rule's event pattern genuinely match?
2. **Observed Activity Verification:** Is the observed action (process launch or HTTP transfer) verified by raw logs?
3. **Authorization Assessment:** Does available evidence establish corporate IT authorization or lack thereof?
4. **Maliciousness Assessment:** Does evidence prove active adversary tradecraft, payload execution, or malware detonation?
5. **Security Outcome Assessment:** Is the final outcome (blocked, allowed, killed, active session) observable?

### Evaluation Summary:
- **CrowdStrike (10 incidents):**
  - Trigger & Activity: `SUFFICIENT`
  - Authorization: `INSUFFICIENT` (ITSM change tickets are never present in SIEM syslogs)
  - Maliciousness: `INSUFFICIENT` (Dual-use administration tools; no malware payload dropped)
  - Security Outcome: `SUFFICIENT` (Falcon EPP blocked/killed the process)
- **Prisma SASE JavaScript Assets (9 incidents):**
  - Trigger & Activity: `SUFFICIENT`
  - Authorization: `NOT_APPLICABLE` (Standard public web browsing)
  - Maliciousness: `SUFFICIENT` (Verified clean standard web assets; no malware)
  - Security Outcome: `SUFFICIENT` (Clean web browsing)
- **Prisma SASE Executable `132591888` (`update.exe`):**
  - Trigger & Activity: `SUFFICIENT`
  - Authorization: `INSUFFICIENT` (Corporate software update vs rogue download unknown)
  - Maliciousness: `INSUFFICIENT` (No WildFire sandbox detonation report available in logs)
  - Security Outcome: `INSUFFICIENT` (Host impact unknown)

---

## 4. Deliverable References

- Frozen Cohort Manifest: [FROZEN_COHORT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/FROZEN_COHORT_MANIFEST.json)
- Evidence Integrity Manifest: [EXPERIMENT_EVIDENCE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EXPERIMENT_EVIDENCE_MANIFEST.json)
- Sufficiency Matrix: [EVIDENCE_SUFFICIENCY_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EVIDENCE_SUFFICIENCY_MATRIX.json)
