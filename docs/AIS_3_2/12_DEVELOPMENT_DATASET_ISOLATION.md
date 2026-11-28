# AIS 3.2 — 12: Development Dataset Isolation

`AIS32BenchmarkService.build_development_cohort` builds `AIS_3_2_DEVELOPMENT` while enforcing strict separation from `AIS_2_6E_FROZEN_20` and `AIS_3_0_INDEPENDENT_HOLDOUT_100`:
- Excludes protected `incident_db_id`, `fortisiem_incident_id`, raw evidence SHA-256 hashes, and `LearningRecord`-exposed IDs.
-Verified in `test_ais32_cohort_isolation_benchmark_metrics_and_api_rbac` (`id_overlap_with_protected = 0`, `hash_overlap_with_protected = 0`, `DEV_LABEL_MUST_NOT_LEAK` excluded from prompts). Live Server 1 cohort creation awaits Admin auth.
