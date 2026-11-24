# 10 — Certified Development Cohort Baseline Report

## Executive Summary

This report establishes the baseline evaluation performance on Partition A (Development & Calibration Cohort, 8 incidents). Partition A is designated for prompt engineering, rule contract authoring, and policy optimization.

---

## 1. Partition A Cohort Composition

Partition A contains 8 incidents:
- **Cluster 1** (5 incidents): `132438483`, `132439932`, `132441815`, `132461358`, `132461368` (CrowdStrike UltraViewer on `DESKTOP-E0G2R49`)
- **Independent Incidents** (3 incidents):
  - `132472498` (CrowdStrike: Potentially unwanted application)
  - `132474210` (CrowdStrike: Legitimate activity)
  - `132502453` (CrowdStrike: Unapproved utility)

---

## 2. Partition A Baseline Performance

| Metric | Observed Value | Mathematical Formula |
|---|---|---|
| **Evaluated Incidents** | 8 | $N_A = 8$ |
| **Model Proposed TP** | 3 (`132439932`, `132461358`, `132472498`) | $3 / 8 = 37.5\%$ |
| **Model Proposed Abstentions** | 5 | $5 / 8 = 62.5\%$ |
| **Validator Accepted Decisive** | 0 | $0 / 8 = 0.0\%$ |
| **Decisive Coverage** | **0.0%** | $0 / 8$ |
| **95% Wilson Score CI for Coverage** | **[0.0%, 32.4%]** | Exact Wilson interval for 0/8 |
| **Preflight Interceptions** | 0 | All 8 dispatched to GPU |
| **Mean GPU Latency** | 22,238 ms | Live vLLM execution |

### Diagnostic Findings for Partition A
1. Dual-use remote tools without corroborating malicious tradecraft were rejected by the validator to `REQUIRES_ATTENTION`.
2. Model abstentions exhibited reasoning contradictions (e.g. claiming certain telemetry was missing when present), which are now accurately flagged as `ABSTENTION_WITH_CONTRADICTION`.
