# Verdict Trustworthiness Engine (AIS 2.1)

## 1. Overview and Core Purpose

A model's self-reported "confidence percentage" (e.g., `confidence: 0.95`) is notoriously unreliable in security contexts due to overconfidence, calibration drift, and sycophantic reasoning.

The **Verdict Trustworthiness Engine** (`backend/app/services/verdict_trustworthiness_engine.py`) replaces self-reported confidence with an **independent, empirical 1–10 Verdict Trust Score**. The score measures the defensibility and evidentiary grounding of a specific verdict given the available telemetry, contract compliance, contradiction analysis, and historical rule validation track record.

---

## 2. The 5-Dimension Trust Rubric

The engine computes an underlying raw score between $0.0$ and $100.0$ across five weighted dimensions:

$$\text{Raw Trust Score} = 0.35 \times S_{\text{claim}} + 0.20 \times S_{\text{source}} + 0.15 \times S_{\text{contradiction}} + 0.15 \times S_{\text{corroboration}} + 0.15 \times S_{\text{history}}$$

| Dimension | Weight | Description | Evaluation Basis |
|---|---|---|---|
| **Claim Support & Grounding** ($S_{\text{claim}}$) | **35%** | Evaluates whether every factual claim, entity assertion, and threshold citation in the verdict reasoning directly maps to canonical incident telemetry. | Penalized for hallucinated IP addresses, unverified usernames, or assumed thresholds. |
| **Source Telemetry Reliability** ($S_{\text{source}}$) | **20%** | Measures the integrity and provenance of the underlying evidence fields. | Drawn directly from `EvidenceSufficiencyAssessmentResult.integrity_score`. |
| **Contradiction & Ambiguity Handling** ($S_{\text{contradiction}}$) | **15%** | Penalizes verdicts that ignore or gloss over conflicting evidence (e.g., claimed egress when flow was inbound). | Drops to 0 if an unhandled contradiction exists; stays at 100 if telemetry is coherent or contradictions are explicitly resolved. |
| **Corroborating Context Availability** ($S_{\text{corroboration}}$) | **15%** | Evaluates the presence of multi-sensor corroboration (e.g., firewall log backed by proxy logs or EDR process telemetry). | Scored proportionally to secondary context completeness. |
| **Historical Policy Track Record** ($S_{\text{history}}$) | **15%** | Measures the empirical accuracy of the current detection policy on historically verified incidents for this rule. | Based on historical true positive / false positive validation rate (defaults to baseline 70.0 when uncalibrated). |

---

## 3. Ordinal Scale Mapping (1–10)

The raw score ($0–100$) is discretized into an intuitive, non-linear **1–10 Ordinal Trust Score**:

| Ordinal Score | Band Name | Raw Score Range | Operational Meaning in SOC |
|---|---|---|---|
| **1–2** | Very Low Trust | $0.0 \le \text{Raw} < 40.0$ | Untrustworthy verdict. Insufficient evidence, severe contradictions, or hallucinated claims. Ineligible for automated triage. |
| **3–4** | Low Trust | $40.0 \le \text{Raw} < 60.0$ | Sub-standard defensibility. Missing non-mandatory evidence or weak factual grounding. Mandatory human escalation. |
| **5–6** | Moderate Trust | $60.0 \le \text{Raw} < 75.0$ | Acceptable evidentiary support, but lacks external corroboration or historical calibration. Standard analyst review required. |
| **7–8** | High Trust | $75.0 \le \text{Raw} < 90.0$ | Strong evidence grounding, verified entities, zero contradictions, and positive historical track record. Suitable for automated pre-triage. |
| **9–10** | Very High Trust | $90.0 \le \text{Raw} \le 100.0$ | Bulletproof evidence grounding, multi-source corroboration, fully calibrated historical accuracy ($\ge 90\%$). Candidate for zero-touch auto-closure/escalation. |

---

## 4. The Uncalibrated Small-Sample Penalty

> [!CAUTION]
> **Sample Size Gating:** A rule without sufficient empirical track record cannot be trusted for automated decisions, regardless of how convincing the prompt or single incident appears.

If a detection rule has been evaluated against **fewer than 30 verified historical incidents** ($N < 30$):
- `is_calibrated` is marked `False`.
- The ordinal trust score is **strictly capped at a maximum of 6/10**.
- The `evaluation_notes` field records:
  `"Rule has fewer than 30 verified historical incidents (sample_size=N); trust score capped at 6/10."`

This prevents premature high-trust ratings on newly authored or rarely triggered rules until statistically valid empirical evidence is accumulated.

---

## 5. Conditions Required to Attain a Perfect Score (10/10)

To achieve the highest trust rating of **10/10**, a verdict must satisfy all of the following criteria simultaneously:
1. **100% Claim Grounding**: `unsupported_claims_count == 0` and `claim_support_score >= 95.0`.
2. **Zero Contradictions**: `contradictions_detected == 0`.
3. **Evidence Sufficiency**: `sufficiency_score >= 90.0` with `missing_mandatory_fields == []`.
4. **Source Reliability**: `source_reliability_score >= 85.0`.
5. **Corroboration Present**: Multi-sensor contextual corroboration confirmed (`corroboration_score >= 80.0`).
6. **Empirically Calibrated**: Rule has $N \ge 30$ historical ground truth samples with an empirical balanced accuracy $\ge 90.0\%$.

If any of these conditions fails, the score is capped below 10.
