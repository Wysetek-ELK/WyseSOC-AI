# Calibration and Uncertainty Reporting (AIS 2.1)

## 1. Overview and Core Purpose

A model that claims 90% confidence should be accurate 90% of the time. If a system claims 95% confidence on 100 alerts but only 60 of them are actually true positives, the system is **poorly calibrated and dangerously overconfident**.

The **Calibration Evaluator** (`backend/app/services/calibration_evaluator.py`) measures probability calibration, computes the **Brier Score** and **Expected Calibration Error (ECE)**, and generates 5-bin reliability diagrams to visualize over/under-confidence.

---

## 2. Mathematical Definitions

### Expected Calibration Error (ECE)
The dataset is partitioned into $M = 5$ equally spaced confidence bins $B_1, \dots, B_M \in [0, 1]$:

$$\text{ECE} = \sum_{m=1}^{M} \frac{|B_m|}{N} \Big| \text{acc}(B_m) - \text{conf}(B_m) \Big|$$

Where:
- $|B_m|$ is the number of samples falling into bin $m$.
- $N$ is the total number of evaluated samples.
- $\text{acc}(B_m)$ is the empirical accuracy of predictions in bin $m$.
- $\text{conf}(B_m)$ is the average model confidence in bin $m$.

An ECE near $0.0$ signifies near-perfect calibration. An ECE $> 0.15$ indicates substantial miscalibration.

### Brier Score
The Brier score measures the mean squared difference between predicted probabilities and actual outcomes:

$$\text{BS} = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2$$

Where:
- $p_i \in [0.0, 1.0]$ is the predicted probability for the positive class.
- $y_i \in \{0, 1\}$ is the actual binary ground truth ($1$ for TP, $0$ for FP).

A Brier score of $0.0$ indicates perfect accuracy and calibration. A score of $0.25$ represents a random coin flip.

---

## 3. Five-Bin Reliability Diagram

Predictions are partitioned into 5 standard bins:
1. **Bin 1**: $[0.0, 0.20)$
2. **Bin 2**: $[0.20, 0.40)$
3. **Bin 3**: $[0.40, 0.60)$
4. **Bin 4**: $[0.60, 0.80)$
5. **Bin 5**: $[0.80, 1.00]$

```
Observed Accuracy
  1.0 |                   / [Perfect Calibration Line]
      |                 /
  0.8 |               /   * (Bin 5: Conf = 0.88, Acc = 0.82)
      |             /
  0.6 |           / * (Bin 4: Conf = 0.69, Acc = 0.61)
      |         /
  0.4 |       / * (Bin 3: Conf = 0.48, Acc = 0.45)
      |     /
  0.2 |   / * (Bin 2: Conf = 0.29, Acc = 0.25)
      | /
  0.0 +----------------------- Predicted Confidence
      0.0  0.2  0.4  0.6  0.8  1.0
```

---

## 4. Honest Small-Sample Reporting ($N < 30$)

> [!WARNING]
> Computing ECE or Brier scores across 5 bins when the total sample size is small ($N < 30$) produces severe statistical noise and false confidence.

The evaluator enforces strict sample-size gating:
- If $N < 30$:
  - `is_calibrated` is set to `False`.
  - `calibration_status` is explicitly reported as `"NOT_CALIBRATED"`.
  - `warning` notes: `"Sample size (N) is below the minimum threshold of 30 required for reliable calibration evaluation. Metrics should not be used for production auto-triage gating."`
  - Bins with zero samples report `count = 0`, `accuracy = 0.0`, `confidence = 0.0` rather than fabricated values.

This transparent honesty protects SOC leadership from relying on statistical artifacts during initial rule onboarding.
