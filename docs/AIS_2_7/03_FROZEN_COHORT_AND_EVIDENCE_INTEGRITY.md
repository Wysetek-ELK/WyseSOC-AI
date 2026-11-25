# 03 — Frozen Cohort & Evidence Integrity

**Phase:** AIS 2.7 (Workstream 3)  
**Cohort Key:** `AIS_2_6E_FROZEN_20`  
**Verified Cohort Size:** `20` (5 Priority Pilot + 15 Remaining; 10 CrowdStrike + 10 Prisma SASE)

---

## 1. Population & Priority Verification

All 20 FortiSIEM incident IDs in the specification match Server 1 PostgreSQL `BenchmarkCohortItem` rows 100%:
- **Priority 5 Pilot:** `132474210`, `132596403`, `132599145`, `132438483`, `132591888`.
- **Remaining 15:** 8 CrowdStrike (`132439932`, `132441815`, `132461358`, `132461368`, `132472498`, `132501348`, `132502453`, `132527297`) + 7 Prisma SASE (`132499009`, `132499023`, `132499745`, `132578774`, `132595592`, `132599146`, `132599330`).

---

## 2. Behavioral Clustering & Non-Independence Limitations

The 20 incidents do **not** represent 20 independent observations; they collapse into **4 behavioral clusters**:
1. **`CS_ULTRAVIEWER_Tosoh` (9 incidents):** All 9 involve `UltraViewer_Service.exe` at customer `Tosoh` across 4 hosts (`PC-TSI-DC`, `DESKTOP-E0G2R49`, `TSI-IT-002-200`, `DESKTOP-KHU6454`, `TSI-IT-002-95` — 5 distinct hosts actually: `PC-TSI-DC` x2, `DESKTOP-E0G2R49` x3, `TSI-IT-002-200` x2, `DESKTOP-KHU6454` x1, `TSI-IT-002-95` x1).
2. **`CS_MEGASYNC_WSTPL` (1 incident):** `132501348` (`MEGAsync.exe` on `DESKTOP-CQ4A60U`, customer `WSTPL`).
3. **`PRISMA_JS_Forbes_Marshall` (9 incidents):** JavaScript files (`review.es.system.js`, `jquery.knob.js`, `ss-widget.min.js`, `clientlib-site.min.*.js`, `scripts-QBOKETIS.js`, `adrum22603859.js`, `2005.*.js`, `exporting.js`, `select2.min.js`) at `Forbes_Marshall`.
4. **`PRISMA_EXE_Forbes_Marshall` (1 incident):** `132591888` (`update.exe` via `teamviewer-base` at `Forbes_Marshall`, host `172.25.6.208`).

Supporting manifests: [FROZEN_COHORT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/FROZEN_COHORT_MANIFEST.json), [INCIDENT_ID_MAPPING.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/INCIDENT_ID_MAPPING.json), [INCIDENT_EVIDENCE_HASH_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/INCIDENT_EVIDENCE_HASH_MANIFEST.json), and [DATASET_SIMILARITY_AND_CLUSTER_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/DATASET_SIMILARITY_AND_CLUSTER_MANIFEST.json).
