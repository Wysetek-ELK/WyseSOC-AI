# 08 — Neutral Prompt Bias Correction

- Audited `NEUTRAL_SOC_BASELINE_V1` (`sha256: eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056`), preserving it untouched for frozen hash compatibility (`test_ais_2_6d_empirical_integrity.py`).
- Added `NEUTRAL_SOC_BASELINE_V2` in `backend/app/services/empirical_benchmark_harness.py`:
  - Treats `TRUE_POSITIVE`, `FALSE_POSITIVE`, and `REQUIRES_ATTENTION` symmetrically.
  - Prohibits claiming `Program Files` paths are writable temp directories, prohibits asserting digital signatures unless reported in `digital_signature_status`, distinguishes proxy/SASE downloads from endpoint execution, enforces `network_classification` accuracy, requires citing `canonical_evidence[].evidence_id`, and mandates `0-100` numeric confidence.
