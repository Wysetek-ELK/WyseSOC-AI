# AIS 2.6d — Workstream 10: Actual LLM Accuracy, Coverage, and Ground Truth Integrity

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:30:00Z  
**Document Identity:** `docs/AIS_2_6d/10_ACTUAL_LLM_ACCURACY_AND_COVERAGE.md`  
**Referenced Manifests:**  
- [THREE_MODE_EMPIRICAL_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/THREE_MODE_EMPIRICAL_METRICS.json)
- [CONFUSION_MATRICES.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/CONFUSION_MATRICES.json)
- [PER_RULE_ACCURACY.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/PER_RULE_ACCURACY.json)
- [METRIC_DENOMINATOR_AUDIT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/METRIC_DENOMINATOR_AUDIT.json)
- [STATISTICAL_LIMITATIONS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/STATISTICAL_LIMITATIONS.json)

---

## 1. Ground Truth Stratification & The Denominator Problem

In historical phases (AIS 2.6c and prior), accuracy metrics were reported without distinguishing between automated FortiSIEM comments and verified human ground truth. Furthermore, simulated runs claimed 0% False Positive error despite having zero certified False Positives or zero decisive inferences in the denominator.

Under AIS 2.6d, Non-Negotiable Requirements 6, 7, and 8 govern all calculations:
- **Rule 6:** Never calculate accuracy using uncertified or inappropriate ground truth.
- **Rule 7:** Never treat "Requires Attention" or "Inconclusive" as an incorrect TP/FP automatically.
- **Rule 8:** Never claim 0% error when the denominator is zero. When the denominator is zero, metrics must evaluate to `null` and report `NOT_DEMONSTRATED`.

### Ground Truth Stratification Levels
- **Level 0 (Unverified / Unknown):** 0 incidents
- **Level 1 (Historical FortiSIEM Operational Classification):** 20 incidents (Contains closure leakage, unverified by SOC analyst)
- **Level 2 (Independent Double-Blind Human Review):** 0 incidents (Pending analyst review via Checkpoint A)
- **Level 3 (Independently Corroborated / Adjudicated):** 0 incidents
- **Level 4 (Formally Certified Ground Truth):** 0 incidents

---

## 2. Empirical Accuracy Evaluation Across Modes

Because:
1. Level 2+ Human Ground Truth reviews completed = 0
2. Live GPU inferences executed = 0 (Server 2 stopped)

The current empirical accuracy metrics are strictly mathematically evaluated as:
- **Mode A (Neutral Baseline):** Precision: `null`, Recall: `null`, F1: `null`, Decisive Coverage: `null` (`NOT_DEMONSTRATED`)
- **Mode B (Approved Policy):** Precision: `null`, Recall: `null`, F1: `null`, Decisive Coverage: `null` (`NOT_DEMONSTRATED`)
- **Mode C (Independent Validator):** Precision: `null`, Recall: `null`, F1: `null`, Unsafe FP Rate: `null` (`NOT_DEMONSTRATED`)

Zero fraudulent numbers or simulation metrics are permitted.

---

## 3. Confusion Matrix Structure (Awaiting Data)

| Metric | Level 1 (Historical) | Level 2 (Human Review) | Level 4 (Certified) |
| :--- | :---: | :---: | :---: |
| True Positives (TP) | Pending Live Run | Pending Review | Pending Review |
| False Positives (FP) | Pending Live Run | Pending Review | Pending Review |
| True Negatives (TN) | Pending Live Run | Pending Review | Pending Review |
| False Negatives (FN) | Pending Live Run | Pending Review | Pending Review |
| Inconclusive / Abstentions | Pending Live Run | Pending Review | Pending Review |
| **Status** | **AWAITING_GPU** | **AWAITING_REVIEW** | **AWAITING_CERT** |

---

## 4. Per-Rule Accuracy Breakdown

- **`PH_RULE_CS_SUSPICIOUS_ACTIVITY` (10 Incidents):**
  - Historical: 10 incidents labeled `True-Positive` by analyst comments, but zero double-blind human verifications recorded in Verdictum AI.
  - Live LLM Accuracy: `NOT_DEMONSTRATED`.
- **`Prisma_SASE_Suspicious_File_Threat_Detection_` (10 Incidents):**
  - Historical: 10 incidents labeled `True-Positive` by analyst comments, but zero double-blind human verifications recorded in Verdictum AI.
  - Live LLM Accuracy: `NOT_DEMONSTRATED`.

---

## 5. Statistical Limitations

With a frozen cohort of $N = 20$ incidents, even after live GPU execution and complete Level 2 human reviews:
- Confidence intervals for accuracy at $N=20$ are broad ($\approx \pm 15\%$ at 95% confidence).
- Results must be reported as preliminary development benchmarks rather than definitive enterprise certifications. Full statistical certification will require expansion to larger cohorts in subsequent phases once baseline feasibility is demonstrated.
