# 05 — Empirical Accuracy & 95% Production Readiness Validation

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` / `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Evaluation Timestamp (UTC):** `2026-11-18T14:52:06Z`
**Live Production Readiness Verdict:** **`PRODUCTION READINESS BLOCKED`** (`is_production_eligible: false`)

---

## 1. Separation of the Three Distinct Metrics

AIS 2.0 strictly separates and exposes three non-interchangeable metrics in both backend (`RuleLearningService`, `/api/learning/rules/{rule_id}`) and frontend ([RuleLearningDashboard.tsx](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/learning/RuleLearningDashboard.tsx)):

| Metric | Definition | Live Server 1 Value (`40498741-...`) | Production Promotion Requirement |
| :--- | :--- | :--- | :--- |
| **1. AI Case Confidence** | Raw per-incident model subjective score (`0–100%`), explicitly uncalibrated until `>= 30` verified cases (`trust_score` capped at `6/10` while `UNCALIBRATED`). | `0.0%` on 4 abstained live runs (`calibration_status: NOT_CALIBRATED`, `historical_sample_count: 0`) | Never treated as proof of empirical accuracy |
| **2. Verified Rule Accuracy** | `(Agreed TP + Agreed FP) / All Eligible Verified TP & FP Evaluations` (excludes `INSUFFICIENT_EVIDENCE` and unresolved `DISPUTED` cases). | **`null`** (`0 / 0` eligible verified evaluations) | **`>= 95.0%`** across **`>= 100`** eligible independent evaluations (`>= 25` TP, `>= 50` FP) |
| **3. Automation Safety (FP Auto-Closure Precision)** | `Agreed FP / (Agreed FP + Critical Missed TP)` plus Wilson 95% lower confidence bound, TP recall, abstention rate, coverage, and false-alarm rate. | FP Precision: **`null`**, Wilson 95% LB: **`null`**, TP Recall: **`null`**, Critical Missed TPs: **`0`**, Abstention Rate: **`100.0%`** (`12/12`), Coverage: **`0.0%`**, False-Alarm Rate: **`0.0%`** | FP Precision **`>= 99.0%`**, Wilson 95% LB **`>= 96.0%`**, TP Recall **`>= 95.0%`**, Critical Missed TPs **`== 0`** |

---

## 2. Live Server 1 Empirical Confusion Matrix & Gate Status

Queried verbatim from `GET /api/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c`:

| Confusion Matrix Cell | Count |
| :--- | :---: |
| `agreed_tp` (AI TP / Analyst TP) | `0` |
| `agreed_fp` (AI FP / Analyst FP) | `0` |
| `ai_false_alarm` (AI TP / Analyst FP) | `0` |
| `critical_missed_tp` (AI FP / Analyst TP) | `0` |
| `abstained_resolved` (AI Abstained / Analyst Resolved) | `0` |
| `disputed` (Unresolved Inter-Analyst Dispute) | `0` |
| **Total Eligible TP/FP Evaluations** | **`0`** |
| **Total Real Canonical Incidents Available on Server 1** | **`69`** (`32` rich FortiGate logs + `37` header-only) |

---

## 3. Verbatim Live Server 1 Readiness Blockers (8 Active Blockers)

The live governance engine truthfully blocks production promotion and reports all **8 active blockers**:

1. `Insufficient eligible verified TP/FP evaluations: 0/100 required (total reviews: 0).`
2. `Insufficient True Positive cases: 0/25 required.`
3. `Insufficient False Positive cases: 0/50 required.`
4. `Verified Rule Accuracy (0.0%) below requirement (95.0%).`
5. `Observed FP Precision (0.0%) below requirement (99.0%).`
6. `Wilson 95% lower confidence bound (0.0%) below safety threshold (96.0%).`
7. `TP Recall (0.0%) below requirement (95.0%).`
8. `All G1-G8 quality gates must PASS before production promotion (passed: 7/8).`

---

## 4. Statistical & Data-Integrity Honesty Statement

- **Why Production Readiness Is Blocked:** Server 1 currently holds **69 real canonical incidents** for `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` (`41` in `GDC_NOC`, `28` in `Demo-SOC`), of which **32** contain rich raw FortiGate logs and **37** are header-only, with **0 independent SOC analyst ground-truth verdicts**. Even if every existing incident on Server 1 were independently reviewed today, `69 < 100` remains below the `100`-sample minimum statistical floor (and `32` rich-log incidents are insufficient to establish both `>= 25` TP and `>= 50` FP cases).
- **Zero Threshold Weakening & Zero Fabrication:** No synthetic incidents or fabricated analyst reviews were inserted into Server 1 PostgreSQL, and none of the statistical gates (`95%` accuracy, `99%` FP precision, `96%` Wilson LB, `95%` TP recall, `0` missed TPs, `>= 100` samples, G1–G8) were relaxed.
- **Software Gate Enforcement Verified:** Automated integration test `test_04_empirical_95_99_zero_missed_tp_and_separation_of_duties` in [test_ais_heavy_tcp_e2e.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_ais_heavy_tcp_e2e.py) proved on isolated in-memory SQLite that:
  - `41/100` samples → **BLOCKED**
  - `150` samples with `1` critical missed TP (even at `99.3%` accuracy) → **BLOCKED**
  - `150` samples (`50` TP, `100` FP, `0` missed TP, `98.7%` accuracy, `100%` FP precision, Wilson LB `>= 96.3%`, G1–G8 PASS) → **ELIGIBLE**
- **Data Partitioning & Leakage Prevention:** `HistoricalGroundTruthValidator.assign_partition()` deterministically separates `LOCKED_TEST` evaluation records from training/RAG retrieval; `test_08` verified `0` `LOCKED_TEST` records leak into `VerifiedSemanticRetrievalService`.
