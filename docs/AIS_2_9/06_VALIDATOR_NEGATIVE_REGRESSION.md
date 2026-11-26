# 06 — Validator Negative & Adversarial Regression

- Verified via `backend/tests/test_ais_2_9_remediation.py` (`pytest` 113 passed across 17 suites):
  - Rejects wrong drive letter (`D:\...` vs corroborating `C:\...`).
  - Rejects wrong directory (`C:\Users\Temp\UltraViewer_Service.exe` vs `\Device\HarddiskVolume3\Program Files (x86)\...`).
  - Rejects basename-only equality (`UltraViewer_Service.exe` != full path).
  - Rejects cross-event NT-to-DOS mapping (`EV-event2` command line never corroborates `EV-event1` file_path).
  - Rejects `truncated_output=true` (`finish_reason=length`) to `REQUIRES_ATTENTION` (`TRUNCATED_OUTPUT`).
- Live Mode A (`pol=False`) negative guardrail confirmation: on `132439932`, `132502453`, and `132501348`, validator blocked erroneous `FALSE_POSITIVE` proposals via `EVIDENCE_CONTRADICTION` / `FP_CRITERIA_UNSATISFIED` (`validator_false_acceptance_count=0`).
