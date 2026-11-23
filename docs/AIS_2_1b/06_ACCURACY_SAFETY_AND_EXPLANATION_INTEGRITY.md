# AIS 2.1b — 06: Accuracy Safety & Explanation Integrity

## 1. Safety Invariants Enforced

Verdictum AI operates under strict mathematical and safety contracts:

1. **Abstentions Never Count as Errors:** An AI evaluation of `REQUIRES_ATTENTION` (Abstained) is an intentional deferral to human analyst judgment. Abstentions reduce decision coverage, but never artificially penalize accuracy.
2. **Double-Blind Protection:** Analysts reviewing incidents do not see AI predictions, trust scores, or model proposed verdicts prior to submitting their independent review. Unreviewed incidents strictly mask AI verdicts.
3. **No Fabrication of Accuracy with Zero Denominator:** When eligible decisive AI-analyst pairs equal zero ($\text{denom} = 0$), the application renders `NOT MEASURABLE`, never a fabricated percentage like `0.00%` or `100.00%`.
4. **Separate Class Balance Accounting:** A one-class dataset (0 TP / 47 FP) is explicitly categorized as `PILOT_CLASS_BALANCE_DEFICIT` and `One-Class Dataset`. Class balance deficits are explained independently of accuracy rather than masking empirical metrics.
5. **No Synthetic Ground Truth:** Patterned synthetic fixtures are barred from learning profiles and accuracy metrics.

---

## 2. Mathematical Definitions

### Decision Coverage
$$\text{Decision Coverage} = \frac{\text{Evaluated Decisive}}{\text{Evaluated Decisive} + \text{Abstained} + \text{Validation Rejected}} = \frac{0}{0 + 15 + 0} = 0.0\%$$

### Abstention Rate
$$\text{Abstention Rate} = \frac{\text{Abstained}}{\text{Evaluated Decisive} + \text{Abstained} + \text{Validation Rejected}} = \frac{15}{15} = 100.0\%$$

### Selective Empirical Accuracy
$$\text{Empirical Accuracy} = \frac{\text{Agreement TP} + \text{Agreement FP}}{\text{Eligible Decisive AI/Analyst Pairs}}$$
$$\text{Eligible Decisive Pairs} = 0 \implies \text{Empirical Accuracy} = \text{NOT MEASURABLE}$$

---

## 3. Explanatory Messaging Audit

- **Accuracy Status Badge:** Displays `NOT MEASURABLE` (amber badge).
- **Primary Narrative:**
  > *"Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts."*
- **One-Class Dataset Callout:**
  > *"One-Class Dataset — Verified FP performance can be evaluated, but TP recall and two-class certification require genuine TP cases."*
- **Pilot Class-Balance Notice:**
  > *"Pilot class-balance deficit: requires $\ge 10$ TP and $\ge 10$ FP for Tier 2 Supervised Pilot qualification."*
