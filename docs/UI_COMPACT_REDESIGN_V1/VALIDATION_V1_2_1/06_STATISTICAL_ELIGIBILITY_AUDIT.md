# VERDICTUM AI — VALIDATION V1.2.1
## 06. STATISTICAL ELIGIBILITY & CONFIDENCE BOUND AUDIT

**Document Version:** 1.0.0  
**Mathematical Scope:** Wilson Score Interval, Precision/Recall Zero-Sample Handling, G7 Quality Gate  
**Status:** MATHEMATICALLY VERIFIED & AUDITED  

---

### 1. Mathematical Formalism

The Wilson score interval provides an asymmetric binomial confidence interval that remains well-behaved near 0 and 1, avoiding the pathologies of the normal approximation (Wald interval).

For sample proportion $\hat{p} = \frac{x}{n}$, sample size $n$, and critical value $z$ from the standard normal distribution (for 95% two-sided confidence, $z = 1.959964$, $z^2 \approx 3.841459$):

$$\text{Center} = \frac{\hat{p} + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}$$

$$\text{Margin} = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}$$

$$\text{Wilson Lower Bound } (W_{\text{lower}}) = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

---

### 2. Error-Free Sample Threshold Derivation

Quality Gate G7 requires that the **Wilson 95% lower bound for precision must reach $\ge 96.0\%$** ($W_{\text{lower}} \ge 0.96$) to certify automated production execution.

Consider the ideal case with zero errors ($x = n$, $\hat{p} = 1.0$):

$$\hat{p}(1 - \hat{p}) = 0$$

Substituting into the Wilson lower bound formula:

$$W_{\text{lower}} = \frac{1 + \frac{z^2}{2n} - z \sqrt{\frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}} = \frac{1 + \frac{z^2}{2n} - \frac{z^2}{2n}}{1 + \frac{z^2}{n}} = \frac{1}{1 + \frac{z^2}{n}} = \frac{n}{n + z^2}$$

To satisfy $W_{\text{lower}} \ge \theta$ where $\theta = 0.96$:

$$\frac{n}{n + z^2} \ge \theta$$

$$n \ge \theta(n + z^2)$$

$$n(1 - \theta) \ge \theta z^2$$

$$n \ge \frac{\theta}{1 - \theta} z^2$$

For $\theta = 0.96$ and $z = 1.959964$ ($z^2 = 3.841459$):

$$n \ge \frac{0.96}{0.04} \times 3.841459 = 24 \times 3.841459 = 92.195$$

Since $n$ must be an integer:

$$n_{\text{min}} = \lceil 92.195 \rceil = 93$$

**Conclusion:** A minimum of **93 consecutive error-free analyst observations** is mathematically required to guarantee a 95% Wilson lower bound $\ge 96.0\%$. Any claim of $\ge 96.0\%$ confidence with fewer than 93 observations is mathematically impossible.

---

### 3. Removal of Zero-Sample Fabrication

#### Previous Vulnerability in V1.2
When `total_fp_evaluations == 0` or `total_analyst_reviews == 0`:
```python
# VULNERABLE CODE (PRE-V1.2.1)
precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0  # Fabricated 100%
wilson_lower = compute_wilson(precision, total_reviews) or 0.96  # Fabricated 96%
```
This allowed rules with zero real telemetry to bypass Gate G7.

#### Remediated Code in `backend/app/services/rule_learning_service.py`
```python
if total_fp_evaluations == 0:
    profile.fp_precision = None
    profile.wilson_lower_bound = None
else:
    profile.fp_precision = round(float(correct / total_fp_evaluations), 4)
    profile.wilson_lower_bound = compute_wilson_lower_bound(
        correct, total_fp_evaluations, confidence=0.95
    )
```

In the UI (`AgentIntelligenceStudioOverview.tsx`), `None` is rendered as `"N/A (0/30 verified reviews)"` with a badge `Evaluation Pending`, preventing false green checkmarks.

---

### 4. Automated Proof Evidence

Executed in `backend/tests/test_v1_2_1_readiness_integrity.py`:
- `test_wilson_lower_bound_no_fabrication`:
  - When $n = 0$: $W_{\text{lower}} \to \text{None}$.
  - When $n = 30$, errors = 0: $W_{\text{lower}} \approx \frac{30}{30 + 3.8415} = 88.65\% < 96.0\%$. Gate G7 fails.
- `test_wilson_lower_bound_93_error_free_samples_threshold`:
  - When $n = 92$, errors = 0: $W_{\text{lower}} = \frac{92}{92 + 3.8415} = 95.99\% < 96.0\%$. Gate G7 fails.
  - When $n = 93$, errors = 0: $W_{\text{lower}} = \frac{93}{93 + 3.8415} = 96.03\% \ge 96.0\%$. Gate G7 passes.
