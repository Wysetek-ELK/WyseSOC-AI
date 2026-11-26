# 14 — Historical Qwen2.5 vs Live Qwen3 Comparison

> **Scope Disclosure**: Fresh Qwen2.5-7B live execution was explicitly excluded (`NOT_RUN_OPERATOR_SINGLE_MODEL_SCOPE`). Archived AIS 2.7 (`Qwen/Qwen2.5-7B-Instruct-AWQ`) metrics were independently recalculated from `docs/AIS_2_7/LIVE_BENCHMARK_RESULTS.json` (`41` ok / `42` entries).

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

- **Observed Improvement (`OBSERVED_IMPROVEMENT_OVER_HISTORICAL_BASELINE`)**:
  - Neutral agreement jumped from `5.0%` (`Qwen2.5 Mode A`) to `55.0%` (`Qwen3 Exp A`), driven largely by fixing Prisma `ed7ff3c7 v1` bias (`0/10 -> 10/10` escalation) plus Qwen3 instruction following.
  - Rule-policy raw agreement jumped from `10.0%` (`Qwen2.5 Mode B`) to **`100.0%` (`Qwen3 Exp C`)**, and validated operational accuracy jumped from `45.0%` (`Qwen2.5 Mode C`) to **`80.0%` (`Qwen3 Exp D`)** (`11.1% -> 66.7%` TP recall).
