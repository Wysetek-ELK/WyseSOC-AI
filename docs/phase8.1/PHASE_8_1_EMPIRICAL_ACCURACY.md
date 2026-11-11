# Phase 8.1 Empirical Accuracy & Calibration Report (Stage 7)

- **Status:** **`PARTIAL / HONESTLY UNCALIBRATED`** *(Leakage=0, calibration gating mathematically verified; real empirical accuracy & calibration withheld because verified non-synthetic balanced samples < 30 per rule and live Server 2 replay is unreachable)*
- **Primary Evidence:** [`stage7_accuracy_calibration.json`](./evidence/historical-replay/stage7_accuracy_calibration.json)

## 1. Per-Rule Historical Simulation & Calibration Measurements

| Rule Code | Policy Version Status | Scanned | Matched | Verified Eligible | ML Excluded | Simulation Status | Decisive Coverage | Balanced Accuracy | Calibration Status |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `APPROVED` (v1) | 26 | 10 | 3 (`0 TP / 3 FP`) | 7 | `INSUFFICIENT_DATA` | `0.0%` | `null` | `NOT_CALIBRATED` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `APPROVED` (v1) | 26 | 10 | 5 (`4 TP / 1 FP`) | 5 | `INCONCLUSIVE` | `0.0%` | `null` | `NOT_CALIBRATED` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `DRAFT` (v2) | 26 | 0 | 0 | 0 | `INSUFFICIENT_DATA` | `0.0%` | `null` | `NOT_CALIBRATED` |
| `PH_RULE_DEBUG_FUNNEL` *(synthetic)* | `DRAFT` (v1) | 26 | 6 | 2 (`1 TP / 1 FP`) | 1 | `INSUFFICIENT_DATA` | `0.0%` | `null` | `NOT_CALIBRATED` |

## 2. Calibration Gate Enforcement Analysis

Per [`CalibrationEvaluator.evaluate_calibration`](../../backend/app/services/calibration_evaluator.py):
- Empirical calibration (`ECE`, `Brier Score`, `CALIBRATED` state) is strictly withheld unless **both** `sample_count >= 30` decisive verified cases **and** `min(TP, FP) >= 3` per class.
- **Why Honest Empirical Accuracy Is Currently Undefined:**
  1. Offline simulation uses deterministic/mock contracts without live Server 2 LLM weights (`decision_coverage = 0.0%`).
  2. Even with live Server 2 online, only `8` non-synthetic human-adjudicated SIEM incidents exist across the entire local snapshot (`3` CS `FP`-only, `5` Prisma SASE `4 TP / 1 FP` collapsed into `3` unique event episodes), leaving a shortfall of **25–30 independent analyst-labeled incidents per rule**.
  3. Therefore, claims of empirical precision, recall, or Brier/ECE calibration are explicitly withheld (`null`).

