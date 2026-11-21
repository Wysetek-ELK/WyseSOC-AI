# 05 — Accuracy Metrics and Explanation Fix

**Verdictum AI — AIS 2.1a Unified Population Hotfix**  
**Component:** Empirical Accuracy Engine & UI Feedback  
**Timestamp:** 2026-11-21T11:16:30+05:30  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Zero-Denominator Safety Invariant

Under classical mathematical definitions:
$$\text{Selective Accuracy} = \frac{\text{TP}_\text{matched} + \text{FP}_\text{matched}}{\text{Total Decisive Predictions}}$$

When $\text{Total Decisive Predictions} = 0$:
$$\text{Selective Accuracy} = \frac{0}{0} = \text{Undefined} \implies \text{NOT MEASURABLE}$$

### Prior Defect:
In certain early UI states, a null or zero selective accuracy was rendered as `0.00%` or `"0% Accuracy"`, creating the false and alarming impression that the AI model failed on every incident.

### AIS 2.1a Resolution:
1. When $\text{decisive comparisons} = 0$, `accuracy_status` is strictly `"NOT_MEASURABLE"`.
2. The UI renders the banner:
   **`Empirical Accuracy: NOT MEASURABLE (0 Decisive AI Predictions)`**
3. Badge indicator explicitly displays: **`DECISIVE PREDICTIONS NEEDED`**.

---

## 2. Plain-English Diagnostic Explanations

The UI now provides two clear, non-contradictory diagnostic explanations:

### Explanation A: Why Accuracy Cannot Be Calculated
> *"Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts. All 13 current operational incidents evaluated under policy v7 received abstentions (REQUIRES_ATTENTION) or missing evaluations. Selective Accuracy requires decisive predictions (TRUE_POSITIVE or FALSE_POSITIVE) matched against verified analyst ground truth."*

### Explanation B: One-Class Dataset & Pilot Certification Deficit
> *"One-Class Dataset: The ground truth dataset for this rule currently consists solely of FALSE_POSITIVE incidents (0 TP / 45 FP in cumulative historical profile; 0 TP / 13 FP in current inventory). While False Positive suppression performance can be verified, True Positive detection recall and two-class production certification (G8 eligibility) require at least 10 verified True Positive incidents."*

---

## 3. Scope-Bound Accuracy Cards

Each of the summary cards in the Accuracy tab is now bound strictly to the selected population scope:

| Card | Current Operational Inventory (13) | Cumulative Historical Cohort (45) | Mathematical Guarantee |
|---|:---:|:---:|:---:|
| **Card 1: Verified Ground Truth** | **13** (0 TP / 13 FP) | **45** (0 TP / 45 FP) | $0 + 13 = 13$ \| $0 + 45 = 45$ |
| **Card 2: Empirical Accuracy** | **NOT MEASURABLE** (0 Decisive) | **NOT MEASURABLE** (0 Decisive) | Zero-denominator safe |
| **Card 3: AI Abstentions** | **13** (100% Rate) | **30** (66.7% Rate) | All abstentions accounted |
| **Card 4: Missing Inference** | **0** (Complete v7 Coverage) | **15** (Initial Benchmarks) | Historical context explained |

The user can toggle seamlessly between **Current Incident Inventory** and **Cumulative Historical Cohort** without ever witnessing mixed numbers or impossible totals.
