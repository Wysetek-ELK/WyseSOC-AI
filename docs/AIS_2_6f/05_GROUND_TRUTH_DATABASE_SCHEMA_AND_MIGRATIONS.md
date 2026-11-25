# 05 — Ground Truth Database Schema & Migrations

- **Revision**: `backend/alembic/versions/016_ground_truth_certification_and_cohort_isolation.py`
- **Tables Created**: `benchmark_cohorts`, `benchmark_cohort_items`, `benchmark_review_revisions`.
- **Table Extended**: `analyst_verdict_reviews` (15 additive columns including `benchmark_cohort_id`, `review_mode`, `is_locked`, `is_draft`, `attestation_flags`, `excluded_from_learning`, snapshot hashes).
- **Non-Destructive Guarantee**: Zero existing operational reviews, `historical_ground_truth`, or `ai_verdict` rows modified or deleted.
