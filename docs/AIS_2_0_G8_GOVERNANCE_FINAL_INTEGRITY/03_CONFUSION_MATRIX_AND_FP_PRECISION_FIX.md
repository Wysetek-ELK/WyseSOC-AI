# Report 03 — Confusion Matrix and FP-Class Precision Correction
**Project**: Verdictum AI — Agent Intelligence Studio (AIS 2.0)  
**Task**: G8 Governance Integrity, Empirical Metrics & Final Deployment Verification  
**Date**: November 20, 2026  
**Status**: Mathematical Definitions & UI/Backend Mappings Fully Corrected  

---

## 1. Executive Summary

This report documents the mathematical reconciliation of the empirical metric calculation pipeline, correcting the formula misclassification identified in previous reports and resolving UI/backend key mapping defects across the confusion matrix.

---

## 2. Standard Confusion Matrix Orientation

In Verdictum AI, the positive class is strictly defined as security policy violations:

$$\mathbf{Positive\;Class} = \text{TRUE\_POSITIVE (Confirmed Attack / Policy Violation)}$$
$$\mathbf{Negative\;Class} = \text{FALSE\_POSITIVE (Confirmed Benign / Authorized Activity)}$$

### Quad-Cell Matrix Definition:

| AI Prediction \ Verified Ground Truth | Actual True Positive (Malicious Activity) | Actual False Positive (Benign Activity) | Total Predicted by AI |
| :--- | :---: | :---: | :---: |
| **AI Predicts TRUE_POSITIVE** | $\mathbf{TP}$ *(True Positive / Attack Confirmed)* | $\mathbf{FP}$ *(False Positive / False Alarm)* | $TP + FP$ |
| **AI Predicts FALSE_POSITIVE** | $\mathbf{FN}$ *(False Negative / Missed Attack)* | $\mathbf{TN}$ *(True Negative / Benign Confirmed)* | $TN + FN$ |
| **Total Actual Ground Truth** | $TP + FN$ | $TN + FP$ | $N = TP + TN + FP + FN$ |

---

## 3. Mandatory Mathematical Formulas & Corrections

### 1. Classification Accuracy (Selective Accuracy on Decisive Automated Decisions)
$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
- Measures overall correctness across decisive automated predictions.
- Abstentions (`REQUIRES_ATTENTION` / `INSUFFICIENT_EVIDENCE`) are explicitly segregated and **never** counted into $TP$ or $TN$.

### 2. True Positive Recall (Sensitivity)
$$\text{Recall} = \frac{TP}{TP + FN}$$
- Measures the proportion of actual malicious activity correctly identified by AI.
- Production Requirement: $\ge 95.0\%$.

### 3. TP-Class Precision (Positive Predictive Value)
$$\text{Precision}_{\text{TP}} = \frac{TP}{TP + FP}$$
- Measures the proportion of AI-predicted attacks that were genuinely malicious.

### 4. FP-Class Precision (Precision of Benign Predictions)
$$\text{Precision}_{\text{FP}} = \frac{TN}{TN + FN}$$
- **The Core Correction**: Measures the reliability of AI recommendations to treat an alert as benign.
- When AI recommends suppressing or closing an alert as a False Positive, how often is it actually benign? Out of all predicted negatives ($TN + FN$), the correct benign decisions are $TN$.
- Previous Report 06 erroneously labeled $TN / (TN + FP)$ as FP Precision. $TN / (TN + FP)$ is **Specificity** (True Negative Rate), which measures the proportion of actual benign incidents identified, NOT the precision of the negative prediction class.
- Both backend and frontend now compute and display both metrics distinctly:
  - $\text{FP Precision} = \frac{TN}{TN + FN}$
  - $\text{Specificity} = \frac{TN}{TN + FP}$
- Production Requirement: $\text{FP Precision} \ge 99.0\%$.

### 5. Specificity (True Negative Rate)
$$\text{Specificity} = \frac{TN}{TN + FP}$$
- Measures the proportion of actual benign incidents correctly classified as False Positive.

---

## 4. UI/Backend Key Mapping Defect Resolution

During the audit, a key mapping disconnect was identified between `RuleLearningService` and `AccuracyLearningSummary.tsx`:

### The Defect:
- In `RuleLearningService.record_analyst_feedback()`, the internal dictionary `error_distribution` recorded outcomes under keys:
  `agreement_tp`, `agreement_fp`, `ai_false_alarm`, `critical_missed_tp`
- However, `AccuracyLearningSummary.tsx` attempted to read:
  `profile?.error_distribution?.tp_as_tp`, `fp_as_tp`, `tp_as_fp`, `fp_as_fp`
- Consequently, when rendered in the UI, these keys evaluated to `undefined` or `0`, causing confusion matrix cells to display fallback values or zeroes even when ground truth had been recorded.

### The Remediation:
In `RuleLearningService._recalculate_profile_metrics()`, all canonical key aliases are now normalized and populated simultaneously:
```python
err_dist["tp"] = agreed_tp
err_dist["fp"] = false_alarm
err_dist["tn"] = agreed_fp
err_dist["fn"] = missed_tp
err_dist["tp_as_tp"] = agreed_tp
err_dist["fp_as_tp"] = false_alarm
err_dist["tp_as_fp"] = missed_tp
err_dist["fp_as_fp"] = agreed_fp
err_dist["agreement_tp"] = agreed_tp
err_dist["ai_false_alarm"] = false_alarm
err_dist["critical_missed_tp"] = missed_tp
err_dist["agreement_fp"] = agreed_fp
err_dist["tp_precision"] = tp_precision
err_dist["fp_precision"] = profile.fp_precision
err_dist["specificity"] = specificity
err_dist["tp_recall"] = profile.tp_recall
err_dist["selective_accuracy"] = profile.empirical_accuracy
err_dist["decisive_evaluations"] = total_decisive
```
And in `AccuracyLearningSummary.tsx`, cell lookups safely check both primary and alias keys with full null-safety:
```tsx
{profile?.error_distribution?.tp ?? profile?.error_distribution?.tp_as_tp ?? profile?.error_distribution?.agreement_tp ?? aiCorrect}
```

---

## 5. Summary of Metric Invariants

1. **Abstentions Segregated**: `REQUIRES_ATTENTION` cases are tracked in `abstention_count` and reported alongside decisive decisions.
2. **Dual Precision Reporting**: TP-Class Precision and FP-Class Precision are presented as separate indicators.
3. **Specificity Isolated**: Specificity ($TN / (TN + FP)$) is displayed in the secondary metrics grid with its own mathematical definition.
4. **Zero Ground-Truth Integrity**: When $N = 0$, accuracy is displayed as `Accuracy: NOT MEASURABLE`, preventing fabricated 100% scores.
