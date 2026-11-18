# 07 — G8 Empirical Gate & Production Accuracy Readiness Report

**Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Verified Live Snapshot Timestamp:** `2026-11-18T16:47:10Z` (`GET /api/learning/profiles/40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Empirical Accuracy Status:** **`NOT_MEASURABLE`**  
**Production Eligibility:** **`BLOCKED` (`is_production_eligible = false`, `lifecycle_stage = LEARNING`)**

---

## 1. Current Live G1–G8 & Learning Profile Status

| Governance Dimension | Current Live Value | Required Threshold | Status |
| :--- | :--- | :--- | :---: |
| **G1–G7 Structural Quality Gates (DRAFT v8)** | `85.0 / 85.0` (`7/7` passed, `0` blockers) | `7/7` passed | **PASS** |
| **G8 Empirical Simulation & Regression Gate** | `0.0 / 15.0` (`INSUFFICIENT_DATA`, `0` verified GT cases) | `>= 5` verified GT cases + no critical regression | **PENDING / BLOCKED** |
| **Gates Passed Total** | **`7 / 8`** | **`8 / 8`** | **BLOCKED** |
| **Total Analyst Reviews** | **`0`** | `>= 100` eligible TP/FP | **BLOCKED** |
| **Eligible Verified TP/FP Evaluations** | **`0 / 100`** | `>= 100` | **BLOCKED** |
| **Verified True Positive (`TP`) Count** | **`0 / 25`** | `>= 25` | **BLOCKED** |
| **Verified False Positive (`FP`) Count** | **`0 / 50`** | `>= 50` | **BLOCKED** |
| **Verified Rule Accuracy** | **`NOT MEASURABLE`** (`null`) | `>= 95.0%` | **BLOCKED** |
| **Observed FP Precision** | **`NOT MEASURABLE`** (`null`) | `>= 99.0%` | **BLOCKED** |
| **Wilson 95% Lower Confidence Bound (FP)** | **`NOT MEASURABLE`** (`null`) | `>= 96.0%` | **BLOCKED** |
| **TP Recall** | **`NOT MEASURABLE`** (`null`) | `>= 95.0%` | **BLOCKED** |
| **Critical Missed TPs (`AI FP` vs `Human TP`)** | `0` observed among `0` verified cases (**NOT proof of safety!**) | `0` across `>= 25` verified TPs | **UNVERIFIED** |
| **Unresolved Analyst Disputes** | `0` | `0` | **PASS** |
| **Active Approved Policy** | **v7** (`d79fb576`, `APPROVED`) | Approved active | **PRESERVED** |
| **Candidate Policy** | **v8** (`20d4f788`, `DRAFT`) | Must remain DRAFT until G8 + Admin | **PRESERVED** |
| **Automation Policy (`is_enabled`)** | **`false`** (`daily_closure_limit = 50`, `current_day_closure_count = 0`) | Disabled until promoted | **SAFE / DISABLED** |

---

## 2. Exact Live Blocking Reasons Reported by AIS 2.0

Verbatim `eligibility_reasons` from `GET /api/learning/profiles/40498741-ee6b-4a71-9101-0d6d3f77154c`:
1. `Insufficient eligible verified TP/FP evaluations: 0/100 required (total reviews: 0).`
2. `Insufficient True Positive cases: 0/25 required.`
3. `Insufficient False Positive cases: 0/50 required.`
4. `Verified Rule Accuracy: NOT MEASURABLE (0 eligible evaluations; >=95.0% required).`
5. `Observed FP Precision: NOT MEASURABLE (0 AI FP evaluations; >=99.0% required).`
6. `Wilson 95% lower confidence bound: NOT MEASURABLE (>=96.0% required).`
7. `TP Recall: NOT MEASURABLE (0 verified TP evaluations; >=95.0% required).`
8. `All G1-G8 quality gates must PASS before production promotion (passed: 7/8).`

---

## 3. End-to-End Learning & Anti-Leakage Architecture Verification

All learning, adjudication, isolation, and reversal controls remain verified via automated regression suite (`backend/tests/test_ais_heavy_tcp_e2e.py` + `backend/tests/test_rule_learning_platform.py`):

| Control | Verification Proof | Result |
| :--- | :--- | :---: |
| **Double-Blind Anti-Anchoring** | Live `GET /api/learning/pending-reviews` (`blind_mode_active = true`, `69` pending, no AI verdict exposed) + `test_02` | **VERIFIED** |
| **Tenant Isolation in RAG Precedents** | `test_03` confirms tenant-scoped precedent retrieval never leaks `Demo-SOC` into `GDC_NOC` or vice versa | **VERIFIED** |
| **`LOCKED_TEST` Holdout Anti-Leakage** | `test_08` verifies `LOCKED_TEST` incidents are strictly excluded from RAG retrieval and training precedent indexing | **VERIFIED** |
| **Label-Correction Reversal Integrity** | `test_10` verifies correcting a prior analyst label cleanly reverses prior confusion-matrix counters & updates RAG eligibility without double-counting | **VERIFIED** |
| **Dispute Adjudication Workflow** | `test_rule_learning_platform.py` verifies `DISPUTED` items block readiness until Senior/Admin adjudication resolves them | **VERIFIED** |
| **No Fake `0.0%` Accuracy Display** | Live `/api/learning/profiles/...` returns `null` + `accuracy_status = "NOT_MEASURABLE"`, and live benchmark `a95cd268` returns `metric_status = "NOT_CALCULABLE"` | **VERIFIED** |
| **No Fabricated Safety from `0` Missed TPs** | `0` critical missed TPs among `0` verified evaluations is explicitly marked **UNVERIFIED**; promotion remains hard-blocked until `>= 25` verified TPs and `>= 50` verified FPs exist | **VERIFIED** |

---

## 4. What Must Happen to Pass G8 and Reach Production Readiness

1. **Collect Real Human Ground Truth:** SOC analysts complete double-blind reviews starting with Priority A (4 mixed-scope incidents) and Priority B (28 external HTTPS/Browsing incidents) — plus ongoing live incidents as they arrive to reach `>= 100` verified cases (`>= 25` TP, `>= 50` FP).
2. **Fix 7B Factual Inversion Before Re-Approving Policy (V8.2):** Address the observed `bidirectional_sessions=100` vs `"predominantly unanswered probes"` prose inversion (see `05_REAL_LLM_REBENCHMARK.md` and `10_FINAL_ACCEPTANCE_AND_NEXT_ACTIONS.md`) via deterministic claim-prose consistency checks and verified RAG precedents.
3. **Run Certifying Holdout G8 Simulation on `LOCKED_TEST`:** Execute real local LLM simulation (`is_simulated = false`) on verified ground-truth cases and confirm all 10 readiness gates pass (`accuracy >= 95%`, `FP precision >= 99%`, `Wilson LCB >= 96%`, `TP recall >= 95%`, `0` critical missed TPs, `0` unresolved disputes, `G1–G8 = 8/8`).
4. **Explicit Admin Approval:** Only after G8 passes may an Admin approve a candidate policy version and separately authorize controlled automation (`FALSE_POSITIVE` only, `min_trust_score >= 8`, daily cap enforced).
