# AIS 2.6d — Workstream 15: Actual Model Capability and Retention Decision Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:55:00Z  
**Document Identity:** `docs/AIS_2_6d/15_ACTUAL_MODEL_CAPABILITY_AND_RETENTION_DECISION.md`  
**Referenced Manifests:**  
- [MODEL_CAPABILITY_DECISION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/MODEL_CAPABILITY_DECISION.json)
- [MODEL_COMPARISON_READINESS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/MODEL_COMPARISON_READINESS.json)

---

## 1. Re-Evaluating the Model Retention Hypothesis

In AIS 2.6c, `MODEL_RETENTION_DECISION.json` recorded a formal recommendation to retain `Qwen/Qwen2.5-7B-Instruct-AWQ`. However, as established in Workstream 1:
- That decision was predicated entirely on offline deterministic simulations.
- Zero live GPU calls were executed.
- Zero empirical accuracy comparisons against human ground truth existed.

Under AIS 2.6d, Non-Negotiable Requirement 6 and the Phase Mission state:
> "Do not inherit the previous conclusion that the current model's capability is proven sound. Treat that conclusion as an unverified hypothesis."

---

## 2. Objective Retention Criteria

To retain `Qwen/Qwen2.5-7B-Instruct-AWQ` as the production inference model for Verdictum AI, the following empirical hurdles must be met during live GPU testing:
1. **Empirical Accuracy:** F1 score $\ge 0.85$ against Level 2 Human Ground Truth on the frozen cohort.
2. **Unsafe False Positive Rate:** Zero ($0\%$) misclassifications of critical true threats as False Positives under Mode C validation.
3. **Decisive Coverage:** Produces definitive verdicts on $\ge 70\%$ of incidents without excessive abstention.
4. **Context Window Stability:** Zero token overflow errors under 8192 token limit.
5. **Inference Latency:** Median response time $\le 30$ seconds on AWS GPU Server 2 (`g5.xlarge`).

---

## 3. Formal Retention Decision

**Current Determination:** `INSUFFICIENT_EVIDENCE_FOR_MODEL_DECISION`.

Neither model retention nor model replacement can be scientifically justified until live GPU inference results are obtained and evaluated against verified human ground truth.
