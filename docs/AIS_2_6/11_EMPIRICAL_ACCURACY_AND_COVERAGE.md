# 11 — Empirical Accuracy and Coverage Report

## Executive Summary

This report delivers the authoritative statistical evaluation of Verdictum AI under AIS 2.6 across all 20 benchmark incidents. In accordance with rigorous empirical standards, metrics with zero denominator (precision, recall, specificity) are reported as `null` rather than fabricated values.

---

## 1. Statistical Matrix

| Metric | Value | 95% Wilson Confidence Interval | Mathematical Calculation |
|---|---|---|---|
| **Total Evaluated Incidents** | 20 | N/A | $N = 20$ |
| **Live GPU Executions** | 10 | [29.9%, 70.1%] | $10 / 20 = 50.0\%$ |
| **Preflight Interceptions** | 10 | [29.9%, 70.1%] | $10 / 20 = 50.0\%$ |
| **Model Proposed TP** | 4 | [7.0%, 42.3%] | $4 / 20 = 20.0\%$ |
| **Model Proposed FP** | 0 | [0.0%, 16.1%] | $0 / 20 = 0.0\%$ |
| **Model Proposed Abstentions** | 6 | [14.0%, 53.5%] | $6 / 20 = 30.0\%$ |
| **Validator Accepted Decisive** | **0** | **[0.0%, 16.1%]** | **0 / 20 = 0.0%** |
| **Decisive Coverage Rate** | **0.0%** | **[0.0%, 16.1%]** | $0 / 20$ |
| **TP Precision** | `null` | `null` | Undefined ($0 / 0$) |
| **TP Recall** | `null` | `null` | Undefined ($0 / 0$) |
| **FP Specificity** | `null` | `null` | Undefined ($0 / 0$) |
| **False Positive Rate (FPR)** | `null` | `null` | Undefined ($0 / 0$) |
| **False Negative Rate (FNR)** | `null` | `null` | Undefined ($0 / 0$) |
| **Selective Accuracy** | `null` | `null` | Undefined ($0 / 0$) |
| **Safety Invariant Violation Rate** | **0.0%** | [0.0%, 16.1%] | 0 autonomous closures |

---

## 2. Wilson Score Interval Calculation Integrity

For small sample sizes with zero occurrences ($k = 0, n = 20$), the normal approximation ($p \pm 1.96 \sqrt{p(1-p)/n}$) collapses to $0 \pm 0$, which is mathematically invalid.
The 95% Wilson score interval is calculated as:
$$w = \frac{\hat{p} + \frac{z^2}{2n} \pm z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
With $k = 0, n = 20, z = 1.95996$:
$$w_{\text{lower}} = 0.0\%$$
$$w_{\text{upper}} = \frac{0 + \frac{3.8415}{40} + 1.96 \sqrt{0 + \frac{3.8415}{1600}}}{1 + \frac{3.8415}{20}} = \frac{0.09604 + 1.96(0.04899)}{1.192075} = \frac{0.192075}{1.192075} \approx 16.11\%$$

The true decisive coverage is bounded within **[0.0%, 16.11%]** with 95% confidence.
