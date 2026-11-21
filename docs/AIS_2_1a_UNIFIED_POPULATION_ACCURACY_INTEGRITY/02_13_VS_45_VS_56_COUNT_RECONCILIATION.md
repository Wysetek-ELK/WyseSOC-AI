# 02 — Count Reconciliation: 13 vs 32 vs 45 vs 56 vs 69

**Verdictum AI — AIS 2.1a Unified Population Hotfix**  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Timestamp:** 2026-11-21T11:15:30+05:30  
**Status:** FULLY RECONCILED  

---

## 1. Discrepancy Overview

Previous acceptance documents and screenshots exhibited differing counts:
1. **13 Incidents** in AI Evaluation Tracking.
2. **32 Reviews** cited in historical acceptance reports.
3. **45 Reviews** cited in the database and current Accuracy card.
4. **56 Events** cited in historical cumulative counters.
5. **69 Events** cited in current cumulative processed counters.

This document establishes the empirical provenance of each number and proves that they do not conflict when properly scoped to their respective populations and timelines.

---

## 2. Definitive Population Breakdown

### Population A: Current Operational Incident Inventory (Count = 13)
- **Source:** PostgreSQL `incidents` table queried by `rule_id = '40498741-ee6b-4a71-9101-0d6d3f77154c'`.
- **Tenants:**
  - `Demo-SOC`: 11 incidents (#335, #543, #546, #595, #664, #705, #729, #841, #1477, #7411, #7475).
  - `GDC_NOC`: 2 incidents (#2339, #7422).
- **Incident Status:** Ingested from live SIEM, normalized, investigated, and reviewed by SOC analysts.
- **Analyst Determinations:** All 13 incidents reviewed as `FALSE_POSITIVE` (0 TP, 13 FP).
- **AI Determinations under v7:** All 13 incidents evaluated as `REQUIRES_ATTENTION` (0 decisive, 13 abstentions).
- **Decisive Comparisons:** 0 decisive predictions.

### Population B: Historical Learning Baseline (Count = 32 Reviews)
- **Source:** Pre-existing analyst review submissions from earlier system training phases before the current 13 operational incidents were imported.
- **Breakdown:** 32 verified reviews, all `FALSE_POSITIVE` (0 TP, 32 FP).
- **AI Status at Review Time:**
  - 17 reviews resolved AI abstentions.
  - 15 reviews were initial human baseline benchmarks before AI inference was stored.

### Population C: Cumulative Historical Ground Truth (Count = 45 Reviews)
- **Mathematical Formula:**
  $$\text{Cumulative Reviews} = \text{Historical Baseline (32)} + \text{Current Operational Reviews (13)} = 45$$
- **Ground Truth Distribution:**
  - Verified TP: $0$
  - Verified FP: $32 + 13 = 45$
  - Disputed / Unresolved: $0$
  - Mathematical Invariant: $0 \text{ TP} + 45 \text{ FP} = 45 \text{ Total Verified}$ (100% consistent).

### Population D: Cumulative Processed Events (56 vs 69 Events)
- **Historical Event Count (56):** Cumulative events processed at the conclusion of AIS 2.0 initial rollout (32 reviews + 24 intermediate inference and telemetry events).
- **Current Event Count (69):**
  $$\text{Current Processed Events} = 56 \text{ (historical)} + 13 \text{ (current operational reviews)} = 69$$
- **Event Composition (69 total):**
  - 30 analyst-resolved AI abstentions (17 historical + 13 current).
  - 15 initial human benchmarks without stored inference.
  - 24 intermediate model execution & telemetry evaluations.

---

## 3. Comprehensive Diagnostic Reconciliation Matrix

| Population Scope | Entity / Table | Unique Incidents | Record Count | Ground Truth (TP / FP) | AI Status (Decisive / Abstained / Missing) | Authoritative Source |
|---|---|---:|---:|:---:|:---:|---|
| **Current Operational Inventory** | `incidents` | **13** | 13 | 0 TP / 13 FP | 0 Decisive / 13 Abstained / 0 Missing | PostgreSQL `incidents` |
| **Current Operational Reviews** | `analyst_verdict_reviews` | **13** | 13 | 0 TP / 13 FP | 0 Decisive / 13 Abstained / 0 Missing | PostgreSQL `analyst_verdict_reviews` |
| **Historical Baseline Reviews** | `analyst_verdict_reviews` | **32** | 32 | 0 TP / 32 FP | 0 Decisive / 17 Abstained / 15 Missing | Early training database records |
| **Cumulative Historical Cohort** | `rule_learning_profiles` | **45** | 45 | 0 TP / 45 FP | 0 Decisive / 30 Abstained / 15 Missing | PostgreSQL `rule_learning_profiles` |
| **Real AI Inference Captures** | `actual_llm_prompt_captures` | **13** | 26+ | N/A | 0 Decisive / 26+ Abstained (v7) | PostgreSQL `actual_llm_prompt_captures` |
| **Decisive Matched Cohort** | Matched (Analyst $\cap$ AI) | **0** | 0 | 0 TP / 0 FP | **0 Decisive Predictions** | AIS Reconciliation Engine |

---

## 4. Why 13 and 45 Can Both Be Correct When Scoped

- It is completely valid for an application to display **13 Incidents** when referring to the **Current Operational Incident Inventory**.
- It is equally valid for the application to display **45 Verified Reviews** when referring to the **Cumulative Historical Ground Truth Cohort**.
- The critical defect in AIS 2.1 was conflating them in a single string: `"13 Reviews (0 TP / 45 FP)"`.
- In AIS 2.1a, with the dual-population segmented toggle, each view strictly guarantees mathematical consistency:
  - **Current Scope Selected:** Displays `13 Incidents (0 TP / 13 FP)`.
  - **Historical Scope Selected:** Displays `45 Reviews (0 TP / 45 FP)`.
- Neither scope ever displays inconsistent or contradictory counts.
