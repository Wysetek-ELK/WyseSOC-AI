# AIS 2.7 — Workstream 12: Empirical Accuracy & Confusion Matrix Report

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Ground Truth Reference:** Exploratory GT-2 (`N = 20`: `9 TRUE_POSITIVE`, `1 FALSE_POSITIVE`, `10 INCONCLUSIVE -> REQUIRES_ATTENTION`; binary eligible `N = 10` CrowdStrike only)  
**Artifacts:** [EMPIRICAL_METRICS.json](EMPIRICAL_METRICS.json), [CONFUSION_MATRICES.json](CONFUSION_MATRICES.json), [RULE_LEVEL_METRICS.json](RULE_LEVEL_METRICS.json), [INCIDENT_LEVEL_COMPARISON.json](INCIDENT_LEVEL_COMPARISON.json)

## 1. Three-Mode Performance Comparison (All Exact Numerators & Denominators)

| Metric | Mode A (Neutral LLM) | Mode B (Policy LLM Raw) | Mode C (Validator `validated_verdict`) | Mode C (`effective_trust_verdict`) |
|---|---|---|---|---|
| **3-Class Accuracy (`N=20`)** | 1/20 (5.0%) | 2/20 (10.0%) | 9/20 (45.0%) | 10/20 (50.0%) |
| **Binary Accuracy (`N=10` CS)** | 1/10 (10.0%) | 2/10 (20.0%) | 1/10 (10.0%) | 0/10 (0.0%) |
| **Binary Decision Coverage** | 10/10 (100.0%) | 3/10 (30.0%) | 1/10 (10.0%) | 0/10 (0.0%) |
| **Conditional Decisive Acc.** | 1/10 (10.0%) | 2/3 (66.67%) | 1/1 (100.0%) | 0/0 (N/A) |
| **TP Recall (`N=9` CS TP)** | 0/9 (0.0%) | 2/9 (22.22%) | 1/9 (11.11%) | 0/9 (0.0%) |
| **TP Precision (Full Cohort)** | 0/0 (N/A) | 2/4 (50.0%) | 1/1 (100.0%) | 0/0 (N/A) |
| **FP Recall (`N=1` CS FP)** | 1/1 (100.0%) | 0/1 (0.0%) | 0/1 (0.0%) | 0/1 (0.0%) |
| **Missed-TP-as-FP (SOC Hazard)** | **9/9 (100.0%)** | **0/9 (0.0%)** | **0/9 (0.0%)** | **0/9 (0.0%)** |
| **FP-as-TP Error Rate** | 0/1 (0.0%) | **1/1 (100.0%)** | 0/1 (0.0%) | 0/1 (0.0%) |
| **Prisma `INCONCLUSIVE` Abstention** | 0/10 (0.0%) | 0/10 (0.0%) | **8/10 (80.0%)** | 10/10 (100.0%) |

## 2. Confusion Matrices (GT-2 Rows vs Predicted Columns)

### Mode A (Neutral Baseline): `20/20` `FALSE_POSITIVE` Collapse
- `TRUE_POSITIVE (9)`: TP=0, **FP=9**, REQ=0
- `FALSE_POSITIVE (1)`: TP=0, **FP=1**, REQ=0
- `INCONCLUSIVE (10)`: TP=0, **FP=10**, REQ=0

### Mode B (Policy-Assisted Raw LLM)
- `TRUE_POSITIVE (9)`: TP=**2**, FP=0, REQ=**7**
- `FALSE_POSITIVE (1)`: TP=**1**, FP=0, REQ=0
- `INCONCLUSIVE (10)`: TP=**1**, FP=**9**, REQ=**0**

### Mode C (`validated_verdict`)
- `TRUE_POSITIVE (9)`: TP=**1**, FP=0, REQ=**8**
- `FALSE_POSITIVE (1)`: TP=0, FP=0, REQ=**1**
- `INCONCLUSIVE (10)`: TP=0, FP=**2**, REQ=**8**

## 3. Confidence Calibration Failure

- **Mode A:** Emitted exact constant `confidence = 85.0%` on **20/20** predictions (`19/19` wrong answers had `>= 80%` confidence!).
- **Mode B:** Mean incorrect confidence = `71.94%`; `11/18` wrong answers had `>= 80%` confidence (e.g., `132499745` `TRUE_POSITIVE` at `95%`).
