# AIS 2.7 — Workstream 13: Statistical Power, Confidence Intervals & Uncertainty Report

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifact:** [STATISTICAL_ANALYSIS.json](STATISTICAL_ANALYSIS.json)

## 1. Wilson 95% Confidence Intervals

| Metric | k / n | Point Estimate | 95% Wilson CI |
|---|---|---|---|
| Mode A 3-Class Accuracy | `1/20` | `5.0%` | `[0.89%, 23.61%]` |
| Mode A Binary TP Recall | `0/9` | `0.0%` | `[0.0%, 29.91%]` |
| Mode B 3-Class Accuracy | `2/20` | `10.0%` | `[2.79%, 30.1%]` |
| Mode B Binary TP Recall | `2/9` | `22.22%` | `[6.32%, 54.74%]` |
| Mode C Validated 3-Class Accuracy | `9/20` | `45.0%` | `[25.82%, 65.79%]` |
| Mode C Prisma Abstention Accuracy | `8/10` | `80.0%` | `[49.02%, 94.33%]` |

## 2. Paired Exact Binomial McNemar Comparisons (`N = 20`, 3-Class Agreement)

| Comparison | Only First Correct (`b`) | Only Second Correct (`c`) | Exact Two-Sided `p`-value | Significant (`alpha = 0.05`) |
|---|---|---|---|---|
| Mode A vs Mode B | `1` | `2` | `1.0` | `False` |
| Mode B vs Mode C (Validated) | `1` | `8` | `0.039062` | `True` |
| Mode A vs Mode C (Validated) | `1` | `9` | `0.021484` | `True` |

## 3. Clustering & Effective Sample Size Caveats

9/10 CrowdStrike incidents share the same UltraViewer_Service.exe detection pattern on host accounts of customer Tosoh; all 10 Prisma SASE incidents share the same Suspicious File rule for customer Forbes Marshall. Effective independent scenario count is materially smaller than N=20, widening true uncertainty beyond naive i.i.d. CIs.  
Because incidents within a rule are correlated (9 UltraViewer incidents under one rule, 10 JS/exe Prisma SASE downloads under one rule, and only `1` False Positive incident in binary ground truth), effective sample size `N_eff < 20`. Despite narrow statistical power on rare classes (FP `N=1`), raw failure in Mode A (`5%`) and Mode B (`10%`) is so extreme that upper 95% CIs (`23.6%` and `30.1%`) remain far below any viable SOC threshold.
