# 13 — Experiment D: Deterministic Validator & Trust Engine Impact (`mode_c`)

- **Across Exp A & Exp B (Anti-Hallucination Safety)**: Rejected `100%` of ungrounded CrowdStrike `FALSE_POSITIVE` predictions (preventing `3` false FP closures in Exp A and `6` in Exp B), enforcing `0` false decisive verdicts.
- **On Exp C (`mode_b -> mode_c`)**:
  - **Validated 3-Class Accuracy**: `16/20 (80.0%)`
  - **Validated TP Recall**: `6/9 (66.67%)`
  - **Validated Binary Precision**: `6/6 (100.0%)` (`0` wrong-polarity errors!)
  - **Exact Reasons for the 4 Validator Downgrades (`20/20` raw -> `16/20` validated)**:
    1. `132474210` (CrowdStrike TP): `INSUFFICIENT_EVIDENCE` (`TP_CRITERIA_UNSATISFIED`) caused by Mode B `8088+104=8192` token truncation (`schema_valid=False`).
    2. `132439932` (CrowdStrike TP): **Validator False Rejection** (`EVIDENCE_VALUE_MISMATCH`) — model cited `process.file_path` as Win32 `"C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe"` (`process.command_line`) vs NT device `\Device\HarddiskVolume3\...`.
    3. `132502453` (CrowdStrike TP): **Validator False Rejection** (`EVIDENCE_VALUE_MISMATCH`) — identical NT device `\Device\HarddiskVolume9\...` vs Win32 command_line mismatch.
    4. `132501348` (CrowdStrike FP): Held safely at `REQUIRES_ATTENTION` (`FP_CRITERIA_UNSATISFIED`) because telemetry lacked external allowlist/hash clean proof (human-only evidence).
