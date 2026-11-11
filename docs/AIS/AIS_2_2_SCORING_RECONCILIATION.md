# Agent Intelligence Studio 2.2 — G1–G8 Scoring & Export Reconciliation (`AIS-F05` & `AIS-F06`)

---

## 1. Root Defect Reconciled (`AIS-F05`)

Under `PolicyQualityValidator` `v2.0.0`, individual gate `max_score` values summed to **`105` (G1–G7)** and **`120` (G1–G8)** because both **G1 (`20`)** and **G2 (`20`)** mapped into the single 20-point `detection_semantics` bucket while `score_breakdown` capped the structural denominator at `85.0` (`85 + 15 = 100`). As a result, a policy earning `G1=16`, `G2=20`, `G3=20`, `G4=10`, `G5=10`, `G6=15`, `G7=10`, `G8=0` displayed gate card points summing to **`101/105`** alongside an overall quality score of **`81/100`** (`81 / 85 = 95.3%`).

---

## 2. Versioned Reconciled Scoring Model (`v2.2.0` vs Legacy `v2.0.0`)

`PolicyQualityValidator` now defaults to `VALIDATOR_VERSION = "v2.2.0"` while explicitly supporting `validator_version="v2.0.0"` for legacy regression verification:

| Gate | Gate Title | `v2.0.0` `max_score` | `v2.2.0` `max_score` | `score_breakdown` Bucket | `v2.2.0` Scoring Rule |
| :-: | :--- | --: | --: | :--- | :--- |
| **G1** | Rule Definition Integrity | `20.0` | **`10.0`** | `detection_semantics` (10 of 20) | Base `10.0`; `INCOMPLETE`/`UNKNOWN` `-5.0` (cap `5.0`); `AUTO_SYNCED` `-2.0`; `HEURISTIC_PARSER` `-3.0`; runtime counter warning `-2.0`; invented S3 threshold `-4.0`. |
| **G2** | Detection Archetype Relevance | `20.0` | **`10.0`** | `detection_semantics` (10 of 20) | `PASSED = 10.0`, `WARNING = 5.0` (`UNKNOWN` / inadequate telemetry), `FAILED = 0.0` (archetype relevance mismatch). Zero cross-gate overwriting. |
| **G3** | Evidence Contract Feasibility | `20.0` | `20.0` | `evidence_contract` (`20.0`) | Base `20.0`; contract missing `0.0`; 0 critical fields `-5.0`; unmapped mandatory field `-4.0` each; unsupported demand `-3.0` each (cap `-6.0`). |
| **G4** | TP Criteria Validity | `10.0` | `10.0` | `tp_fp_criteria` (10 of 20) | Base `10.0`; too brief (`<20` chars) `0.0`; non-objective/artifact mismatch `-3.0` each. |
| **G5** | FP Criteria & Benign Assumptions | `10.0` | `10.0` | `tp_fp_criteria` (10 of 20) | Base `10.0`; blanket RFC-1918/loopback benign assumption or hardcoded confidence range `0.0` (`FAILED`); brief `<20` chars `-2.0`. |
| **G6** | Abstention & Escalation Safety | `15.0` | `15.0` | `abstention_escalation` (`15.0`) | Base `15.0`; missing abstention `-8.0`; missing `REQUIRES_ATTENTION`/`abstain` `-3.0`; minimal escalation `-4.0`; unsafe RFC-1918 escalation `-5.0`; un-gated isolation `-2.0`. |
| **G7** | Internal Policy & Contract Consistency | `10.0` | `10.0` | `internal_consistency` (`10.0`) | Base `10.0`; missing S4 with critical fields `0.0`; omitted critical field `-1.0` each; TP==FP self-contradiction `0.0`. |
| **G8** | Simulation & Regression Validation | `15.0` | `15.0` | `historical_simulation` (`15.0`) | **Must pass with non-simulated `OPENAI_COMPATIBLE` on exact `policy_digest` (`15.0`)**; simulated, `<5` verified cases, missing, stale, or inconclusive `= 0.0` (`WARNING`); regression `= 0.0` (`FAILED`). |
| **Totals** | **G1–G7 Structural / G1–G8 Overall** | **`105` / `120`** *(mismatched)* | **`85.0` / `100.0`** | **Exact `85.0 + 15.0 = 100.0`** | **`sum(G1..G8 scores) == sum(score_breakdown) == quality_score`** on every assessment. |

### Worked Example (`PH_RULE_HEAVY_TCP_HOST_SCAN` with G1 Runtime-Counter Warning Only, Pre-G8)
- **v2.0.0 (Legacy):** `G1=16/20, G2=20/20, G3=20/20, G4=10/10, G5=10/10, G6=15/15, G7=10/10, G8=0/15` -> card sum `101/120`, `structural_raw = 81/85 (95.3%)`, `quality_score = 81.0`.
- **v2.2.0 (Current):** `G1=8/10, G2=10/10, G3=20/20, G4=10/10, G5=10/10, G6=15/15, G7=10/10, G8=0/15` -> card sum **`83/100`**, `detection_semantics = 18.0/20.0`, `structural_raw_score = 83.0/85.0`, `structural_quality_score = 97.6%`, `quality_score = 83.0`.
- **When G8 Passes with Real LLM:** `G8 = 15/15`, `quality_score = 98.0 / 100` (or `100.0 / 100` when G1 has zero warnings).

---

## 3. Historical Assessment Preservation Guarantee

1. Stored `PolicyQualityAssessmentRecord` rows (`policy_quality_assessments`) retain their exact persisted `validator_version`, `quality_score`, `score_breakdown`, and `gate_results` permanently (`UPDATE` is never executed on historical assessment records).
2. Read-only endpoint `GET /api/prompts/rule/{rule_id}/assessments` returns stored assessment records verbatim with `is_legacy_scoring_model = (validator_version != "v2.2.0")`.
3. `GET /api/prompts/rule/{rule_id}/quality-preview` surfaces `historical_assessment_preserved`, `persisted_validator_version`, and `persisted_quality_score` alongside the current `v2.2.0` evaluation so reviewers see both without silent rescoring.
4. `PolicyQualityValidator.validate_policy_quality(..., validator_version="v2.0.0")` remains unit-tested in `test_ais_2_2_remediation.py::test_1` and `test_policy_remediation_and_ground_truth.py`.

---

## 4. Assessment Export & Schema Alignment (`AIS-F06`)

- **Fixed `validation_status: null`:** `PolicyQualityAssessmentResponse.validation_status` now always returns an explicit non-null status (`SIMULATED_ONLY_NOT_CERTIFYING`, `EVALUATED_PASSED`, `EVALUATED_FAILED`, `INSUFFICIENT_DATA`, `INCONCLUSIVE`, or `NOT_EVALUATED`), mirrored by `resolveValidationStatus` in [`frontend/src/lib/qualityExport.ts`](../../frontend/src/lib/qualityExport.ts).
- **Structural vs. Empirical Eligibility:** Both `PolicyQualityValidator` and `/api/prompts` endpoints consistently populate `approval_eligible`, `structural_approval_eligible`, `empirical_validation_eligible`, `autonomous_operation_eligible`, and `hard_gate_failure`.
- **Cross-Format Parity (JSON, Markdown, CSV):**
  - **JSON (`schema_version: "1.0"`):** Adds `scoring_model_version`, `scoring_denominator`, `structural_denominator`, `structural_raw_score`, `gate_scores_total`, `gate_max_total`, non-null `validation_status`, `simulation_provenance`, `historical_preservation`, and `digests`.
  - **Markdown:** Renders `Validation Status`, `Validator / Scoring Model`, `Simulation Provider`, `Simulation Provenance`, eligibility tiers, breakdown table, all 8 gates, and cryptographic digests.
  - **CSV (CWE-1236 protected):** Adds `validator_version`, `scoring_model_version`, `validation_status`, `gate_scores_total`, `gate_max_total`, `simulation_status`, `simulation_provider_type`, `simulation_model_identifier`, `simulation_execution_provenance`, `simulation_is_simulated`, `policy_digest`, `contract_digest`, and `rule_digest` columns.
