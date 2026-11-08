# Simulation Lab & Paired Regression Analysis (AIS 2.1)

## 1. Overview and Core Purpose

In production detection engineering, updating an LLM prompt or investigation policy often introduces subtle regressions—improving accuracy on one sub-scenario while silently failing on another (e.g., catching more cloud backup flows but suddenly missing small-volume slow exfiltrations).

The **Simulation Lab Regression Engine** (`backend/app/services/policy_simulation_service.py`) conducts **paired regression evaluations**. It executes candidate and baseline policies against the **exact same historical incident cohort** under identical blind test conditions, comparing verdict distributions and safety metrics.

---

## 2. Paired Simulation Architecture

```
                          [ Historical Incidents Cohort ]
                                         |
                                         v
                         [ Zero-Leakage Sanitization ]
                                         |
                    +--------------------+--------------------+
                    |                                         |
                    v                                         v
        +-----------------------+                 +-----------------------+
        |    Baseline Policy    |                 |   Candidate Policy    |
        +-----------------------+                 +-----------------------+
                    |                                         |
                    v                                         v
        [ Baseline Inference ]                    [ Candidate Inference ]
                    |                                         |
                    v                                         v
        [ Sufficiency & Guardrails ]              [ Sufficiency & Guardrails ]
                    |                                         |
                    v                                         v
        [ Baseline Evaluation Run ]               [ Candidate Evaluation Run ]
                    |                                         |
                    +--------------------+--------------------+
                                         |
                                         v
                          [ Paired Regression Comparator ]
                                         |
                   +---------------------+---------------------+
                   |                     |                     |
                   v                     v                     v
              VALIDATED          REGRESSION_DETECTED     INSUFFICIENT_DATA
```

---

## 3. Regression Triggers and Gating Rules

A candidate policy is flagged as `REGRESSION_DETECTED` if any of the following statistical conditions are met:

1. **Balanced Accuracy Degradation**:
   $\text{Balanced Accuracy}_{\text{candidate}} < \text{Balanced Accuracy}_{\text{baseline}} - 0.05$ (a drop of 5 percentage points or more).
2. **Introduction of New False Negatives**:
   A true positive incident that was correctly identified by the baseline policy is misclassified as a `FALSE_POSITIVE` by the candidate policy. In security operations, an undetected intrusion is a catastrophic regression.
3. **Elevated Hallucination Rate**:
   $\text{Unsupported Claims Count}_{\text{candidate}} > \text{Unsupported Claims Count}_{\text{baseline}} + 2$.
4. **Severe Abstention Ballooning**:
   Candidate policy abstention rate spikes by more than 25 percentage points without an increase in telemetry missingness.

If the evaluated cohort contains fewer than 10 incidents, the comparison status is classified as `INSUFFICIENT_DATA` rather than passing blindly.

---

## 4. Regression Report Output Schema

The `compare_runs` method produces a `RegressionComparisonReport` containing:

```json
{
  "baseline_run_id": "run-base-101",
  "candidate_run_id": "run-cand-102",
  "status": "VALIDATED",
  "accuracy_delta": 0.045,
  "ece_delta": -0.032,
  "trust_score_delta": 0.8,
  "unsupported_claims_delta": -2,
  "new_false_negatives_count": 0,
  "new_false_positives_count": 0,
  "sample_overlap_count": 50,
  "details": "Candidate policy improved balanced accuracy by 4.5% while reducing ECE by 0.032 with zero newly introduced false negatives."
}
```

This structured report enables detection engineers to safely review and validate policy iterations before proposing them for SOC lead approval.
