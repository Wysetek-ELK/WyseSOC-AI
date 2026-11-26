# 07 — False Positive Evidence Availability (`132501348`)

- On `132501348` (`MEGAsync.exe`), telemetry does not contain an explicit enterprise allowlist, signed change ticket, or approved IT software disposition.
- Qwen3 Mode B proposed `FALSE_POSITIVE` (`6210` tokens), and `IndependentVerdictValidator` deterministically gated it to `REQUIRES_ATTENTION` with `FP_CRITERIA_UNSATISFIED` (`grounding_ratio=1.0`) across all 3 independent runs (`targeted4`, `frozen20`, `stability4`).
- No validator loosening or synthetic benign allowlist hardcoding was introduced.
