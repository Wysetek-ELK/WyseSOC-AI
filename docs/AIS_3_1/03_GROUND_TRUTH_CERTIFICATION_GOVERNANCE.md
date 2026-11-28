# AIS 3.1 — Workstream 3: GT-2 vs GT-3 Certification Governance

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Machine-Readable Evidence:** `docs/AIS_3_1/CERTIFICATION_GATE_MATRIX.json`

---

## 1. Certification State Machine Requirements

Implemented in `backend/app/services/ground_truth_certification_service.py`:

| Certification State | Code Constant | Exact Transition & Governance Requirement | Current Cohort Count |
|---|---|---|---:|
| **GT-0** | `GT0_UNREVIEWED` | 0 locked `BENCHMARK_CERTIFICATION` reviews and no historical label. | **0** |
| **GT-1** | `GT1_HISTORICAL_ONLY` | Non-empty historical SIEM resolution metadata present, 0 locked human certification reviews. | **0** |
| **GT-2** | `GT2_SINGLE_REVIEW` | Exactly **1** locked independent human review (`reviewer_id` unique). Provisional benchmark eligible under `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` only. | **100** |
| **GT-3** | `GT3_CERTIFIED` | **2 or more** distinct authorized reviewers (`reviewer_id` different from reviewer 1), both `is_locked=True`, and agreeing on conclusive verdict (`TRUE_POSITIVE` or `FALSE_POSITIVE`), OR conflict formally resolved by adjudication. | **0** |
| **Inconclusive Certified** | `CERTIFIED_INCONCLUSIVE` | 2+ distinct locked reviewers agreeing on `INCONCLUSIVE`. | **0** |
| **Conflict** | `CONFLICT_PENDING_ADJUDICATION` | 2+ distinct locked reviewers with disagreeing verdicts; requires separate adjudicator resolution. | **0** |
| **Exposure Risk** | `exposure_risk_flag` | Tracks whether historical/AI/RAG/prompt signals exist; separated in AIS 3.1 from strict `CONFIRMED_EXPOSURE` quarantine. | **0 Confirmed / 75 Masked / 25 Clean** |

---

## 2. Root Cause Why All 100 Holdout Incidents Remain at `GT2_SINGLE_REVIEW`

Backend database audit confirms that all `100/100` incidents in `AIS_3_0_INDEPENDENT_HOLDOUT_100` have **strictly 1 locked human review**, all submitted by `admin` (`Reviewers locked: 1/2`), and `0` second-reviewer submissions. Therefore:

- The UI (`GT2_SINGLE_REVIEW`, `GT-3 Certified: 0`) accurately reflects genuine database state — there is **no certification state-machine bug** preventing GT-3 promotion.
- Self-review by `admin` a second time is explicitly prohibited by backend service logic (`"Reviewer has already submitted a locked review"` / `different_reviewer_required`) and AIS governance rules.

---

## 3. Mandatory Governance Decision Branch Executed: Branch B

Per Workstream 3 **Branch B ("Only one valid independent reviewer exists")** and AIS 2.8 / 2.9 precedent:

1. **Retain `GT2_SINGLE_REVIEW`:** Zero fake or duplicate second reviews are created; GT-3 policy requirements remain untouched.
2. **Execute Provisional Benchmark:** `AIS31BenchmarkService.create_or_resume_run` automatically tags any run on non-GT3 cohorts as `benchmark_grade = "PROVISIONAL_SINGLE_REVIEW_BENCHMARK"` (distinct from `"CERTIFIED_GT3_BENCHMARK"`).
3. **Second-Reviewer Readiness Maintained (`Branch C` Workflow Active):** Any distinct authorized human analyst logging into `/human-review-queue` receives a clean, double-blind view of each GT-2 incident:
   - First reviewer's (`admin`) verdict and notes are hidden.
   - Historical SIEM verdict and operational `ai_verdict` remain masked under `BLIND_ENFORCED`.
   - Frozen factual evidence and `INCONCLUSIVE` adjudication support remain intact so a second human reviewer can certify the cohort to `GT-3` asynchronously without repeating `admin`'s 100 reviews.
