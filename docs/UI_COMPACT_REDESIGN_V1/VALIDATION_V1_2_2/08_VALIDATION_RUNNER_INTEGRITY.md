# VERDICTUM AI — VALIDATION V1.2.2
## 08. VALIDATION RUNNER INTEGRITY & ASSERTION ENFORCEMENT

**Document Version:** 1.0.0  
**Runner Target:** `scripts/run_v1_2_2_validation.mjs`  
**Status:** AUDITED, REPAIRED & VERIFIED  

---

### 1. Defect Analysis of Previous Runners

In Validation V1.2.1, two critical test runner integrity flaws allowed invalid states to be reported as passing:

1. **Hardcoded `isValid: true`:**
   In `run_v1_2_1_validation.mjs`, several scenarios computed sub-assertions (such as `hasGateScore = false`) but returned `isValid: true` directly in the return object, bypassing the evaluated assertion logic.
2. **Ambiguous String Matching:**
   In Blind Review testing, `textContent.includes('Blind Review')` was used. Because the header contains a toggle button that displays `"Blind Review: OFF"` when inactive, the assertion matched the string `"Blind Review"` even when the feature was disabled, falsely marking Blind Review as active.
3. **Premature Evaluation Before Next.js Compilation:**
   Running tests immediately after process start without establishing origin session state caused initial requests to redirect to `/login` before DOM elements settled.

---

### 2. Architectural Corrections in V1.2.2 Runner

#### A. Strict Boolean Evaluation
Every scenario in `scripts/run_v1_2_2_validation.mjs` computes individual boolean sub-assertions, and assigns `isValid` strictly to their conjunction:
```javascript
const allPassed = Boolean(hasStage1Blocked && hasStage2Blocked && hasNoContradictionText && isApproveDisabled);
return {
  hasStage1Blocked,
  hasStage2Blocked,
  hasScore77,
  hasNoContradictionText,
  isApproveDisabled,
  isValid: allPassed
};
```
If **any** single assertion evaluates to `false`, `allPassed` evaluates to `false`, and the scenario status is marked as `FAIL`.

#### B. Fail-Fast Exit Code
At completion, the runner checks:
```javascript
if (evidencePayload.status !== "PASS") {
  console.error("FAIL: One or more validation scenarios failed assertions!");
  process.exit(1);
}
```
A non-zero exit code halts automated pipelines immediately upon any assertion breach.

#### C. Dedicated Session Context & Origin Warm-up
The runner now navigates to `${BASE_URL}/login` before evaluating any scenario to establish the domain context, preventing `about:blank` localStorage isolation issues.
