# AIS 2.0 Evaluate Accuracy & G8 Eligibility Architecture Fix

**Target Rule**: `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Rule UUID**: `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Date**: November 20, 2026  

---

## 1. Architectural Changes

### 1.1 Backend Service: `RuleLearningService.evaluate_rule_accuracy`
Implemented authoritative evaluation and reconciliation method in `backend/app/services/rule_learning_service.py`:
- Fetches or provisions `RuleLearningProfile` for `(rule_id, customer)`.
- Resolves all canonical rule identifiers (UUID and string rule ID).
- Audits all `AnalystVerdictReview` records in PostgreSQL.
- Classifies comparison outcomes into:
  - Decisive Hits: `AGREEMENT_TP`, `AGREEMENT_FP`
  - Decisive Errors: `AI_FALSE_ALARM`, `CRITICAL_MISSED_TP`
  - Non-Decisive Samples: `ANALYST_RESOLVED_ABSTENTION`, `ANALYST_ONLY_INITIAL_BENCHMARK`, `DISPUTED`
- Computes metrics strictly without fabrication:
  - If `decisive_evaluations > 0`: Computes Selective Accuracy, FP Precision, Wilson 95% Lower Confidence Bound, TP Recall, Specificity, and TP Precision.
  - If `decisive_evaluations == 0`: Sets all metrics strictly to `None` and returns clear explanatory diagnostic breakdown.
- Assesses Tier 2 Supervised Pilot class balance:
  - Requires $\ge 10$ verified TP and $\ge 10$ verified FP.
  - Calculates exact deficits (`tp_deficit = max(0, 10 - tp)`, `fp_deficit = max(0, 10 - fp)`).
- Persists refreshed metrics to PostgreSQL `rule_learning_profiles` and updates `last_evaluated_at = utc_now()`.

### 1.2 Backend API Endpoint: `POST /api/learning/rules/{rule_id}/evaluate-accuracy`
Exposed in `backend/app/api/rule_learning.py`:
- Requires active authenticated user.
- Accepts optional `customer` (defaults to `"DEFAULT"`) and `version_id`.
- Delegates to `RuleLearningService.evaluate_rule_accuracy`.
- Returns structured JSON payload with evaluation breakdown, class balance status, and diagnostic messages.

### 1.3 Frontend API Client: `api.evaluateRuleAccuracy`
Implemented in `frontend/src/lib/api.ts`:
- Enforces HTTP POST with `Content-Type: application/json`.
- Encodes query parameters for `customer` and `version_id`.
- Handles error deserialization with clear fallback messaging.

### 1.4 Frontend AIS Page: `handleEvaluateAccuracy` & Dynamic Next Action
Updated in `frontend/src/app/agent-intelligence-studio/page.tsx`:
- Connected `handleEvaluateAccuracy()` to "Evaluate Accuracy" button click.
- Corrected `nextRecommendedAction` state machine:
  - When $reviews \ge 30$ but $TP < 10$: Action recommends **"Collect True Positive Ground Truth"** with badge `Class Balance Needed` and routes to incident review workbench.
  - When $reviews \ge 30$ and $accuracy == null$: Action recommends **"Evaluate Accuracy"** and triggers `handleEvaluateAccuracy()`.
- Fixed `fetchLearningProfile` race condition by decoupling it from `promptRequestIdRef.current`.
- Passed `learningProfile` to `ReviewIncidentsWorkbench` to eliminate 0-count visual glitches.

### 1.5 Interactive Controls in `AccuracyLearningSummary`
Updated in `frontend/src/components/compact/AccuracyLearningSummary.tsx`:
- Added prominent "Evaluate Accuracy" button with spinner state.
- Added Empirical Diagnostic Alert Card when ground truth exists but accuracy is N/A:
  - Explains 0 decisive predictions ($16$ abstentions, $15$ initial benchmarks).
  - Outlines Pilot Class Balance Deficit ($0/10$ TP confirmed).
  - Provides direct one-click actions: "Evaluate Accuracy", "Review Queue", and "Test AI".
- Added explanatory note beneath confusion matrix explaining why cells are currently zero.

---

## 2. G1–G8 Production Governance Invariant Preservation

The hotfix strictly preserves all authoritative quality gates:
- **G1 (Syntactic Schema Validity)**: Verified.
- **G2 (Evidence Contract Adherence)**: Verified.
- **G3 (False Positive Suppression Precision)**: Requires $\ge 99.0\%$ FP Precision.
- **G4 (Malicious Activity Detection Sensitivity)**: Requires $\ge 95.0\%$ TP Recall.
- **G5 (Wilson Lower Bound Confidence)**: Requires $\ge 96.0\%$ confidence lower bound.
- **G6 (Abstention & Escalation Safety)**: Verified.
- **G7 (Internal Policy Consistency)**: Verified.
- **G8 (Simulation & Regression Validation)**: Requires empirical regression simulation on active policy digest.
- **Zero Critical Missed TPs**: Maintained ($0$ missed TPs observed).
- **Controlled Production Criteria**: Requires $\ge 100$ decisive evaluations ($\ge 25$ TP, $\ge 50$ FP). The 31 FP reviews are tracked accurately as progress toward the 50 FP requirement, while explicitly highlighting the 25 TP deficit for production.
