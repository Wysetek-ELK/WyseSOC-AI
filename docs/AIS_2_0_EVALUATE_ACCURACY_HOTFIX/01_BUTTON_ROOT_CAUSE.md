# AIS 2.0 Evaluate Accuracy Button & Readiness Root Cause Analysis

**Target Rule**: `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Rule UUID**: `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Active Baseline**: `v7 APPROVED` (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`)  
**Candidate Revision**: `v8 DRAFT` (`20d4f788-85a5-437d-afbe-fe7fd80abca1`)  
**Date**: November 20, 2026  

---

## 1. Executive Summary

Investigation into the observed defect where clicking **Evaluate Accuracy** in Verdictum AI → Agent Intelligence Studio produced no user response, and where 31 verified analyst reviews resulted in zero measurable accuracy with an all-zero confusion matrix, revealed two distinct, compounding root causes:

1. **Frontend Action Inertia & Missing Evaluation Endpoint**: The "Evaluate Accuracy" button action in `frontend/src/app/agent-intelligence-studio/page.tsx` (lines 1906–1917) was implemented solely as `() => { setPrimaryTab("learning"); }`. When an analyst clicked the button while already viewing the *Accuracy & Learning* tab, nothing happened. No backend evaluation was triggered, no API call was dispatched, and no calculation occurred.
2. **Mathematical Indeterminacy in Selective Accuracy**: Under Verdictum AI mathematical governance, Selective Accuracy is defined as `(TP + TN) / (TP + TN + FP + FN)`. Decisive outcomes require a model prediction (TP or FP) matched against human ground truth. All 31 analyst reviews in the database were `FALSE_POSITIVE`. Of those 31 reviews, 16 resolved AI abstentions (`REQUIRES_ATTENTION`), and 15 were initial benchmarks without prior AI inference (`ANALYST_ONLY_INITIAL_BENCHMARK`). Because decisive paired predictions equaled exactly zero, the denominator was zero, rendering empirical accuracy mathematically undefined (`null` / `N/A`) and all confusion matrix cells zero.
3. **Transient State Clearing via Shared Request ID**: In `page.tsx`, `fetchLearningProfile` was gated by `reqId !== promptRequestIdRef.current`. Because `fetchPrompt` concurrently incremented `promptRequestIdRef.current`, `fetchLearningProfile` occasionally discarded its freshly fetched profile, causing the UI to intermittently render `Reviewed: 0` and `Accuracy & Learning (0)`.

---

## 2. Code Trace & Failure Path

### 2.1 The Nonfunctional Button
In `frontend/src/app/agent-intelligence-studio/page.tsx`:
```tsx
// DEFECTIVE IMPLEMENTATION:
if (learningProfile && learningProfile.empirical_accuracy === null) {
  return {
    label: "Evaluate Accuracy",
    description: "30+ verified analyst reviews collected. Compute empirical accuracy and confusion matrix.",
    action: () => {
      setPrimaryTab("learning"); // <-- No-op when already on learning tab!
    },
    buttonText: "Evaluate Accuracy",
    badge: "Evaluation Ready",
    badgeColor: "bg-teal-950/80 text-teal-300 border-teal-800",
  };
}
```
**Impact**:
- The analyst sees the call-to-action banner: "Evaluate Accuracy — 30+ verified analyst reviews collected. Compute empirical accuracy and confusion matrix."
- The analyst clicks the button.
- React executes `setPrimaryTab("learning")`.
- Since `primaryTab` is already `"learning"`, state is unchanged. No loading spinner, no network request, and no calculation occurs.

### 2.2 Missing Evaluation Endpoint
Neither `backend/app/api/rule_learning.py` nor `backend/app/api/prompts.py` provided an endpoint for explicitly triggering evaluation or recalculating accuracy against current ground truth. Metrics were only updated passively inside `AnalystReviewService.record_analyst_feedback` during individual submission.

### 2.3 The `promptRequestIdRef` Race Condition
```tsx
// DEFECTIVE RACE CONDITION:
const fetchLearningProfile = async (ruleId: string) => {
  if (!ruleId) { setLearningProfile(null); return; }
  const reqId = promptRequestIdRef.current;
  try {
    const data = await api.getRuleLearningProfileDetail(ruleId);
    if (reqId !== promptRequestIdRef.current) return; // <-- Drops profile if prompt increments ref!
    setLearningProfile(data);
  } catch {
    if (reqId !== promptRequestIdRef.current) return;
    setLearningProfile(null);
  }
};
```
Whenever `fetchPrompt` ran concurrently, `++promptRequestIdRef.current` invalidated `reqId`, silently dropping the loaded learning profile and leaving `learningProfile` as `null` or 0 in the UI.

---

## 3. Remediation Strategy

1. **Expose Dedicated Backend Endpoint**: Implement `POST /api/learning/rules/{rule_id}/evaluate-accuracy` in `rule_learning.py` and `RuleLearningService.evaluate_rule_accuracy`.
2. **Reconcile Decisive Paired Predictions**: Audit all `AnalystVerdictReview` records, compute decisive evaluations, Wilson confidence intervals, and class balance status without fabricating metrics.
3. **Wire Frontend Click Handler**: Implement `handleEvaluateAccuracy()` in `page.tsx`, trigger `api.evaluateRuleAccuracy()`, show toast feedback, and refresh profile state.
4. **Add Interactive Controls in `AccuracyLearningSummary`**: Add prominent "Evaluate Accuracy" buttons and a clear diagnostic alert explaining why accuracy is N/A when decisive evaluations equal zero.
5. **Eliminate Request ID Interference**: Decouple `fetchLearningProfile` from `promptRequestIdRef.current` and pass `learningProfile` as prop to `ReviewIncidentsWorkbench` to eliminate 0-count visual glitches.
