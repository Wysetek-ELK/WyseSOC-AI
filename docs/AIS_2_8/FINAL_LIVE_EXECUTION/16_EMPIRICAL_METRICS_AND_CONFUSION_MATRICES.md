# 16 — Empirical Metrics & Confusion Matrices

## Full-Cohort Scorecard (`AIS_2_6E_FROZEN_20`)

| Metric | Historical Qwen2.5 (Mode B) | Historical Qwen2.5 Validated (Mode C) | Qwen3 Neutral (Exp A Raw) | Qwen3 Enriched (Exp B Raw) | Qwen3 Policy (Exp C Raw) | Qwen3 Validated (Exp D) | Qwen3 Replay V1 (Exp R 15/20) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3-Class Agreement | 2/20 (10.0%) | 9/20 (45.0%) | 11/20 (55.0%) | 11/20 (55.0%) | 20/20 (100.0%) | 16/20 (80.0%) | 5/15 (33.33%) |
| Binary E2E Correctness | 2/10 (20.0%) | 1/10 (10.0%) | 1/10 (10.0%) | 1/10 (10.0%) | 10/10 (100.0%) | 6/10 (60.0%) | 0/10 (0.0%) |
| Conditional Binary Accuracy | 2/3 (66.67%) | 1/1 (100.0%) | 1/4 (25.0%) | 1/7 (14.29%) | 10/10 (100.0%) | 6/6 (100.0%) | 0/3 (0.0%) |
| Binary Decision Coverage | 3/10 (30.0%) | 1/10 (10.0%) | 4/10 (40.0%) | 7/10 (70.0%) | 10/10 (100.0%) | 6/10 (60.0%) | 3/10 (30.0%) |
| TP Recall | 2/9 (22.22%) | 1/9 (11.11%) | 0/9 (0.0%) | 0/9 (0.0%) | 9/9 (100.0%) | 6/9 (66.67%) | 0/9 (0.0%) |
| FP Identification Recall | 0/1 (0.0%) | 0/1 (0.0%) | 1/1 (100.0%) | 1/1 (100.0%) | 1/1 (100.0%) | 0/1 (0.0%) | 0/1 (0.0%) |
| Inconclusive Agreement | 0/10 (0.0%) | 8/10 (80.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 5/5 (100.0%) |
| TP -> FP Misclassifications | 0 | 0 | 3 | 6 | 0 | 0 | 3 |
| Inconclusive Binary Leakage | 10 | 2 | 0 | 0 | 0 | 0 | 0 |

## Evidence-Equivalent Subset (`19` incidents, excluding human-only `132501348`)

- **Exp C Raw**: `19/19 (100.0%)` 3-class | TP Recall `9/9 (100.0%)` | Inconclusive `10/10 (100.0%)`
- **Exp D Validated**: `16/19 (84.21%)` 3-class | TP Recall `6/9 (66.67%)` | Binary Precision `100.0%`

## Confusion Matrices

- **Exp C (`mode_b.parsed`)**: `{"FALSE_POSITIVE->FALSE_POSITIVE": 1, "INCONCLUSIVE->REQUIRES_ATTENTION": 10, "TRUE_POSITIVE->TRUE_POSITIVE": 9}`
- **Exp D (`mode_c.validated`)**: `{"FALSE_POSITIVE->REQUIRES_ATTENTION": 1, "INCONCLUSIVE->REQUIRES_ATTENTION": 10, "TRUE_POSITIVE->REQUIRES_ATTENTION": 3, "TRUE_POSITIVE->TRUE_POSITIVE": 6}`
