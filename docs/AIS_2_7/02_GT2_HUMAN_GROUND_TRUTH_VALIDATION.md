# 02 — GT-2 Human Ground Truth Validation

**Phase:** AIS 2.7 (Workstream 2)  
**Cohort:** `AIS_2_6E_FROZEN_20` (20 incidents)  
**Ground Truth Level:** **GT-2 (Single Independent Locked Review — Exploratory Benchmark Only)**  
**GT-3 Dual-Reviewer Certified:** `0 / 20` (NOT production-certified)

---

## 1. Verified Label Distribution (Server 1 PostgreSQL)

Retrieved directly from `/api/ground-truth/cohorts/AIS_2_6E_FROZEN_20/queue` and `/incidents/{id}` on `172.26.41.240`:

| Vendor / Rule | Total | TRUE_POSITIVE | FALSE_POSITIVE | INCONCLUSIVE | Binary Eligible |
|---|---:|---:|---:|---:|---:|
| **CrowdStrike** (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | 10 | 9 | 1 | 0 | 10 |
| **Prisma SASE** (`Prisma_SASE_Suspicious_File_Threat_Detection_`) | 10 | 0 | 0 | 10 | 0 |
| **Total Cohort** | **20** | **9** | **1** | **10** | **10** |

- **Reviewer:** `admin` (`20 / 20` locked, `0` drafts, `0` conflicts, `0` `GT-0/GT-1`).
- **Critical Evaluation Constraint:** Prisma SASE has **0** binary TP/FP labels (all 10 are `INCONCLUSIVE`). The entire binary TP/FP subset (`N = 10`) consists of 9 near-duplicate `UltraViewer_Service.exe` TP alerts (`Tosoh`) and 1 `MEGAsync.exe` FP alert (`132501348`, `WSTPL`).

---

## 2. Human Review Quality & Consistency Findings (Original Labels Preserved)

1. **`132474210` Metadata Slip (Flagged):** Locked verdict is `TRUE_POSITIVE` with rationale stating CrowdStrike rule is configured to block UltraViewer and killed the process, but `authorization_context` dropdown was set to `AUTHORIZED`. Original locked label `TRUE_POSITIVE` is preserved.
2. **`132596403` & `132599145` Metadata Slip (Flagged):** Locked verdict is `INCONCLUSIVE` with rationale stating raw logs lack file hash and complete URL, but `evidence_sufficiency_status` was set to `SUFFICIENT` (unlike the other 8 Prisma SASE reviews marked `INSUFFICIENT`). Original locked labels are preserved.
3. **`132501348` (`MEGAsync.exe`) External Evidence Dependency (Flagged):** Rationale explicitly states *"the executable hash was checked and found to be clean, with no known malicious reputation"* and begins with *"Closure Reason: False Positive (FP)"*. No external hash reputation lookup is provided to the LLM.
4. **Structured Evidence References:** All 20 reviews have `evidence_references = []` and `additional_evidence = []`.

---

## 3. Exposure-Risk & Independence Assessment

All 20 items carry `exposure_risk_flag = true` on Server 1 due to pre-existing operational `ai_verdict` records, historical/ML `HistoricalGroundTruth` rows, legacy `[AI Verdict]` notes in `Investigation`, and 20 matching `LearningRecord` rows. However:
- During GT-2 submission, blind-review APIs masked AI verdicts, historical labels, and handover notes.
- Comparing locked GT-2 verdicts against `fixtures/Incident json.zip` historical resolutions shows the human reviewer **changed the verdict on 16 of 20 incidents** (5/9 UltraViewer changed FP→TP, 1/1 MEGAsync changed TP→FP, 10/10 Prisma SASE changed TP/FP→INCONCLUSIVE).
- Potential prior exposure of the `admin` account to operational views cannot be fully ruled out until an independent second analyst completes GT-3.

Reference manifests saved to [GROUND_TRUTH_REFERENCE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GROUND_TRUTH_REFERENCE_MANIFEST.json), [GROUND_TRUTH_LABEL_DISTRIBUTION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GROUND_TRUTH_LABEL_DISTRIBUTION.json), [GROUND_TRUTH_ELIGIBILITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GROUND_TRUTH_ELIGIBILITY_MANIFEST.json), and [REVIEWER_EXPOSURE_RISK_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/REVIEWER_EXPOSURE_RISK_REGISTER.json).
