# Phase 8.2 — Stage C Historical Ground-Truth Corpus Audit

**Evidence Source:** `docs/phase8.2/evidence/historical-data/stage_c_corpus_inventory.json`  
**Seeded Corpus Audited:** `backend/ai_verdict.db` (`26` total incidents, read-only inspect & temp clone simulation)

## 1. Per-Rule Historical Funnel (Post `P8.2-DEF-001` & `P8.2-DEF-002`)

| Rule Code | Status | Total | ML Excluded | Synthetic Excluded (`INC-DEBUG-*`) | Duplicate Clusters Excluded | Human-Labeled | Eligible Independent Groups | Verified TP / FP | Containment-Only FP Notes | G8 / Calibration Eligible |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `INACTIVE` | 10 | 7 | 0 | 0 | 3 | **3** | 0 TP / 3 FP | 2 (`132439932`, `132441815`) | `false` / `false` |
| `PH_RULE_DEBUG_FUNNEL` | `ACTIVE` | 6 | 0 | **6** | 0 | 0 | **0** | 0 TP / 0 FP | 0 | `false` / `false` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `ACTIVE` | 0 | 0 | 0 | 0 | 0 | **0** | 0 TP / 0 FP | 0 | `false` / `false` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `ACTIVE` | 10 | 5 | 0 | **2** | 5 | **3** | 2 TP / 1 FP | 0 | `false` / `false` |

## 2. Corpus Integrity & Leakage Isolation

- **Zero Ground-Truth Leakage:**
  - Live `build_model_facing_payload`: `0` forbidden-key hits across all 26 incidents (`leakage_live_payload_hits = 0`).
  - Historical replay `HistoricalGroundTruthValidator.sanitize_incident_for_inference`: `0` forbidden-key hits across all 26 incidents (`leakage_replay_sanitized_hits = 0`).
- **Deterministic Partitioning Across 26 Incidents:** `TRAIN = 15`, `CALIBRATION = 4`, `TUNING = 4`, `LOCKED_TEST = 3`.
- **Conclusion:** Neither active nor inactive rules currently meet the minimum `>= 5` independent human-verified ground-truth group requirement for G8 regression or `>= 30` cases for calibration. All 4 rules correctly evaluate to `INSUFFICIENT_DATA` and `NOT_CALIBRATED`.

