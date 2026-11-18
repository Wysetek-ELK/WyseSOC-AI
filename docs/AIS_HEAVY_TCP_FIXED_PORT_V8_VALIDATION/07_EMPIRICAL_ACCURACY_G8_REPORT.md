# 07 — Empirical Accuracy & Gate G8 Validation Report

**Evaluation Timestamp (UTC):** `2026-11-18T16:12:16Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Empirical Accuracy Status:** **`NOT MEASURABLE`** (`0` eligible verified TP/FP evaluations; `NOT` reported as `0.0%` achieved accuracy)
**Gate G8 Status:** **`NOT PASSED / INSUFFICIENT_DATA`** (`certifying_empirical_eligible: false`)
**Production Readiness Verdict:** **`BLOCKED`** (`is_production_eligible: false`, `lifecycle_stage: LEARNING`, `is_enabled: false`)

---

## 1. Distinct Metrics Table (Queried Live from Server 1 `10021a3f`)

| # | Metric | Live Server 1 Value | Denominator / Basis | Production Threshold | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | **Model Case Confidence** | `0.0%` across 12 V7/V8 benchmark runs (`UNCALIBRATED`) | Subjective per-case LLM output (never proof of accuracy) | Must be calibrated on `>= 30` verified cases | `NOT_CALIBRATED` |
| 2 | **Verified TP/FP Accuracy** | **`NOT MEASURABLE`** (`null`) | `0 / 0` eligible verified TP/FP evaluations | `>= 95.0%` | **BLOCKED** |
| 3 | **TP Recall (Sensitivity)** | **`NOT MEASURABLE`** (`null`) | `0 / 0` verified TP cases | `>= 95.0%` | **BLOCKED** |
| 4 | **FP Precision (Auto-Closure Safety)** | **`NOT MEASURABLE`** (`null`) | `0 / 0` AI FP predictions with verified label | `>= 99.0%` | **BLOCKED** |
| 5 | **Wilson 95% Lower Bound (FP Precision)** | **`NOT MEASURABLE`** (`null`) | Requires verified AI FP denominator | `>= 96.0%` | **BLOCKED** |
| 6 | **Critical Missed TPs** | **`0`** observed (`0` eligible denominator — not proof of zero future misses) | `0 / 0` | `== 0` | `UNVERIFIED` |
| 7 | **Abstention Rate** | `100.0%` (`12/12` live runs; `6/6` V7 & `6/6` V8 exploratory replay) | All real LLM inferences executed | Monitored (safe abstention preferred over forced guesses) | **OBSERVED** |
| 8 | **Decision Coverage** | `0.0%` (`0/6` decisive TP/FP on V7 and V8) | `6` identical benchmark incidents | Improve via context upgrade + verified RAG precedents | **OBSERVED** |
| 9 | **Automation Eligibility** | **`false`** (`BLOCKED`) | G1–G7 PASS (`7/8`), G8 pending, `0/100` verified samples | All 10 empirical + governance gates PASS | **BLOCKED** |

---

## 2. Verbatim Live Server 1 Readiness Blockers (`GET /api/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c`)

Verified verbatim after deploying commit `10021a3f` (now explicitly reporting **`NOT MEASURABLE`** rather than misleading `0.0%`):

1. `Insufficient eligible verified TP/FP evaluations: 0/100 required (total reviews: 0).`
2. `Insufficient True Positive cases: 0/25 required.`
3. `Insufficient False Positive cases: 0/50 required.`
4. `Verified Rule Accuracy: NOT MEASURABLE (0 eligible evaluations; >=95.0% required).`
5. `Observed FP Precision: NOT MEASURABLE (0 AI FP evaluations; >=99.0% required).`
6. `Wilson 95% lower confidence bound: NOT MEASURABLE (>=96.0% required).`
7. `TP Recall: NOT MEASURABLE (0 verified TP evaluations; >=95.0% required).`
8. `All G1-G8 quality gates must PASS before production promotion (passed: 7/8).`

---

## 3. Gate G8 Funnel & Exclusion Breakdown (V7 Run `ca113d0a` & V8 Run `9e2ebd30`)

- **Scanned & Rule-Matched (`40498741-...`):** `6 / 6`
- **Excluded from Certifying G8 Scoring:** `6 / 6` — `exclusion_reasons: {"MISSING_ANALYST_LABEL": 6}` (`0` rule mismatches, `0` synthetic fixtures, `0` heuristic/ML labels)
- **Evaluated in Isolated Exploratory Replay (`include_unlabeled_replay=true`):** `6 / 6` real Server 2 GPU inferences (`OPENAI_COMPATIBLE`, `is_simulated: false`)
- **Partition Leakage Protection:** `HistoricalGroundTruthValidator.assign_partition()` deterministically isolates `LOCKED_TEST` evaluation records from RAG training retrieval (`test_08` verified `0` leakage).

---

## 4. Remaining Sample Requirements to Unblock G8 & Production Readiness

| Requirement | Current Live Count | Required Minimum | Deficit |
| :--- | :---: | :---: | :---: |
| Eligible Verified TP/FP Evaluations | `0` | `100` | **`100`** (max `32` rich-log incidents currently on Server 1; `>= 68` additional rich-log incidents needed) |
| Verified True Positive Cases | `0` | `25` | **`25`** |
| Verified False Positive Cases | `0` | `50` | **`50`** |
| Independent `LOCKED_TEST` Holdout Partition | `0` | Leakage-free holdout set | Must remain strictly excluded from RAG retrieval |
| G1–G8 Quality Gates Passed | `7 / 8` (G1–G7 PASS) | `8 / 8` | **G8 empirical pass on real LLM** |
