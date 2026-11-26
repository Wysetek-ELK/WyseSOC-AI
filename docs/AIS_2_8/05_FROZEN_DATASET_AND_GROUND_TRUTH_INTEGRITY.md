# 05 — Frozen Dataset & Ground Truth Integrity

- **Cohort Key:** `AIS_2_6E_FROZEN_20` (preserved completely unmodified; `len=0`).
- **Ground Truth Distribution (GT-2 Single Reviewer, Not Yet GT-3 Dual-Certified):**
  - CrowdStrike (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`): **9 `TRUE_POSITIVE`**, **1 `FALSE_POSITIVE`**, **0 `INCONCLUSIVE`** (10 total)
  - Prisma SASE (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`): **0 `TRUE_POSITIVE`**, **0 `FALSE_POSITIVE`**, **10 `INCONCLUSIVE`** (10 total)
- **Disclosed Reference Limitations:**
  - Heavy cluster concentration (repeated UltraViewer/TeamViewer/TanClient/js patterns) and only 1 FP sample.
  - External human-only evidence dependencies noted in AIS 2.7 (e.g. `132501348` MEGAsync VirusTotal lookup, `132474210`, `132596403`, `132599145` telemetry reconciliation).
  - Zero ground-truth labels were altered or leaked into any prompt or runner payload.
