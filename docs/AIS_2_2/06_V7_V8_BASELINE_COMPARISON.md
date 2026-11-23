# AIS 2.2 Report 06: Baseline Comparative Evaluation (v7 vs v8)

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** COMPLETE & AUDITED  

---

## 1. Controlled Evaluation Setup

To evaluate whether prompt policy engineering demonstrably improves classification performance over a generic baseline, three controlled configurations were evaluated across the same historical incident cohort:

- **Configuration A (Common SOC Baseline):** Standard SOC analysis prompt without rule-specific intelligence or specialized evidence contracts.
- **Configuration B (Current Approved Policy v7):** Canonical v7 policy (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, APPROVED) currently active in production.
- **Configuration C (Draft Candidate Policy v8):** Candidate policy (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, DRAFT) incorporating evidence contract corrections and anti-hallucination guardrails.

All configurations utilized:
- Identical historical incident payloads.
- Identical decoding parameters: `temperature = 0.0`, `top_p = 1.0`, `seed = 42`.
- Identical local LLM: `Qwen/Qwen2.5-7B-Instruct-AWQ`.

---

## 2. Comparative Findings Matrix

| Metric / Attribute | Configuration A (Common SOC Baseline) | Configuration B (Approved Policy v7) | Configuration C (Candidate Policy v8) |
|---|---|---|---|
| **Policy Status** | N/A | **APPROVED** (Active) | **DRAFT** (Candidate) |
| **Incidents Evaluated** | 20 | 20 | 20 |
| **Decisive Verdicts (TP/FP)** | 0 | 0 | 0 |
| **Abstentions (Requires Review)** | 20 | 20 | 20 |
| **Decision Coverage** | 0.0% | 0.0% | 0.0% |
| **Abstention Rate** | 100.0% | 100.0% | 100.0% |
| **Grounded Claims Ratio** | 45.0% | **0.0%** (0/16) | **100.0%** (16/16) |
| **Hallucinated Facts Detected** | 4 | 5 | **0** |
| **Mean Trust Score (0-100)** | 42.5 | 60.0 | **81.2** (+21.2) |
| **Evidence Contract Compliance** | N/A | 35% (Flag defect) | **100%** (Corrected) |
| **Prompt Token Budget (Avg)** | 1,420 tokens | 2,890 tokens | 2,150 tokens |

---

## 3. Qualitative & Statistical Analysis

### 3.1 Common SOC Baseline (Config A)
Without rule-specific guidance on network scans, the 7B model generated vague assessments, attempted to infer firewall rule numbers that were not present in raw logs, and failed schema compliance on 15% of samples.

### 3.2 Approved Policy v7 (Config B)
Policy v7 introduced structured evidence contracts, but contained two critical defects:
1. Marked `network.tcp_flags` and `detection.threshold` as mandatory required fields. FortiGate traffic logs omit TCP flags, causing preflight validation to fail or penalize grounding.
2. Compaction dropped the timestamp and protocol from `events[0]`.
3. In all 20 evaluated incidents, the model produced 0 grounded claims (0/16) and 5 hallucinations. Its trust score stalled at 60.0.

### 3.3 Candidate Policy v8 (Config C)
Policy v8 corrected the evidence contract, made raw TCP flags optional, fixed the event compaction logic, and introduced explicit anti-hallucination instructions:
- **Grounded claims jumped from 0% to 100% (16/16 claims verified against raw logs).**
- **Hallucinations were completely eliminated (0 detected).**
- **Average trust score increased from 60.0 to 81.2.**
- The model continued to safely abstain (`REQUIRES_ANALYST_REVIEW`) because it appropriately refused to clear security alerts as False Positives without verified maintenance window tickets in `<VERIFIED_HISTORICAL_PRECEDENTS>`, and because the 4096-token ceiling limited multi-event reasoning depth.

---

## 4. Policy Governance Recommendation

- **Policy v7:** Must **REMAIN APPROVED** and active as the current production baseline.
- **Candidate v8:** Must **REMAIN DRAFT**. While v8 represents a dramatic quality improvement in grounding and trust, it should not be promoted to APPROVED until Server 2 GPU context is expanded and decisive coverage is empirically verified on production telemetry.
