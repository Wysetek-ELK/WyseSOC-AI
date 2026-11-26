# 15 — Empirical Metrics and Confusion Matrices

- **AIS 2.9 Validated Exact 3-Class Agreement**: `95.0%` (`19/20`) vs AIS 2.8 `80.0%` (`16/20`)
- **AIS 2.9 Validated TP Recall**: `100.0%` (`9/9`) vs AIS 2.8 `66.67%` (`6/9`)
- **AIS 2.9 Binary Correctness**: `90.0%` (`9/10`) vs AIS 2.8 `60.0%` (`6/10`)
- **AIS 2.9 Binary Decision Coverage**: `90.0%` (`9/10`) vs AIS 2.8 `60.0%`
- **AIS 2.9 Conditional Binary Accuracy**: `100.0%`
- **AIS 2.9 Inconclusive Agreement**: `100.0%` (`10/10`, `0` binary leakage)

## Validated Confusion Matrix (`GT_HUMAN -> VALIDATED`)

```json
{
  "FALSE_POSITIVE->REQUIRES_ATTENTION": 1,
  "INCONCLUSIVE->REQUIRES_ATTENTION": 10,
  "TRUE_POSITIVE->TRUE_POSITIVE": 9
}
```
