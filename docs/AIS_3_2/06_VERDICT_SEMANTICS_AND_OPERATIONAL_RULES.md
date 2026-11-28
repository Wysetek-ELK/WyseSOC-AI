# AIS 3.2 — 06: Verdict Semantics & Operational Rules

Implemented `VerdictSemanticsEngine` (`backend/app/services/verdict_semantics_engine.py`):
- Separates `detection_validity` (`CONFIRMED`/`NOT_CONFIRMED`/`UNKNOWN`), `activity_characterization` (`MALICIOUS`/`SUSPICIOUS`/`BENIGN_AUTHORIZED`/`BENIGN_UNAUTHORIZED`/`OPERATIONAL_ISSUE`/`UNKNOWN`), `authorization_status` (`VERIFIED_AUTHORIZED`/`VERIFIED_UNAUTHORIZED`/`UNKNOWN`/`NOT_APPLICABLE`), and `operational_impact`.
- Genuine collector/logging outages evaluate as `TRUE_POSITIVE` (`OPERATIONAL_ISSUE`) unless explained by verified maintenance/recovery. Semantic mappings remain `PROVISIONAL` pending formal SOC sign-off.
