# Phase 8.1 Historical Corpus Forensic Audit (Stage 6)

- **Status:** **`PASSED`** *(Complete forensic inventory executed on isolated clone of `backend/ai_verdict.db` + `fixtures/Incident json.zip`; zero labels fabricated)*
- **Primary Evidence:** [`stage6_corpus_audit.json`](./evidence/historical-replay/stage6_corpus_audit.json)

## 1. Corpus Composition & Provenance Breakdown (`26` Incidents Across `4` Rules)

| Rule Code | Rule Status | Total Incidents | `ev_cnt == 0` Synthetic Debug | ML-Generated (`is_ml_generated=1`, Excluded) | Human `VERIFIED_TP` | Human `VERIFIED_FP` | Missing / Unverified |
|---|---|---:|---:|---:|---:|---:|---:|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `INACTIVE` | 10 | 0 | 7 (`2 FP`, `5 TP`) | **0** | **3** | 0 |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `ACTIVE` | 10 | 0 | 5 (`4 FP`, `1 TP`) | **4** *(1 cluster of 3 + 1 standalone)* | **1** | 0 |
| `PH_RULE_DEBUG_FUNNEL` | `ACTIVE` | 6 | **6** | 1 (`TP`) | **1** *(synthetic 0-event)* | **1** *(synthetic 0-event)* | 3 (`2 None`, `1 Under Investigation`) |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `ACTIVE` | 0 | 0 | 0 | **0** | **0** | 0 |
| **Total** | — | **26** | **6** | **13** | **5** *(4 non-synthetic)* | **5** *(4 non-synthetic)* | **3** |

## 2. Critical Dataset Integrity Findings

1. **Zero-Event Synthetic Debug Records Counted as Eligible in Replay (`P8.1-GAP-DS-01`):**
   - `PH_RULE_DEBUG_FUNNEL` contains `6` synthetic fixture rows (`INC-DEBUG-01..06`) with `event_count = 0`, `first_seen_epoch = null`, and single-key payloads (`["command_line"]` or `[]`).
   - Existing `PolicySimulationService` excluded `INC-DEBUG-05` (`CORRUPT_OR_EMPTY_PAYLOAD`), `INC-DEBUG-03` (`MISSING_ANALYST_LABEL`), `INC-DEBUG-04` (`AMBIGUOUS_LABEL`), and `INC-DEBUG-06` (`HEURISTIC_OR_ML_LABEL`), leaving **`INC-DEBUG-01` (`TP`) and `INC-DEBUG-02` (`FP`) marked as `verified_ground_truth_cases = 2`** even though they lack real SIEM `rawEvents` telemetry.
2. **Batch Near-Duplicate & ML/Human Overlap Clusters (`stage6_corpus_audit.json`):**
   - `Prisma_SASE_Suspicious_File_Threat_Detection_` human `VERIFIED_TP` count of `4` collapses to **only 2 distinct incident bursts**: `132596403` (`Mail has been sent already`) plus a **3-incident batch closure cluster** (`132599145` [`ev=2`], `132599146` [`ev=11`], `132599330` [`ev=2`]) sharing identical `cleared_time_epoch = 1793846725003` and `cleared_reason = "Case has been raised for the similar incidents."`.
   - `PH_RULE_CS_SUSPICIOUS_ACTIVITY` `132438483` (`is_ml=True`) and `132439932` (`is_ml=False`) share identical `cleared_time_epoch = 1793783492775` and `cleared_reason = "kill process is true"`.
3. **Zero True Positives in Non-ML CrowdStrike Human Set:**
   - All `3` human-labeled non-ML rows (`132439932`, `132441815`, `132474210`) in `PH_RULE_CS_SUSPICIOUS_ACTIVITY` are `False Positive`; all `5` CS `True Positive` rows were `is_ml_generated = 1`.
4. **Leakage & Partition Verification:**
   - **Data Leakage:** `0 / 26` incidents leaked `resolution`, `cleared_reason`, `cleared_user`, or `comments` in either live `build_model_facing_payload` or replay `sanitize_incident_for_inference` (`leakage_free = true`).
   - **Deterministic Splits:** `TRAIN = 15`, `CALIBRATION = 4`, `TUNING = 4`, `LOCKED_TEST = 3`.

