# Analyst vs AI Comparison Reconciliation Audit

**Target Rule**: `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Rule UUID**: `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Tenant Scope**: `DEFAULT`  
**Date**: November 20, 2026  

---

## 1. Ground Truth Reconciliation Table

Audit of PostgreSQL database table `analyst_verdict_reviews` for `rule_id = '40498741-ee6b-4a71-9101-0d6d3f77154c'`:

| Metric Category | Count | Mathematical Treatment | UI Representation |
|:---|:---:|:---|:---|
| **Total Human Analyst Reviews** | **31** | Denominator for review coverage | "From 31 total analyst review(s)" |
| **Verified True Positives (TP)** | **0** | Human verified attack sample | 0 TP |
| **Verified False Positives (FP)** | **31** | Human verified benign sample | 31 FP |
| **Analyst Abstentions** | **0** | Insufficient evidence by human | 0 |
| **Agreed TP (`AGREEMENT_TP`)** | **0** | Decisive Hit (AI: TP, Analyst: TP) | Cell (TP, TP) = 0 |
| **Agreed FP (`AGREEMENT_FP`)** | **0** | Decisive True Negative (AI: FP, Analyst: FP) | Cell (FP, FP) = 0 |
| **AI False Alarm (`AI_FALSE_ALARM`)** | **0** | Decisive False Positive (AI: TP, Analyst: FP) | Cell (TP, FP) = 0 |
| **Critical Missed TP (`CRITICAL_MISSED_TP`)** | **0** | Decisive False Negative (AI: FP, Analyst: TP) | Cell (FP, TP) = 0 |
| **AI Abstentions Resolved (`ANALYST_RESOLVED_ABSTENTION`)** | **16** | Non-decisive (AI: `REQUIRES_ATTENTION`, Analyst: FP) | Excluded from Selective Accuracy |
| **Initial Benchmarks (`ANALYST_ONLY_INITIAL_BENCHMARK`)** | **15** | Non-decisive (AI: None, Analyst: FP) | Excluded from Selective Accuracy |
| **Total Decisive Comparisons** | **0** | $TP + TN + FP + FN = 0$ | **Empirical Accuracy: N/A** |

---

## 2. Why Empirical Accuracy is Mathematically N/A

Under Verdictum AI mathematical governance, **Selective Accuracy** is formulated as:
$$\text{Selective Accuracy} = \frac{\text{Agreed TP} + \text{Agreed FP}}{\text{Total Decisive Automated Predictions}}$$

Where:
$$\text{Total Decisive Automated Predictions} = \text{Agreed TP} + \text{Agreed FP} + \text{AI False Alarm} + \text{Critical Missed TP}$$

### The Mathematical Problem:
$$\text{Total Decisive Automated Predictions} = 0 + 0 + 0 + 0 = 0$$
$$\text{Selective Accuracy} = \frac{0}{0} \implies \text{UNDEFINED (N/A)}$$

### Why Decisive Predictions Equaled Zero:
1. **16 AI Abstentions**: When Local AWQ evaluated these 16 incidents, the model safely output `REQUIRES_ATTENTION` (ungrounded evidence / perimeter sweep uncertainty). Because the AI abstained, it did NOT make a decisive assertion of True Positive or False Positive. The human analyst subsequently investigated and determined the traffic was a benign routine scan (False Positive). This is classified as `ANALYST_RESOLVED_ABSTENTION` and is tracked under safety abstentions, not decisive classification.
2. **15 Initial Benchmarks**: 15 incidents were reviewed by the analyst before Local AWQ inference had ever processed them (`revealed_ai_verdict = None`). Without an AI verdict to compare against, these serve as un-paired ground truth benchmarks (`ANALYST_ONLY_INITIAL_BENCHMARK`).
3. **Class Balance Deficit**: All 31 reviews were False Positives ($TP = 0$). Under Tier 2 Supervised Pilot rules, at least 10 independently confirmed True Positives and 10 False Positives are required to calibrate the baseline.

---

## 3. Policy Isolation & Version Binding

- **Active Policy (`v7 APPROVED`)**: SHA `d79fb576-c6b9-4f63-9167-3c7a2419b70a`  
  Has 7/8 quality gates passing, with G8 in WARNING state due to zero decisive empirical evaluations.
- **Candidate Policy (`v8 DRAFT`)**: SHA `20d4f788-85a5-437d-afbe-fe7fd80abca1`  
  Under evaluation in the Agent Simulation Lab. Test AI executions on candidate v8 produce candidate-specific simulation runs and do NOT corrupt the active v7 production profile until formal promotion.
