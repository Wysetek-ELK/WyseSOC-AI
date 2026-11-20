# Phase 6: Accuracy & Decision Coverage Reconciliation

## 1. Baseline Reconciliation

Prior to this implementation, the AIS 2.0 dashboard presented confusing accuracy indicators due to conflicting interpretations of abstentions and missing inference runs.

### Observed Baseline Metrics:
- **Total Verified Analyst Reviews:** 31
  - Verified False Positives (FP): 31 (100%)
  - Verified True Positives (TP): 0 (0%)
- **AI Evaluation Breakdown for Reviewed Incidents:**
  - Reviewed Incidents with AI Abstentions: 16
  - Reviewed Incidents without Stored AI Inference: 15
  - Eligible Decisive AI Predictions: 0
- **Empirical Accuracy:** **`NOT MEASURABLE`**

---

## 2. Reconciled Metrics Formulation

In `frontend/src/components/compact/AccuracyLearningSummary.tsx` and `backend/app/services/ais_evaluation_service.py`, the metrics are strictly computed:

$$\text{Decision Coverage} = \frac{\text{Evaluated Decisive}}{\text{Total Incident Population}} = \frac{0}{31} = 0.0\%$$

$$\text{Abstention Rate} = \frac{\text{Abstained}}{\text{Total Incident Population}} = \frac{16}{31} = 51.6\%$$

$$\text{Missing Evaluation Rate} = \frac{\text{Not Evaluated}}{\text{Total Incident Population}} = \frac{15}{31} = 48.4\%$$

### Empirical Accuracy Rule:
When $\text{Eligible Decisive Comparisons} == 0$, empirical accuracy is undefined. The UI explicitly renders:
> **Accuracy: NOT MEASURABLE**  
> *"No eligible decisive AI predictions (TP/FP) exist to compare against the 31 verified analyst ground-truth labels. The AI model abstained on 16 incidents and 15 incidents have not yet undergone model inference."*

---

## 3. Decision Coverage 7-Element Grid
The redesigned Accuracy Learning Summary renders a clear 7-metric panel:
1. **Total Population:** 31 Incidents
2. **Decisive AI Verdicts:** 0 (0.0%)
3. **AI Abstentions:** 16 (51.6%)
4. **Not Evaluated:** 15 (48.4%)
5. **Validation Rejected:** 0 (0.0%)
6. **Evaluation Failed:** 0 (0.0%)
7. **Verified Analyst Reviews:** 31 (All FP)

### Class Balance Deficit Notice:
The system warns administrators that all 31 analyst-reviewed incidents are False Positives. A true empirical benchmark requires sourcing verified True Positive host scans to evaluate model sensitivity and precision accurately.
