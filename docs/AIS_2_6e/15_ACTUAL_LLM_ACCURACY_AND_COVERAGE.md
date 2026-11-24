# AIS 2.6e — Actual LLM Accuracy, Coverage and Ground Truth Dependency

**Document Identifier:** `15_ACTUAL_LLM_ACCURACY_AND_COVERAGE.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / AUDITED  
**Current Assessment:** `NOT_DEMONSTRATED` (Blocked at Checkpoint A)  
**Related Manifests:** [THREE_MODE_EMPIRICAL_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/THREE_MODE_EMPIRICAL_METRICS.json), [CONFUSION_MATRICES.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CONFUSION_MATRICES.json), [PER_RULE_ACCURACY.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/PER_RULE_ACCURACY.json)

---

## 1. Executive Summary & Scientific Position

A core failure of historical phases (AIS 2.6c and prior) was reporting empirical accuracy metrics derived from deterministic offline simulations or uncertified labels.

In Phase AIS 2.6e, Non-Negotiable Requirement 8 is enforced: *"Never claim 0% error when the denominator is zero"*, and Requirement 6: *"Never calculate accuracy using uncertified or inappropriate ground truth"*.

Because human ground truth review is currently pending (0 of 20 certified reviews completed) and Server 2 GPU inference is unexecuted (0 live calls), the empirical accuracy of `Qwen/Qwen2.5-7B-Instruct-AWQ` is formally classified as:

$$\mathbf{EMPIRICAL\_ACCURACY = null \quad (NOT\_DEMONSTRATED)}$$

---

## 2. Mathematical Definition of Evaluation Metrics

When Stage B is executed against certified ground truth, the evaluation pipeline computes metrics under strict mathematical definitions:

### 2.1 Decisive Coverage
$$\text{Decisive Coverage} = \frac{N_{\text{True Positive}} + N_{\text{False Positive}}}{N_{\text{Total Requests Evaluated}}}$$
*Note: Incidents assigned `INCONCLUSIVE` (or `REQUIRES_ATTENTION`) are excluded from the decisive numerator but retained in the total denominator.*

### 2.2 Empirical Accuracy (Certified Population)
$$\text{Accuracy} = \frac{N_{\text{True Positive Matches}} + N_{\text{False Positive Matches}}}{N_{\text{Total Decisive Matches Against Certified Ground Truth}}}$$
*Invariant:* If denominator is 0, metric strictly evaluates to `null`. It is NEVER coerced to 0% or 100%.

### 2.3 Unsafe False Positive Rate (Critical SOC Safety Invariant)
$$\text{Unsafe FP Rate} = \frac{N_{\text{Actual Attacks Misclassified as False Positive}}}{N_{\text{Total Certified Malicious Incidents}}}$$
*Security Rule:* An unsafe FP represents an undetected breach. The maximum acceptable threshold for production SOC deployment is $< 1.0\%$.

---

## 3. Ground Truth Dependency Analysis

Accuracy cannot exist in an epistemological vacuum. An AI's verdict can only be scored as "accurate" if an authoritative ground truth reference is established.
- In `backend/ai_verdict.db`, historical FortiSIEM resolution statuses exist (`1` or `0`), but these reflect unverified automated ticket closures, not analyst ground truth.
- True ground truth requires an accredited human analyst to review the raw logs and rule context under blind conditions.
- Until the 5 priority reviews and 15 cohort reviews are submitted via `/human-review-queue`, accuracy is fundamentally unmeasurable.
