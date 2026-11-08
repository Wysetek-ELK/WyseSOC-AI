# 08. SIMULATION AND REGRESSION APPROVAL

## Overview

In Agent Intelligence Studio 2.0, policy quality is not validated solely by static text analysis. The `PolicySimulationService` (`backend/app/services/policy_simulation_service.py`) connects policy generation directly to the **Simulation Lab** to perform empirical historical backtesting. Gate **G8** evaluates candidate policies against historical incidents with verified ground truth before production promotion.

---

## Historical Backtesting Workflow

```text
+-------------------------------------------------------------------------+
|                    HISTORICAL BACKTESTING WORKFLOW                      |
|                                                                         |
|  [ Candidate Policy Draft ]                                             |
|             |                                                           |
|             v                                                           |
|  [ Query Historical Incidents for Rule ID ]                             |
|  (Filter by verified ground truth labels: TP, FP)                       |
|             |                                                           |
|             +---------> [ Sample Count < 5 ]                           |
|             |           - Return status: INSUFFICIENT_DATA              |
|             |           - Gate G8 issues non-blocking warning.          |
|             |           - Quality score receives -5 penalty.            |
|             |           - Does NOT hard-block new rules.                |
|             v                                                           |
|  [ Sample Count >= 5 ]                                                  |
|             |                                                           |
|             v                                                           |
|  [ Replay Triage Simulation with Candidate Policy ]                     |
|             |                                                           |
|             v                                                           |
|  [ Compare against Active Baseline Policy Performance ]                 |
|             |                                                           |
|             +---------> [ Accuracy Regresses > 2.0% ]                  |
|             |           - Return status: REGRESSION_DETECTED            |
|             |           - Gate G8 FAILS.                                |
|             |           - Approval BLOCKED.                             |
|             v                                                           |
|  [ Accuracy Maintained or Improved ]                                    |
|             - Return status: PASSED                                     |
|             - Gate G8 PASSES.                                           |
+-------------------------------------------------------------------------+
```

---

## Handling the Cold-Start Problem: `INSUFFICIENT_DATA`

A major risk in automated governance is the "cold-start" trap: if a brand-new SIEM detection rule is introduced, there are zero historical incidents in the database. If a regression check required 100 historical incidents to pass, no new rule could ever be approved.

AIS 2.0 solves this safely:
- When available historical incidents $N < 5$:
  - Status is set to `INSUFFICIENT_DATA`.
  - Gate G8 passes with a documented warning:
    ```json
    {
      "gate_id": "G8",
      "status": "PASSED",
      "score": 0.8,
      "details": "Insufficient historical incident samples (N=0 < 5). Regression check waived with caution warning."
    }
    ```
  - The policy draft is NOT hard-blocked from SOC Lead approval.
  - The UI displays an amber advisory flag reminding the SOC Lead that the policy is operating on limited historical validation.

---

## Regression Criteria ($N \ge 5$)

When 5 or more ground-truth incidents exist, the simulation evaluates:
1. **True Positive Recall:** Did the candidate policy classify all verified malicious incidents as True Positive?
2. **False Positive Specificity:** Did the candidate policy correctly dismiss verified benign operations?
3. **Abstention Rate:** Did the candidate policy produce unnecessary abstentions on complete telemetry?

If candidate accuracy drops by more than $2.0\%$ compared to the currently active production version:
- Gate G8 fails immediately with finding: `REGRESSION_DETECTED: Candidate policy accuracy (80.0%) dropped below active baseline (85.0%).`
- `approval_eligible` is set to `False`.
- The draft cannot be approved until refined.
