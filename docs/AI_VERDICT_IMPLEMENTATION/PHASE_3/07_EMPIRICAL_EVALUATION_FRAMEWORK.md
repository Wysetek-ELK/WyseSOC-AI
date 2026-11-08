# 07. EMPIRICAL EVALUATION FRAMEWORK

**Document Identifier:** `AV-P3-DOC-07`  
**Requirement Mapping:** `P3-REQ-07` (Empirical Evaluation Framework)  
**Implementation Modules:** `app/services/calibration_evaluation_service.py`, `app/schemas/calibration.py`  

---

## 1. Principles of Honest Evaluation

In Phase 0 and Phase 1 audits, it was discovered that test simulation scores were sometimes casually described as "accuracy" even when no independent ground truth was available.

Phase 3 establishes an empirical evaluation framework based on strict scientific criteria:
- **No Ground-Truth Leakage:** Model inference inputs never receive closure codes or ground-truth labels.
- **Independent Benchmark Records:** Evaluations are computed exclusively against independently adjudicated `HistoricalGroundTruth` or supervisor-verified `LearningRecord` entries.
- **Bifurcated Abstention Metrics:** The framework separates performance on decisive verdicts from abstentions (`REQUIRES_ATTENTION`).

---

## 2. Calculated Metrics

`CalibrationEvaluationService.calculate_metrics` evaluates predictions across 7 core metrics:

1. **Precision:** $\frac{TP}{TP + FP}$ — Fraction of declared true positives that were genuinely malicious.
2. **Recall:** $\frac{TP}{TP + FN}$ — Fraction of actual malicious attacks successfully identified.
3. **False Negative Rate (FNR):** $\frac{FN}{TP + FN}$ — Critical security metric measuring missed attacks.
4. **Abstention Rate:** $\frac{\text{Abstained (REQUIRES\_ATTENTION)}}{\text{Total Cases}}$ — Frequency with which the system defers to human analysts.
5. **Selective Accuracy:** $\frac{TP + TN}{TP + TN + FP + FN}$ — Accuracy computed strictly on non-abstained, decisive cases.
6. **Brier Score:** Mean squared error between predicted model probabilities and true ground truth labels ($y \in \{0, 1\}$).
7. **Expected Calibration Error (ECE):** Weighted absolute difference between accuracy and confidence across 5 confidence bins ($[0-20\%], [20-40\%], [40-60\%], [60-80\%], [80-100\%]$).

