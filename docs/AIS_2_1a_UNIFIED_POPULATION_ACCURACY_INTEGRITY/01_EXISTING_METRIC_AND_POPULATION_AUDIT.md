# 01 — Existing Metric and Population Audit

**Verdictum AI — Agent Intelligence Studio (AIS) 2.1a Hotfix**  
**Target Rule:** Heavy TCP Host Scan On Fixed Port  
**Canonical Rule UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Approved Baseline Policy:** Version v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`)  
**Audit Timestamp:** 2026-11-21T11:15:00+05:30  
**Audit Target:** Live Production Server 1 (`http://172.26.41.240:3000`) & Local Repository  

---

## 1. Executive Summary

This audit establishes the empirical ground truth and source of truth across Server 1's live PostgreSQL database, FastAPI backend services (`AisEvaluationService`, `RuleLearningService`, `AnalystReviewService`), and Next.js frontend components (`AccuracyLearningSummary.tsx`, `AiTestWorkbench.tsx`, `ReviewIncidentsWorkbench.tsx`).

Prior to this hotfix, the user interface presented contradictory numbers:
- **Accuracy Top Banner:** `13 Reviews (0 TP / 45 FP)` — an impossible mathematical statement where 45 false positives were displayed within a population of 13 reviews.
- **Population Discrepancy:** 13 incidents displayed in the AI Evaluation Tracking table vs 32 human reviews cited in historical learning reports vs 45 verified reviews stored in the database vs 56/69 cumulative evaluation events.
- **Automated Acceptance Assertion Failure:** `gui_acceptance_results.json` showed `hasNotMeasurable = false` despite the UI attempting to show "Not Measurable".
- **Fixture Provenance Ambiguity:** References to patterned UUIDs (`10000000-...` and `20000000-...`) raised concerns about potential test fixture poisoning in production evaluation metrics.

---

## 2. Server 1 Live Database Inventory Audit

Direct live database queries executed against Server 1 via authenticated endpoints revealed the exact operational reality:

### Table 1: Operational Database Counts for Heavy TCP Rule (`40498741-ee6b-4a71-9101-0d6d3f77154c`)

| Database Entity | Target Table | Live Record Count | Description & Tenant Breakdown |
|---|---|---:|---|
| **Incident Records** | `incidents` | **13** | Current operational SIEM incidents: 11 for `Demo-SOC`, 2 for `GDC_NOC`. Incident IDs: #335, #543, #546, #595, #664, #705, #729, #841, #1477, #2339, #7411, #7422, #7475. |
| **Analyst Reviews** | `analyst_verdict_reviews` | **45** | 32 historical baseline reviews + 13 reviews on current operational incidents. 100% of verified reviews are `FALSE_POSITIVE` (0 TP / 45 FP). |
| **Model Prompt Captures** | `actual_llm_prompt_captures` | **26+** | Real Local LLM prompt captures under policy v7 (`Qwen/Qwen2.5-7B-Instruct-AWQ`). |
| **Trust Assessments** | `verdict_trust_assessment_records` | **26+** | Governed trust assessments confirming effective verdict `REQUIRES_ATTENTION` (abstained under v7). |
| **Rule Learning Profile** | `rule_learning_profiles` | **1** | Rule learning profile for Heavy TCP rule (`total_analyst_reviews = 45`, `verified_fp_count = 45`, `verified_tp_count = 0`). |
| **Patterned Test Fixtures** | Operational tables | **0** | **Zero** patterned test UUIDs exist in the live database. |

---

## 3. Root Cause Analysis of Observed Defects

### Issue A: Contradictory Analyst Review Totals (`13 Reviews (0 TP / 45 FP)`)
- **Location:** `frontend/src/components/compact/AccuracyLearningSummary.tsx` (Lines 118-125 in previous revision).
- **Mechanism:** The component assigned `totalVerified = evalSummary.matched_verified_reviews` (which returns 13 from current incident inventory), but extracted `verifiedFp = profile.verified_fp_count` (which returns 45 from the historical learning profile).
- **Result:** The UI concatenated `totalVerified` (13) with `profile.verified_tp_count` (0) and `profile.verified_fp_count` (45), creating the mathematically invalid display: `"13 Reviews (0 TP / 45 FP)"`.
- **Root Cause:** Conflation of two separate populations (Current Incident Inventory vs. Cumulative Historical Cohort) into a single display line without population boundaries or mathematical reconciliation.

### Issue B: Population Scope Mismatch (13 vs 32 vs 45 vs 56 vs 69)
- **13 Incidents:** The exact distinct count of current operational SIEM incidents present in the `incidents` table for `40498741-ee6b-4a71-9101-0d6d3f77154c` across active tenants `Demo-SOC` and `GDC_NOC`.
- **32 Reviews:** An earlier historical acceptance batch of analyst ground-truth reviews recorded prior to the ingestion and review of the 13 current operational incidents.
- **45 Reviews:** The current cumulative sum of all verified analyst ground truth: 32 historical + 13 current = 45 verified reviews.
- **56 Events:** Cumulative processed events recorded in `RuleLearningProfile` at the time of the previous acceptance audit (comprising 32 reviews + 24 intermediate evaluation attempts).
- **69 Events:** Current cumulative processed events: 56 historical + 13 current = 69 events.
- **Root Cause:** Backend endpoints returned metrics from differing snapshot scopes without explicit scope metadata identifying whether a counter belonged to the current incident inventory or the cumulative historical profile.

### Issue C: Browser Acceptance Assertion Discrepancy (`hasNotMeasurable = false`)
- **Location:** `scripts/run_ais_2_1a_gui_acceptance.mjs` (Line 264 in previous revision).
- **Mechanism:** The acceptance test asserted `text.includes('Not Measurable') || text.includes('No eligible decisive')`.
- **Failure Cause:** In the DOM, the banner rendered in uppercase `NOT MEASURABLE` and the explanatory text read `0 eligible decisive AI predictions were found`, causing the strict case-sensitive and string-exact check to return `false`.
- **Root Cause:** Fragile string matching in the automated verification script that did not account for DOM case transformations or minor phrasing variations.

### Issue D: Patterned Fixture Provenance (`10000000-...`, `20000000-...`)
- **Investigation:** Grep across the codebase revealed that patterned UUIDs were utilized exclusively in unit test mock suites (`test_ais_evaluation_tracking.py`, legacy mock data).
- **Live DB Verification:** A query against `http://172.26.41.240:3000/api/ais/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/evaluation-tracking` confirmed that 0 patterned UUIDs exist in operational tables.
- **Preventive Guard:** Added regex filters (`^[0-9]0000000-0000-0000-0000-[0-9a-f]{12}$`) in `RuleLearningService` and `AisEvaluationService` to ensure any synthetic test fixtures are categorically excluded from certified production evaluation metrics.

---

## 4. Audit Conclusion

The underlying data on Server 1 is sound, authentic, and free of synthetic fixture poisoning. The observed discrepancies were entirely caused by frontend metric mixing and missing population scope boundaries in backend responses. Implementing a centralized dual-scope population contract cleanly resolves all 4 issues.
