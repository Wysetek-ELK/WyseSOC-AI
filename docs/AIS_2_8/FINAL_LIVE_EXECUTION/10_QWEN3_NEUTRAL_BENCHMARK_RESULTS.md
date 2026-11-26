# 10 — Experiment A: Qwen3 Neutral V2 Results (`QWEN3_NEUTRAL_V2`)

- **Technical Completion**: `20/20` (`ok=True`, `finish_reason=stop`, `schema_valid=20/20`, `0` overflows).
- **Parsed Outcomes**: `16` `REQUIRES_ATTENTION`, `4` `FALSE_POSITIVE`, `0` `TRUE_POSITIVE`.
  - **3-Class Exact**: `11/20 (55.0%)`
  - **Prisma SASE `INCONCLUSIVE`**: `10/10 (100.0%)` (major improvement vs AIS 2.7 `0/10`!)
  - **CrowdStrike FP (`132501348`)**: `1/1 (100.0%)` parsed `FALSE_POSITIVE`
  - **CrowdStrike TP Recall**: `0/9 (0.0%)` (`3` TPs misclassified as `FALSE_POSITIVE`, `6` abstained as `REQUIRES_ATTENTION`)
- **Mode A Validated Outcomes**: `20/20` resolved to `REQUIRES_ATTENTION` (`10/20 = 50.0%` 3-class, `0` false decisive errors).
