# AIS 2.6d — Workstream 14: Trust Score and Confidence Calibration Integrity Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:50:00Z  
**Document Identity:** `docs/AIS_2_6d/14_TRUST_SCORE_AND_CONFIDENCE_INTEGRITY.md`  
**Referenced Manifests:**  
- [TRUST_SCORE_AUDIT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/TRUST_SCORE_AUDIT.json)
- [CONFIDENCE_CALIBRATION_READINESS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/CONFIDENCE_CALIBRATION_READINESS.json)

---

## 1. Disentangling Model Confidence from Empirical Accuracy

Under Non-Negotiable Requirement 16:
- **Never equate model-generated confidence with empirical accuracy.**
- In AIS 2.6c and earlier, high self-reported model confidence (e.g. 0.95) was occasionally cited as evidence of verdict trustworthiness, even when predicting an unverified False Positive.
- Model self-confidence is a soft metric reflecting generation certainty, frequently subject to overconfidence in instruction-tuned LLMs.

---

## 2. Multi-Factor Trust Score Architecture

Verdictum AI computes an objective composite Trust Score independent of raw model self-confidence:
1. **Evidence Grounding Factor (35%):** Ratio of cited telemetry entities (hashes, IPs, processes) that exist verbatim in the raw event payload.
2. **Rule Directive Alignment (25%):** Degree of consistency with triggered SIEM detection rule logic.
3. **Validator Agreement (20%):** Concordance with independent deterministic validator checks.
4. **Historical Provenance Factor (20%):** Level of verified human ground truth corroborating the pattern (Level 0 through 4).

---

## 3. Calibration Status

Expected Calibration Error (ECE) and Brier Score calculations require paired tuples of `(model_confidence, binary_ground_truth)`.
- Live inferences: 0
- Level 2 human reviews: 0
- Current Status: **CALIBRATION_PENDING_LIVE_DATA** (ECE: `null`, Brier Score: `null`).
