# 16 — Stability and Repeatability (`temperature=0.0`, `enable_thinking=false`)

| Incident | Runs Compared | Prompt Tokens Series | Completion Tokens Series | Validated Verdicts | Exact Match |
|---|---:|---|---|---|---:|
| 132439932 | 3 | [6908, 6908, 6908] | [636, 636, 636] | ['TRUE_POSITIVE', 'TRUE_POSITIVE', 'TRUE_POSITIVE'] | True |
| 132474210 | 3 | [6106, 6106, 6106] | [658, 658, 658] | ['TRUE_POSITIVE', 'TRUE_POSITIVE', 'TRUE_POSITIVE'] | True |
| 132501348 | 3 | [5595, 5595, 5595] | [615, 615, 615] | ['REQUIRES_ATTENTION', 'REQUIRES_ATTENTION', 'REQUIRES_ATTENTION'] | True |
| 132596403 | 2 | [5423, 5423] | [658, 658] | ['REQUIRES_ATTENTION', 'REQUIRES_ATTENTION'] | True |
