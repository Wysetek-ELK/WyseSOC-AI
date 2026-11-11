# Agent Intelligence Studio 2.2 — Ground-Truth Readiness Diagnostics & ML Re-Evaluation Audit Plan

**Non-Mutation Guarantee:** Neither [`HistoricalEligibilityService`](../../backend/app/services/historical_eligibility_service.py) nor [`backend/scripts/audit_ground_truth_readiness.py`](../../backend/scripts/audit_ground_truth_readiness.py) mutates any database record (`mutated_records = 0`), historical resolution, `is_ml_generated` boolean, or `Investigation.is_independently_verified` flag.

---

## 1. Local Development Database Observed Diagnostics (`backend/ai_verdict.db`)

Executed read-only command: `cd backend; python scripts/audit_ground_truth_readiness.py` (`database_target_scheme: sqlite+aiosqlite`, `database_mutated: false`).

### Corpus Summary
| Metric | Observed Local DB Value | Notes |
| :--- | --: | :--- |
| `available_incident_count` | **`26`** | Complete local SQLite dev corpus (`earliest_epoch: 1793781975000`, `latest_epoch: 1794214585286`) |
| `verified_tp_count` | **`2`** | Independently human-eligible TPs |
| `verified_fp_count` | **`4`** | Independently human-eligible FPs |
| `eligible_independent_count` | **`6`** | Aggregate across all 4 rules (`TRAIN: 2, TUNING: 1, LOCKED_TEST: 3`) |
| `unverified_or_ml_count` | **`12`** | `HEURISTIC_OR_ML_LABEL: 12` |
| `synthetic_count` | **`6`** | `SYNTHETIC_FIXTURE_EXCLUDED: 6` |
| `duplicate_group_count` / `duplicate_excluded` | **`6`** / **`2`** | `DUPLICATE_CLUSTER_EXCLUDED: 2` |
| `disputed_count` | **`0`** | `Investigation.is_disputed == True` |
| `g8_eligibility` / `calibration_eligibility` | `ELIGIBLE` (corpus) / `INSUFFICIENT_DATA` | Aggregate `>= 5` (`6`), **every single rule `< 5`** (`3, 0, 0, 3` -> per-rule G8 `INSUFFICIENT_DATA`) |
| `total_flagged_ml_generated` | **`13`** | Stored `historical_ground_truth.is_ml_generated = 1` rows |
| `confirmed_ml_or_automated` | **`12`** | Confirmed ML/automated tokens or system actors under AIS 2.1 word-boundary detection |
| `false_positive_ml_candidates` | **`1`** | `INC-DEBUG-06` (also synthetic `SYNTHETIC_FIXTURE_EXCLUDED`, `needs_human_verification_candidates: 1`) |

### Per-Rule Local DB Readiness Breakdown
| Rule Identifier (UUID) | Available | Verified TP / FP | Eligible | Exclusion Breakdown | G8 Eligibility | Autonomous Ready Alone? |
| :--- | --: | :-: | --: | :--- | :--- | :--- |
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (`271b0831-...`) | `10` | `0 / 3` | **`3`** | `HEURISTIC_OR_ML_LABEL: 7` | `INSUFFICIENT_DATA` | **No** (`sample_threshold_alone_sufficient: false`) |
| `PH_RULE_DEBUG_FUNNEL` (`07bef27c-...`) | `6` | `0 / 0` | **`0`** | `SYNTHETIC_FIXTURE_EXCLUDED: 6` | `INSUFFICIENT_DATA` | **No** |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` (`37a7542f-...`) | `0` | `0 / 0` | **`0`** | — | `INSUFFICIENT_DATA` | **No** |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` (`b2f1f1e4-...`) | `10` | `2 / 1` | **`3`** | `HEURISTIC_OR_ML_LABEL: 5`, `DUPLICATE_CLUSTER_EXCLUDED: 2` | `INSUFFICIENT_DATA` | **No** |
| **`PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-...`)** | *Absent locally* | **`NOT VERIFIED`** | **`NOT VERIFIED`** | Remote Server 1 PostgreSQL unreachable locally | **`NOT VERIFIED`** | **No** |

*(Synthetic test coverage in `test_ais_2_2_remediation.py::test_5` additionally proves read-only detection of `RECLASSIFY_FALSE_SUBSTRING_HUMAN_VERIFIED`, `KEEP_ML_AUTOMATED`, sibling rule isolation, and `sample_threshold_alone_sufficient: false`.)*

---

## 2. Auditable Re-Evaluation Plan for Remote Production PostgreSQL (`is_ml_generated`)

Because production PostgreSQL Server 1 (2,900+ historical incidents, 34 SIEM rules) is **`NOT VERIFIED`** from the local workspace, execute the following read-only-first remediation plan during the integration validation window on Server 1:

1. **Step 1 — Read-Only Audit Run (Zero DB Writes):**
   ```powershell
   python backend/scripts/audit_ground_truth_readiness.py --output /tmp/ais_gt_readiness_server1.json
   ```
   Review `summary.ml_reevaluation_audit` and per-rule `rules[]` counts for `PH_RULE_HEAVY_TCP_HOST_SCAN` and all 34 rules.
2. **Step 2 — Inspect Candidate Reclassifications Without Promoting Blindly:**
   - `KEEP_ML_AUTOMATED`: Rows where `detect_automated_or_ml_text(...) == True` (`\bml\b`, `"Resolution set by Machine Learning"`, automated actor). Keep `is_ml_generated = True` unless an independent human investigation (`Investigation.is_independently_verified = True`) exists.
   - `RECLASSIFY_FALSE_SUBSTRING_HUMAN_VERIFIED`: Legacy rows flagged solely due to the old `"ml" in comments.lower()` substring bug (`normal`, `html`, `xml`, `yaml`, `similar`, `email`) that **already** have `Investigation.is_independently_verified = True` and an explicit TP/FP label. Eligible for approved scripted `is_ml_generated = False` backfill with `AuditLog` entries.
   - `RECLASSIFY_FALSE_SUBSTRING_NEEDS_REVIEW`: Legacy rows without ML/automated tokens that lack `Investigation.is_independently_verified = True`. Route to Human Review Queue; **do not auto-verify** or auto-promote into G8 calibration solely by clearing `is_ml_generated`.
3. **Step 3 — Governance Guardrail:**
   - Even when a rule reaches `eligible_independent_count >= 5` (`g8_eligibility == "ELIGIBLE"`), `governance_readiness.sample_threshold_alone_sufficient` remains **`false`**. Autonomous operation still requires: (1) an `APPROVED` policy version passing G1–G7, (2) a real non-simulated `OPENAI_COMPATIBLE` Gate G8 `EVALUATED_PASSED` run bound to the exact active `policy_digest` with balanced accuracy `>= 80%` and `critical_false_negatives == 0`, and (3) explicit Pilot configuration approval.
