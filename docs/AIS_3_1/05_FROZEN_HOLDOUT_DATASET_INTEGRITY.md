# AIS 3.1 — Workstream 5: Frozen Holdout Dataset Integrity

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Inference Manifest SHA-256:** `e1c21e62afc071dd2b94868c8d7a41b6414b16b27705580a0f42fdbd61611a2d`  
**Machine-Readable Evidence:**
- [FROZEN_HOLDOUT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/FROZEN_HOLDOUT_MANIFEST.json)
- [HOLDOUT_ELIGIBILITY_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/HOLDOUT_ELIGIBILITY_MATRIX.json)

---

## 1. Security Domain Separation

To prevent ground truth leakage across inference and evaluation workflows, AIS 3.1 enforces strict structural separation across three distinct data domains:

1. **Inference Manifest Domain (`FROZEN_HOLDOUT_MANIFEST.json` / inference API payload):**
   - Contains only `sequence_rank`, `cohort_item_id`, `incident_db_id`, `fortisiem_incident_id`, `rule_id`, `rule_name`, resolved `vendor`, `customer`, `severity`, cryptographic hashes (`raw_evidence_sha256`, `canonical_evidence_sha256`, `rule_definition_sha256`, `raw_logs_sha256`), certification state, exposure state, and eligibility state.
   - Contains **zero** human verdicts, **zero** historical SIEM resolutions, and **zero** operational `ai_verdict` values.
2. **Restricted Ground Truth Domain (`AnalystVerdictReview` + `HUMAN_REVIEW_RECONCILIATION.json`):**
   - Access restricted to Administrator / Senior SOC Analyst certification endpoints.
   - Never queried by `AIS31BenchmarkService._prepare_incident_wire_payload` or `AIS31BenchmarkService.execute_run`.
3. **Evaluation Manifest Domain (`AIS31BenchmarkRun` + `AIS31BenchmarkResult` + post-run `evaluate_run_against_ground_truth`):**
   - Binds run metadata (`run_key`, `manifest_sha256`, `policy_freeze_sha256`) to immutable per-incident `wire_prompt_sha256` and `result_integrity_sha256` before comparing against locked GT-2 labels only after execution completes.

---

## 2. Dataset Population Accounting

| Population Classification | Count | Notes |
|---|---:|---|
| **Original Frozen Cohort Population** | **100** | Retained as permanent denominator in all accuracy metrics |
| **Verified Clean / Provisional GT-2 Eligible (`ELIGIBLE`)** | **100** | `25` `VERIFIED_NO_DETECTED_EXPOSURE` + `75` `HISTORICAL_LABEL_EXISTS_BUT_MASKED` |
| **GT-2 Single-Review Population** | **100** | `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` grade |
| **GT-3 Certified Population** | **0** | Pending 2nd independent human reviewer |
| **Quarantined (`QUARANTINED` / Confirmed Exposure)** | **0** | Zero holdout incidents in `LearningRecord`, `ActualLLMPromptCapture`, or `AIS_2_6E_FROZEN_20` |

---

## 3. Freeze & Immutability Controls

- **Raw Logs & Rules Preserved:** Original AIS 3.0 cohort snapshots and hashes verified intact across all 100 items (`0` membership changes, `0` raw log modifications, `0` ground truth edits).
- **Idempotent Checkpointing (`AIS31BenchmarkResult`):** Unique database constraint `uq_ais31_run_fid (run_id, fortisiem_incident_id)` prevents duplicate benchmark accounting across resumable batch executions.
- **No Test-Set Learning:** `LearningRecord`, `VerifiedSemanticRetrievalService`, and Agent Memory ingestion are disabled (`rag_excluded=True`, `memory_excluded=True`).
