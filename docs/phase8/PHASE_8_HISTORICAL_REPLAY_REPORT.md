# Phase 8 Historical Ground Truth & Empirical Replay Report

**Stage Covered:** Stage 5 (Historical Replay, Ground-Truth Hygiene, Leakage Audit & Calibration)
**Execution Script:** [`scripts/run_phase8_empirical_validation.py`](../../scripts/run_phase8_empirical_validation.py)
**Raw Metrics Output:** [`stage5_historical_replay.json`](./evidence/metrics/stage5_historical_replay.json)

## 1. Corpus Ground-Truth Composition & Leakage Audit

Cloning `backend/ai_verdict.db` into an isolated Alembic-upgraded (`007_distributed_locks`) temporary database yielded **26 historical incidents** (`24` `HistoricalGroundTruth` records) and deterministically partitioned them into `TRAIN: 15`, `LOCKED_TEST: 3`, `CALIBRATION: 4`, and `TUNING: 4` (`0` duplicate payload clusters):

- **Human-Adjudicated Non-ML Ground Truth (`11` rows):** `5` `VERIFIED_TP`, `5` `VERIFIED_FP`, `1` `UNVERIFIED` (`raw="Under Investigation"`).
- **ML-Generated Labels Excluded (`13` rows):** `7` `ml=True | raw="True Positive"`, `6` `ml=True | raw="False Positive"` -> strictly adjudicated `UNVERIFIED` (`is_eligible_for_evaluation=False`), preventing circular self-evaluation.

### Leakage Audit Discovery & Remediation (`P8-DEF-05`)

Initial Phase 8 payload auditing revealed **`19 / 26` incidents leaking ground-truth fields** (`clearedReason`, `clearedUser`, `comments`, nested structures) through shallow case-sensitive allowlist checks in [`HistoricalGroundTruthValidator`](../../backend/app/services/historical_ground_truth_validator.py).

- **Remediation:** Replaced shallow `.pop()` stripping with recursive `_deep_strip_leakage()` matching case- and punctuation-normalized keys across nested dicts/lists, and expanded [`FORBIDDEN_GROUND_TRUTH_KEYS`](../../backend/app/services/model_payload_allowlist.py).
- **Post-Fix Re-Audit:** `checked_incidents=26`, **`leaked_cases_count=0`**, **`leakage_free=true`**.

## 2. Empirical Replay Outcomes & Unbalanced Calibration Gating

Due to offline Server 2 GPU inference, [`PolicySimulationService`](../../backend/app/services/policy_simulation_service.py) executed deterministic replay in `SIMULATED` mode:

| Rule ID | Policy Status | Matched / Eligible GT | Simulation Status | Decision Coverage | Abstention Rate | Calibration Status |
|---|---|---:|---|---:|---:|---|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `APPROVED` | `10` / `3` (`3` FP, `0` TP) | `INSUFFICIENT_DATA` | `0.0%` | `100.0%` | `NOT_CALIBRATED` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `APPROVED` | `10` / `5` (`4` TP, `1` FP) | `INCONCLUSIVE` | `0.0%` | `100.0%` | `NOT_CALIBRATED` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `DRAFT` | `0` / `0` | `INSUFFICIENT_DATA` | `0.0%` | `0.0%` | `NOT_CALIBRATED` |
| `PH_RULE_DEBUG_FUNNEL` | `DRAFT` | `6` / `2` (`1` TP, `1` FP) | `INSUFFICIENT_DATA` | `0.0%` | `100.0%` | `NOT_CALIBRATED` |

## 3. Remediated Replay Bugs Verification

1. **Calibration Lookup Crash (`P8-DEF-04`)**: Calling nonexistent `adjudicate_ground_truth_label()` previously threw runtime errors and bypassed `CalibrationEvaluator` single-class checks when `gt_cases >= 30`. Confirmed fixed in [`test_phase8_calibration_stats_and_unbalanced_gating`](../../backend/tests/test_phase8_integration.py): single-class sets (`35` TP, `0` FP) accurately remain `is_calibrated=False` / `NOT_CALIBRATED`, while balanced non-ML sets calibrate properly and ML rows are excluded.
2. **Honest Non-Fabrication**: `overall_accuracy`, `precision`, `recall`, `ece`, and `brier_score` all return `null` when zero decisive predictions occur—no fabricated accuracy values were emitted.

