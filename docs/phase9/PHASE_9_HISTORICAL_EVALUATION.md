# Phase 9 — Historical Evaluation & Data Eligibility Readiness

---

## 1. Purpose & Non-Fabrication Guarantee

Phase 9 adds a deterministic **Historical Corpus Eligibility Report** (`backend/app/services/historical_eligibility_service.py`) and **time-aware / partition replay filtering** (`after_epoch`, `before_epoch`, `split_partition` in `backend/app/services/policy_simulation_service.py`) so engineering and SOC leads can assess whether historical SIEM incidents qualify for G8 empirical certification and confidence calibration **before** running evaluations.

- **Integrity Notice Enforced by API & UI:** Eligibility readiness counts identify sample size, deduplication, disputed exclusions, and missing contract fields; they **do not** fabricate or substitute empirical verdict accuracy.
- Whenever verified independent TP/FP samples are below G8 (`< 10 TP` or `< 10 FP` or rule-level minimum `< 5`) or calibration (`< 30` independent samples with both classes), the API explicitly returns `"INSUFFICIENT_DATA"` and Dashboard G (`frontend/src/components/pilot/HistoricalEligibilityPanel.tsx`) renders `INSUFFICIENT_DATA`.

---

## 2. Capabilities Implemented

| Capability | Location | Verified Behavior |
|---|---|---|
| Corpus Eligibility Report (JSON + CSV) | `GET /api/verdict-intelligence/eligibility-report`, `GET /api/pilot/eligibility-report?format=csv` | Evaluates available incidents per rule, adjudicated TP/FP, disputed investigations (`is_disputed`), insufficient evidence, ML-generated / unverified resolutions, synthetic fixtures, near-duplicate clusters, missing critical contract fields (`source_field`), and deterministic holdout partitions (`TRAIN`, `TUNING`, `CALIBRATION`, `LOCKED_TEST`). |
| Chronological & Partition Replay | `POST /api/verdict-intelligence/dry-run/evaluate` (`after_epoch`, `before_epoch`, `split_partition`) | Filters evaluation cohorts by event epoch boundaries and dataset split partition, persisting filter provenance inside replay result `claims_summary`. |
| UI Reporting & Export | `/verdict-intelligence?tab=eligibility` | Interactive filter by `rule_id`, holdout partition counters, missing required fields breakdown, G8/Calibration badges, and Bearer-authenticated JSON/CSV download. |

---

## 3. Local Repository Corpus Snapshot

Inspection of `backend/ai_verdict.db` (`docs/phase9/evidence/metrics/issue1_issue2_db_audit.json`):
- Local dev DB holds 26 incidents (`24` rows in `historical_ground_truth`), `4` rules, `8` historical evaluation runs (`validation_state`: 7 `INSUFFICIENT_DATA`, 1 `INCONCLUSIVE`), and `26` simulated heuristic incident verdicts (`"model_identifier": "simulated-heuristic-v1"`).
- Real empirical accuracy and G8 certification across production SOC data remain **`NOT_TESTED`** / **not established** until verified human-adjudicated telemetry and live Server 2 inference are executed in staging/production.

