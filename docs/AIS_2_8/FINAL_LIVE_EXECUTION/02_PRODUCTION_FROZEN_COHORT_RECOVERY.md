# 02 — Production Frozen Cohort Recovery (`AIS_2_6E_FROZEN_20`)

- **Authoritative Source**: Server 1 PostgreSQL via authenticated `/api/ground-truth/cohorts/AIS_2_6E_FROZEN_20` (local snapshot saved in restricted store `C:\Users\amits\OneDrive\Documents\SOC-AI-Agent\scratch\s1_frozen_cohort_full.json`).
- **Recovered Counts (Calculated Independently from Locked Rows)**:
  - **Total Unique Incidents**: `20 / 20`
  - **CrowdStrike (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)**: `TRUE_POSITIVE=9`, `FALSE_POSITIVE=1`, `INCONCLUSIVE=0`
  - **Prisma SASE (`PH_RULE_PRISMA_SASE_*`)**: `TRUE_POSITIVE=0`, `FALSE_POSITIVE=0`, `INCONCLUSIVE=10`
  - **Total Distribution**: `{'TRUE_POSITIVE': 9, 'FALSE_POSITIVE': 1, 'INCONCLUSIVE': 10}`
- **Locked GT-2 Reviews**: `20/20` locked, `20/20` `GT2_SINGLE_REVIEW`, `0/20` `GT3_CERTIFIED`.
- **Historical Exposure Risk Flagged**: `20/20` items (`blind_status=BLIND_ENFORCED`, historical labels and legacy `[AI Verdict]` notes sanitized from prompts).
