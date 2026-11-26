# 11 — Fresh Multi-Rule Holdout Preparation (`AIS_3_0_INDEPENDENT_HOLDOUT_100`)

- Seeded and verified `AIS_3_0_INDEPENDENT_HOLDOUT_100` via `/api/ground-truth/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/ensure` and `/api/ground-truth/holdout-readiness`:
  - **Count**: `100 / 100` (`shortfall=0`)
  - **Distinct Rule Families**: `30` non-CrowdStrike/non-Prisma FortiSIEM rules
  - **Overlap with Frozen 20**: `0` (`zero_overlap_with_frozen=true`)
  - **Certification Status**: `100/100 GT0_UNREVIEWED`, `0/100` AI benchmark verdicts run, excluded from RAG/learning.
