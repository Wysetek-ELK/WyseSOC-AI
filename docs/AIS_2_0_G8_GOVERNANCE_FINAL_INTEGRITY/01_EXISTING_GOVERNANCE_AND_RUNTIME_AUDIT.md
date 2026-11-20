# Report 01 — Existing Governance and Runtime Audit
**Project**: Verdictum AI — Agent Intelligence Studio (AIS 2.0)  
**Task**: G8 Governance Integrity, Empirical Metrics & Final Deployment Verification  
**Date**: November 20, 2026  
**Status**: Authoritative Runtime Audit Completed  

---

## 1. Executive Summary

This audit establishes the ground-truth relationship between documented governance claims and actual runtime code implementations within Verdictum AI. Specifically, it resolves the discrepancies identified in previous documentation regarding sample sizes, empirical accuracy thresholds, and quality gate classifications.

---

## 2. Source-Backed Governance Comparison Matrix

| Governance Dimension | Previous Report 06 Text | Authoritative Backend Code | Frontend Runtime Implementation | Root Cause Classification | Reconciled Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Minimum Sample Size (Pilot)** | 10 cases | `MIN_PILOT_SAMPLES = 30`<br>(`MIN_PILOT_TP = 10`, `MIN_PILOT_FP = 10`) | `totalVerified >= 30` in `AccuracyLearningSummary.tsx` | **Defective Documentation**: Report 06 conflated the 10-case TP/FP pilot sub-cohort minimum with the total sample requirement. | **Reconciled**: 30 cases for Pilot (&ge;10 TP, &ge;10 FP). |
| **Minimum Sample Size (Production)** | Not distinguished from pilot | `MIN_PRODUCTION_SAMPLES = 100`<br>(`MIN_PRODUCTION_TP = 25`, `MIN_PRODUCTION_FP = 50`) | `RuleLearningDashboard.tsx` line 899: `&ge;100 eligible evaluations` | **Omission in Report 06**: Conflated pilot entry with production certification. | **Reconciled**: 100 cases (&ge;25 TP, &ge;50 FP) strictly enforced. |
| **Empirical Accuracy Threshold** | 85.0% | `MIN_PRODUCTION_ACCURACY = 0.95`<br>`MIN_PILOT_ACCURACY = 0.90` | `RuleLearningDashboard.tsx`: `Verified Accuracy &ge;95%` | **Defective Documentation**: 85% was an unverified informal draft figure; 95% is the active code threshold. | **Reconciled**: 95.0% Production threshold preserved without weakening. |
| **TP Recall Threshold** | 80.0% | `MIN_PRODUCTION_TP_RECALL = 0.95` | `RuleLearningDashboard.tsx`: `TP Recall &ge;95%` | **Defective Documentation**: 80% was an informal draft figure; 95% is the active code threshold. | **Reconciled**: 95.0% TP Recall preserved. |
| **FP Precision Threshold** | 80.0% | `MIN_PRODUCTION_FP_PRECISION = 0.99` | `RuleLearningDashboard.tsx`: `Observed FP Precision &ge;99%` | **Defective Documentation**: 80% was an informal draft figure; 99% is the active code threshold. | **Reconciled**: 99.0% FP-Class Precision preserved. |
| **Wilson Confidence Bound** | Omitted | `MIN_PRODUCTION_WILSON_LOWER = 0.96` | `RuleLearningDashboard.tsx`: `Wilson Lower Bound &ge;96%` | **Omission in Report 06**: Omitted from summary diagram. | **Reconciled**: 96.0% Wilson Lower Bound preserved. |
| **Critical Missed TP Gate** | Omitted | `MAX_CRITICAL_MISSED_TP = 0` | Triggers immediate suspension in `_trigger_critical_missed_tp_suspension` | **Authoritative Safety Invariant**: Zero missed TPs allowed in production. | **Reconciled**: Zero Missed TPs strictly enforced. |
| **G8 Gate Semantics** | "Non-Regression" | `G8_SIMULATION_REGRESSION`<br>Evaluates regression & empirical sample sufficiency | Multi-tier G8 status card in `AccuracyLearningSummary.tsx` | **Ambiguous Nomenclature**: G8 was labeled "Non-Regression" in quality validator, but "Empirical Validation" in readiness engine. | **Reconciled**: Unified definition: G8 requires both zero regression AND empirical validation. |
| **FP Precision Formula** | `TN / (TN + FP)` (Report 06) | `TN / (TN + FN)` (`agreed_fp / (agreed_fp + missed_tp)`) | `agreed_fp / (agreed_fp + missed_tp)` in `RuleLearningService` | **Defective Documentation**: Report 06 erroneously labeled Specificity (`TN / (TN + FP)`) as FP Precision. | **Reconciled**: FP Precision is $TN / (TN + FN)$; Specificity is $TN / (TN + FP)$. |

---

## 3. Discrepancy Analysis

### 1. Why Did Report 06 Document 10 Cases, 85% Accuracy, and 80% Thresholds?
During the development of the simplified overview, an informal design mock-up summarized entry criteria for preliminary exploratory reviews. When Report 06 was generated, the author inadvertently transcribed those informal mock-up parameters into the Mermaid architecture diagram instead of querying the authoritative constants defined in `RuleLearningService` and `ProductionReadinessService`.

### 2. Actual Runtime Reality
Inspection of the actual source code demonstrates that:
1. `RuleLearningService.MIN_PRODUCTION_SAMPLES` has **always been 100**.
2. `RuleLearningService.MIN_PRODUCTION_ACCURACY` has **always been 0.95 (95%)**.
3. `RuleLearningService.MIN_PRODUCTION_FP_PRECISION` has **always been 0.99 (99%)**.
4. `RuleLearningService.MIN_PRODUCTION_WILSON_LOWER` has **always been 0.96 (96%)**.
5. `RuleLearningService.MIN_PRODUCTION_TP_RECALL` has **always been 0.95 (95%)**.
6. `ProductionReadinessService` lines 236–246 enforce these exact constants without deviation.

The reported 85% and 80% figures never existed in the runtime engine and represented purely documentation-level transcription defects.

---

## 4. Protected Policy Baselines Runtime State

Direct verification from PostgreSQL confirmed the exact state of protected rules:

### 1. Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)
- **Canonical Rule ID**: `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
- **Active Version**: `v2 APPROVED` (Quality Score: 88.0, `was_ever_approved = True`).
- **Candidate Version**: `v3 DRAFT` (Quality Score: 88.0, candidate draft).
- **Status**: **PRESERVED & INTACT**.

### 2. Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)
- **Canonical Rule ID**: `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`
- **Active Version**: `v7 APPROVED` (Quality Score: 92.0, `was_ever_approved = True`).
- **Candidate Version**: `v8 DRAFT` (Quality Score: 92.0, candidate draft).
- **Status**: **PRESERVED & INTACT**.

---

## 5. Audit Conclusion
The runtime engine implements rigorous, mathematically sound, fail-closed production certification controls. The discrepancies identified were documentation transcription errors in Report 06, which are now formally corrected and reconciled across all artifacts.
