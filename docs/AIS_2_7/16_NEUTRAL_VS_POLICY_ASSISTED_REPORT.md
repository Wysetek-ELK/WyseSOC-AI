# AIS 2.7 — Workstream 16: Mode A (Neutral) vs Mode B (Policy-Assisted Raw LLM)

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifact:** [MODE_A_VS_MODE_B_COMPARISON.json](MODE_A_VS_MODE_B_COMPARISON.json)

## 1. Did Policy Context Actually Help?

- **Overall 3-Class Shift:** `5.0% (1/20)` -> `10.0% (2/20)` (**Not statistically significant**, exact McNemar `p = 1.0`, `b=1, c=2`).
- **Verdict Transitions (`11/20` changed):**
  - `POLICY_RESCUED_TP`: `2` (`132439932`, `132527297`) — though both contained underlying path/signature hallucinations!
  - `POLICY_SHIFTED_FP_TO_ABSTENTION_VIA_FALSE_MISSING_FIELD`: `7` CrowdStrike UltraViewer TPs — eliminating missed-TP-as-FP suppression only because mentioning `process.command_line` in the policy confused the 7B-AWQ model into falsely believing the field was absent!
  - `POLICY_CAUSED_REGRESSION_FP_TO_TP`: `1` (`132501348` `MEGAsync.exe`) — swapped Mode A's accidental FP match into a wrong TP.
  - `POLICY_SHIFTED_TO_FALSE_TP_ON_INCONCLUSIVE`: `1` (`132499745` Prisma SASE -> `95%` conf TP).
  - `UNCHANGED_WRONG_FP`: `9` Prisma SASE `INCONCLUSIVE` alerts remained wrong `FALSE_POSITIVE`.

**Root Insight:** Policy prompting (`+1,480` to `+1,981` tokens per prompt) did **not** endow `Qwen2.5-7B-Instruct-AWQ` with reliable analytical reasoning; furthermore, Server 1's active Prisma SASE policy (`ed7ff3c7` v1) actively harmed Mode B by imposing EDR field rules and discouraging `REQUIRES_ATTENTION` on network logs.
