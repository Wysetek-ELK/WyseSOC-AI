# 04 — Ground Truth Taxonomy & Certification Specification

- **Tiers**: `GT0_UNREVIEWED`, `GT1_HISTORICAL_ONLY`, `IN_PROGRESS`, `GT2_SINGLE_REVIEW`, `CONFLICT_PENDING_ADJUDICATION`, `GT3_CERTIFIED`, `CERTIFIED_INCONCLUSIVE`.
- **Verdict Taxonomy**: `TRUE_POSITIVE`, `FALSE_POSITIVE`, `INCONCLUSIVE` alongside structured `detection_correctness`, `authorization_context`, `confidence_level`, and `evidence_sufficiency_status`.
- **Dual-Reviewer & Independence Invariants**: Self-approval raises `409 Conflict`; conflicting reviews move to `CONFLICT_PENDING_ADJUDICATION` requiring an independent Senior/Admin adjudicator (`403` if conflicting reviewer attempts adjudication); Admins can revise via immutable `BenchmarkReviewRevision` records.
