# AIS 2.7 — Workstream 17: Raw LLM (Mode B) vs Deterministic Validator (Mode C)

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [MODE_B_VS_MODE_C_COMPARISON.json](MODE_B_VS_MODE_C_COMPARISON.json), [VALIDATOR_FALSE_REJECTION_REGISTER.json](VALIDATOR_FALSE_REJECTION_REGISTER.json)

## 1. Validator Impact & Safety Value

- **3-Class Accuracy Lift:** `10.0% (2/20)` -> `45.0% (9/20)` (**Statistically significant**, exact McNemar two-sided `p = 0.0391`).
- **Critical SOC Safety Improvements:**
  - **Prisma SASE `INCONCLUSIVE` rescue:** `8/10 (80.0%)` erroneous decisive Mode B verdicts stopped and converted to `REQUIRES_ATTENTION` (`6` hallucination rejections + `2` insufficient-evidence rejections).
  - **`132501348` FP-as-TP attack surface blocked:** Mode B's erroneous `TRUE_POSITIVE` on `MEGAsync.exe` rejected (`TP_CRITERIA_UNSATISFIED`) -> `REQUIRES_ATTENTION`.
  - **False Missing-Field Contradictions Exposed:** `7/7` Mode B abstentions on CrowdStrike explicitly tagged `ABSTENTION_WITH_CONTRADICTION` proving `process.command_line` was actually present.
- **Validator False Rejection Audit:** `1` Mode B GT-matching TP (`132527297`) was downgraded by Mode C -> **0 substantive false rejections** (`VALIDATOR_FALSE_REJECTION_REGISTER.json`) because Mode B genuinely fabricated `"Binary not signed"` citing `process.name`.
- **Remaining Validator Gaps Exposed:**
  1. Missed prose-level path contradiction in `132439932` (`"writable temporary path"` inside `claim_text` despite `Program Files (x86)` `asserted_value`).
  2. Leaked `2/10` Prisma `FALSE_POSITIVE` verdicts (`132599145`, `132499023`) where field-string citations superficially matched while narrative misread IPs/assumed benignity.
