# 09 — Empirical Metrics and Statistical Integrity

## 1. Statistical Metric Foundations

In accordance with rigorous statistical evaluation standards:
1. **Undefined Metrics**: When the denominator is zero (0 decisive verdicts accepted), metrics such as Accuracy, Precision, Recall, and F1-score cannot be calculated ($0/0$). They are strictly recorded as `null`, **not** fabricated as 0.0% or 100.0%.
2. **Wilson Score Interval**:
   $$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
   where $z = 1.96$ for a 95% two-sided confidence interval.

---

## 2. Authoritative Metrics Matrix

| Metric | Raw Value | Statistical Treatment | 95% Wilson Confidence Interval | Notes |
|---|---|---|---|---|
| **Decisive Verdict Coverage** | 0 / 20 | 0.0% | **[0.00%, 16.84%]** | Full benchmark cohort ($N=20, k=0$) |
| **Provisional Ground Truth Accuracy** | 0 / 0 | `null` (Indeterminate) | Undefined ($0/0$) | No decisive verdicts accepted |
| **Provisional Decisive Cohort Coverage** | 0 / 2 | 0.0% | **[0.00%, 65.76%]** | $N=2$ provisional incidents, $k=0$ decisive |
| **Validator TP Rejection Rate** | 4 / 4 | 100.0% | [51.01%, 100.00%] | All uncorroborated dual-use TPs rejected |
| **Validator Abstention Acceptance Rate** | 6 / 6 | 100.0% | [60.97%, 100.00%] | All honest model abstentions accepted |
| **Context Guard Interception Rate** | 10 / 10 | 100.0% | [72.25%, 100.00%] | All Prisma requests exceeding 3328 tokens intercepted |

---

## 3. Ground Truth Cohort Separation

- Natural historical telemetry records ($N=20$) are strictly maintained under `PROVISIONAL_UNVERIFIED`.
- Controlled simulation test cases ($N=7$) in `test_ais_2_5a_validator_regression.py` are executed strictly in test harnesses with isolated SQLite databases and are never blended into natural historical metrics.
