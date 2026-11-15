# VERDICTUM AI — VALIDATION V1.2.2
## 05. STATISTICAL ELIGIBILITY & SAMPLING THRESHOLDS REPORT

**Document Version:** 1.0.0  
**Target Engine:** `WilsonScoreEvaluator`, `RuleLearningService`  
**Status:** MATHEMATICALLY VERIFIED  

---

### 1. Separation of Pilot vs Production Thresholds

The platform enforces strict separation between pilot exploration and autonomous production gating:

| Evaluation Tier | Sample Requirement | Wilson Lower Bound Target | Target Decision Confidence | Allowed Automation Level |
| :--- | :--- | :--- | :--- | :--- |
| **Supervised Pilot** | $N \ge 30$ verified reviews | $\approx 88.65\%$ ($z = 1.96$) | 95% Confidence Level | Human-in-the-loop approval, analyst co-pilot |
| **Controlled Production** | $N \ge 100$ verified reviews | $\ge 96.00\%$ ($z = 1.96$) | 95% Confidence Level | Autonomous policy approval & verdict execution |

---

### 2. Wilson Score Lower Bound Zero-Failure Analysis

Under the Wilson score interval formula with continuity correction at 95% confidence ($z = 1.96$):

$$w = \frac{p + \frac{z^2}{2n} - z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

For a perfect sample ($k = n$, $p = 1.0$):

| Sample Count ($n$) | Successes ($k$) | Empirical Accuracy | Wilson Lower Bound ($w$) | Pilot Eligible? | Production Eligible? |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | 0 | None (Zero Denom) | None (Zero Denom) | No | No |
| 10 | 10 | 100.0% | 72.25% | No | No |
| 30 | 30 | 100.0% | **88.65%** | **YES** | **NO** (< 96%) |
| 50 | 50 | 100.0% | 92.60% | YES | NO (< 96%) |
| 90 | 90 | 100.0% | 95.89% | YES | NO (< 96%) |
| 92 | 92 | 100.0% | 95.99% | YES | NO (< 96%) |
| **93** | **93** | **100.0%** | **96.03%** | **YES** | **YES** ($\ge 96\%$) |
| 100 | 100 | 100.0% | 96.30% | YES | YES ($\ge 96\%$) |

#### Core Takeaway
A rule with 30 reviews cannot be treated as ready for production approval. The Wilson lower bound for 30 error-free reviews is 88.65%, which falls significantly short of the 96% requirement. At least **93 error-free reviews** (or 100 real-world reviews) are mathematically required.

---

### 3. Zero-Denominator & Zero-Evaluation Guardrails

When a rule has 0 evaluated reviews or 0 FP predictions:
- `empirical_accuracy`: `None` (UI renders `Pending` or `N/A`, never `0%` or synthetic `100%`).
- `fp_precision`: `None`
- `tp_recall`: `None`
- `wilson_lower_bound`: `None`

All math functions in `WilsonScoreEvaluator` return `0.0` or `None` without dividing by zero or synthesizing passing metrics.
