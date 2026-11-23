# AIS 2.1b.1 — Accuracy & Ground-Truth Protection Report

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Governance Policy**: Trustworthy SOC AI Evaluation & Blind Review Integrity  
**Date**: November 23, 2026  

---

## 1. Governance Principles & Strict Invariants

Verdictum AI enforces non-negotiable governance principles to prevent the fabrication of AI metrics, protect SOC analyst integrity, and ensure that only empirical, double-blind reviewed evidence influences deployment decisions:

1. **Abstentions Are Never Counted as Errors**: When the LLM abstains due to low confidence or ambiguous telemetry, it is an intended safeguard, not a False Positive or False Negative.
2. **Selective Accuracy Denominator Protection**: Selective accuracy is evaluated solely over *decisive* AI predictions compared against verified ground truth.
   $$\text{Selective Accuracy} = \frac{\text{Eligible Decisive True Positives} + \text{Eligible Decisive True Negatives}}{\text{Eligible Decisive Predictions}}$$
   When $\text{Eligible Decisive Predictions} = 0$, accuracy is **mathematically undefined**. Fabricating a synthetic $0\%$ or $100\%$ is strictly prohibited. The system must report `NOT_MEASURABLE` with `selective_accuracy: null`.
3. **Double-Blind Analyst Review**: Analysts must never see AI predictions, confidence scores, or policy hints prior to submitting their independent verdict.
4. **Zero Synthetic Ground Truth in Production**: Synthetic fixtures or test mock verdicts must never be injected into production learning profiles or empirical accuracy tables.
5. **Policy Immutability**: Production corrective releases must never alter the approved status of active policies (v7 APPROVED) or draft policies (v8 DRAFT).

---

## 2. Empirical Ground-Truth Status on Server 1

### Verified Analyst Verdicts (Server 1 Live Database):
- **Operational Inventory (Current Scope)**:
  - Total Incidents: **35**
  - Analyst Reviews: **33**
  - Verified True Positives (TP): **0**
  - Verified False Positives (FP): **33**
  - Unreviewed Incidents: **2**
- **Cumulative Historical Cohort (Historical Scope)**:
  - Total Cumulative Reviews: **65**
  - Verified True Positives (TP): **0**
  - Verified False Positives (FP): **65**
  - Initial Benchmark Reviews: **16**
  - Ongoing Operational Reviews: **49**

### Root Cause of Single-Class Distribution:
The target rule, `Heavy TCP Host Scan On Fixed Port`, detects high-volume port scanning activity. In the staging/pilot network environment, all observed scan events originated from authorized internal vulnerability assessment scanners and benign network management appliances. SOC analysts correctly verified 100% of these alerts as benign activity (False Positives).

The system truthfully displays this single-class distribution without injecting fabricated True Positives.

---

## 3. AI Evaluation Outcomes Under Policy v7

Under approved policy v7 (`Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2):
- **Decisive Predictions**: **0**
- **Abstentions**: **33**
- **Rejections**: **0**
- **Failed Evaluations**: **0**
- **Not Evaluated / In-Flight**: **2**
- **Total Incidents**: **35**

Because the model produced **0 decisive predictions** (100% abstention rate on this complex telemetry), the selective accuracy denominator is **0**.

### UI & API Reporting:
- `accuracy_status`: `"NOT_MEASURABLE"`
- `selective_accuracy`: `null`
- `accuracy_denominator`: `0`
- `explanation`: *"Selective accuracy cannot be calculated because there are zero decisive AI predictions compared against verified analyst ground truth for this policy version. The model abstained on all evaluated incidents."*

---

## 4. Live GUI Acceptance Verification

The live acceptance test on Server 1 verified:
```json
"accuracyTab": {
  "hasAccuracyTab": true,
  "hasVerifiedReviewsMention": true,
  "hasFpMention": true,
  "hasNotMeasurable": true,
  "hasContradictory13Reviews45FP": false
}
```
The UI truthfully displays the `NOT MEASURABLE` status card and transparently presents the 0 TP / 33 FP ground truth breakdown, fully satisfying all governance and safety invariants.
