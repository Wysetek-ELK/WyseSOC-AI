# 06 — Wire Token & Context Window Verification

- **Remote `/tokenize` Calibration (`POST /api/ground-truth/ais27/tokenize-verify`)**:
  - `small`: `37` live vLLM tokens vs `91` local estimate (drift `-54`)
  - `medium`: `1630` vs `1850` (drift `-220`)
  - `near_limit`: `6410` vs `6370` (drift `+40`)
- **Live Execution Token Accounting**:
  - **Experiment A (`mode_a`)**: prompt `3754..7261` (avg `5334.3`), max total `7901`, overflows `0`.
  - **Experiment B (`mode_a`)**: prompt `5398..6859` (avg `5771.8`), max total `7579`, overflows `0`.
  - **Experiment C (`mode_b`)**: prompt `5423..8088` (avg `6106.6`), max total `8192`, **1 context overflow (`132474210`: `8088 + 104 = 8192`, `finish_reason=length`)** because `sys_b` (~800 tokens larger than `sys_a`) exceeded the `mode_a`-calibrated reserve.
  - **Experiment R (`mode_a` V1, 15 calls)**: prompt `2918..6884`, overflows `0`.
