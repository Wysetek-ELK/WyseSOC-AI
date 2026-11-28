# AIS 3.2 — 02: AIS 3.1 Failure Root-Cause Analysis

Reconciled historical AIS 3.1 holdout (`AIS_3_0_INDEPENDENT_HOLDOUT_100`, `18 TP / 80 FP / 2 INCONCLUSIVE`, status `FAIL_INTELLIGENCE`):
- **Raw LLM (`Qwen/Qwen3-14B-AWQ`):** `25/100` decisive coverage (`25%`), `12/25` conclusive accuracy (`48%`), `12/100` E2E (`12%`), `0/18` TP recall (`6` FNs + `12` TP abstentions), `7` FP overcalls.
- **Validated Application:** `1/100` decisive coverage (`1%`), `99` abstentions (`24/25` raw verdicts overridden by endpoint-coupled validator checks).
- **Root Causes Decomposed:**
  1. Operational monitoring TPs (`7301`, `15482`, `11002`) misclassified as FP for "no attack".
  2. Config change (`11992`) & external deny (`141`) lacked authorized context vs probing semantics.
  3. Endpoint-centric validator rejected valid network/firewall/IPS/ops claims.
  4. `max_completion_tokens=768` truncated complex structured JSON (incident `8777`).
