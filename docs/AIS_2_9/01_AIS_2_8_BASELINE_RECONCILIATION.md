# 01 — AIS 2.8 Baseline Reconciliation

- Reconciled [EMPIRICAL_METRICS.json](docs/AIS_2_8/FINAL_LIVE_EXECUTION/EMPIRICAL_METRICS.json) and deployed code at commit `215f744c9e699aac97512505a1afb5fdca888732`.
- AIS 2.8 Qwen3 Exp C (raw) scored 20/20 raw agreement, while Exp D (validated) dropped to 16/20 (80.0%) due to:
  1. `132474210`: Mode B prompt overflow (`8088 + 104 = 8192`, `finish_reason=length`).
  2. `132439932`: False `EVIDENCE_VALUE_MISMATCH` comparing quoted Win32 UltraViewer path against `\Device\HarddiskVolume3\...`.
  3. `132502453`: False `EVIDENCE_VALUE_MISMATCH` comparing quoted Win32 UltraViewer path against `\Device\HarddiskVolume9\...`.
  4. `132501348`: Legitimate safety abstention (`FALSE_POSITIVE` -> `REQUIRES_ATTENTION`, `FP_CRITERIA_UNSATISFIED`) preserved for human/allowlist telemetry.
