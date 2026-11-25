# 10 — Offline Benchmark Readiness & Token Audit

- Fixed `EmpiricalBenchmarkHarness._lookup_approved_prompt_version` fallback UUIDs/versions (`bd751fac...` v1 CS and `8ae7beaa...` v1 Prisma SASE).
- Added `EmpiricalBenchmarkHarness.load_certified_ground_truth_cohort(...)` consuming strictly `GT3_CERTIFIED` TP/FP from PostgreSQL/SQLite, keeping `CERTIFIED_INCONCLUSIVE` separated (`inconclusive_ground_truth_count`), excluding `GT0`/`GT1`/`CONFLICT`, and gating `GT2` behind explicit `include_gt2_exploratory=True`.
- **GPU Server 2 Compliance**: Zero live GPU inference calls executed during AIS 2.6f.
