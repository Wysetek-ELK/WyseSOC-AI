# AIS 2.2 Report 04: Benchmark Design & Leakage Controls

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** COMPLETE & AUDITED  

---

## 1. Deterministic Dataset Selection & Splitting

To ensure reproducibility across evaluation runs, dataset partitioning was implemented using a fixed pseudo-random seed (`seed = 42`) and recorded in `BENCHMARK_MANIFEST.json`.

### Dataset Cohorts

| Cohort Name | Purpose | Allocation | Incidents |
|---|---|---|---|
| **Development / Tuning Cohort** | Prompt engineering, contract refinement, and error analysis. | 30% | 6 Incidents |
| **Validation Cohort** | Hyperparameter validation and guardrail calibration. | 30% | 6 Incidents |
| **Held-Out Blind Benchmark Cohort** | Final authoritative evaluation of model accuracy and abstention. | 40% | 8 Incidents |

---

## 2. Anti-Data-Leakage Safeguards

A critical requirement of AIS 2.2 is ensuring that the local LLM never observes historical analyst determinations, ticket closure notes, or ground-truth hints during prompt compilation.

### 2.1 Sanitization Strategy
`HistoricalGroundTruthValidator.sanitize_incident_for_inference` applies recursive deep-stripping across all dictionary keys and nested lists:
- `incidentResDescription` (Analyst resolution text)
- `clearedReason` (FortiSIEM closure reason code)
- `clearedUser` / `cmsClearUser` (Identity of the clearing analyst)
- `clearedTime` (Epoch timestamp of resolution)
- `incidentComments` (Analyst investigation comments)
- `ticketStatus` / `status_name` (Ticket state)
- `analyst_verdict` / `analyst_notes` / `resolution_notes`

### 2.2 Audit & Verification
All 20 historical incident JSON fixtures were audited using recursive key inspection against `_NORMALIZED_LEAKAGE_KEYS`:
- Total incidents audited: 20
- Total data leaks detected: **0**
- Sanitization success rate: **100.0%**

---

## 3. Duplicate Detection & Quarantine

In historical SIEM telemetry, repeated alerts triggered by the same recurring scanner or automated task can inflate benchmark scores if present across both development and test splits.

A cluster analysis was performed grouping incidents by `(rule_name, event_structure_hash)`:
- **4 Duplicate Clusters** were identified in the historical dataset.
- In each cluster, the primary incident was retained for evaluation, while identical subsequent occurrences were quarantined in `BENCHMARK_MANIFEST.json` under `duplicate_quarantine`.
- This ensures that near-duplicates cannot artificially skew model generalization metrics.

---

## 4. Immutable Benchmark Manifest

The complete specification, cohort membership, SHA256 hashes, and quarantine records are committed to:
`docs/AIS_2_2/BENCHMARK_MANIFEST.json`

Every incident payload has an immutable SHA256 integrity hash recorded prior to inference.
