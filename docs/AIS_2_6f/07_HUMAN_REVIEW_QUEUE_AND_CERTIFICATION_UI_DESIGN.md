# 07 — Human Review Queue & Certification UI Design

- Maintained clean single navigation structure inside `/human-review-queue` (zero extra top-level sidebar route).
- Top-level switcher cleanly separates **Operational Reviews** (with DB-wide `status_counts` aggregates across all incidents) from **Ground Truth Certification (AIS 2.6e)** (`GroundTruthCertificationPanel.tsx`).
- Priority Pilot (`X/5`) and Full Cohort (`X/20`) progress bars expose zero TP/FP class distributions prior to certification.
- Investigation drawer includes triggered rule spec + SHA-256, searchable/copyable raw logs, canonical normalized evidence, manual evidence attachment, 3 mandatory attestations, Draft/Lock controls, Conflict Adjudication panel, and collapsible Guide.
