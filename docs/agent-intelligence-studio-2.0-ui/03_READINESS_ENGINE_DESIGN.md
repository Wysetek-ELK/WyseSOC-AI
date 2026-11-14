# 03 - Production Readiness Engine Design

## 1. Architectural Principles

The `ProductionReadinessService` (`backend/app/services/production_readiness_service.py`) acts as the single authoritative backend engine for computing rule readiness across Verdictum AI. It eliminates heuristic guesswork and client-side inference by rigorously evaluating detection semantics, evidence contracts, quality gates, ground truth calibration, and empirical simulation replay.

### Core Non-Negotiable Rules:
1. **Never Treat Missing Data as PASS:** If evidence or review count is absent, status is `BLOCKED` or `NEEDS_ACTION`, never `COMPLETED`.
2. **Never Treat N/A Accuracy as Zero or PASS:** When sample count is below the minimum statistical threshold, empirical accuracy is `N/A`.
3. **Never Treat Raw Field Presence as Semantic Verification:** Field existence does not satisfy Gate G1 or G3 if correlation conditions are unverified.
4. **Never Treat an Offline LLM as Successful Validation:** Simulation replay must record actual provider provenance (`OPENAI_COMPATIBLE` vs `SIMULATED`). Simulated replay cannot substitute for verified live benchmark gates.
5. **Never Treat Draft Generation as Production Approval:** An intelligent draft is strictly provisional until reviewed and formally approved by an authorized administrator.
6. **Strict Separation of Readiness and Deployment:** A rule's SIEM ingestion status (`Rule.status`) and its AI policy readiness (`readiness_status`) are independent lifecycle concepts.

---

## 2. Readiness State Machine

```
+----------------------------------------------------------------------------------------------------+
|                                    READINESS STATE MACHINE                                         |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    +----------------+                                                                              |
|    |   INCOMPLETE   |  <-- Missing SIEM semantics, threshold, or mandatory contract fields         |
|    +----------------+                                                                              |
|            |                                                                                       |
|            v                                                                                       |
|    +----------------+                                                                              |
|    |    BLOCKED     |  <-- Quality Gate G1-G7 failure, unacknowledged drift, or blocking issue      |
|    +----------------+                                                                              |
|            |                                                                                       |
|            v                                                                                       |
|    +----------------+                                                                              |
|    |    LEARNING    |  <-- Gates G1-G7 passed; collecting double-blind analyst ground-truth        |
|    +----------------+      (0 - 29 verified reviews)                                               |
|            |                                                                                       |
|            v                                                                                       |
|    +----------------+                                                                              |
|    |   VALIDATING   |  <-- >= 30 verified reviews; executing empirical simulation replay           |
|    +----------------+      (Testing FP Precision >=98%, Wilson >=96%, TP Recall >=95%)             |
|            |                                                                                       |
|            v                                                                                       |
|    +--------------------+                                                                          |
|    | READY_FOR_APPROVAL |  <-- All 8 gates passed, empirical benchmarks met; awaiting Admin signoff|
|    +--------------------+                                                                          |
|            |                                                                                       |
|            v                                                                                       |
|    +----------------+                                                                              |
|    |    APPROVED    |  <-- Formally approved by Administrator; bound by cryptographic digests      |
|    +----------------+                                                                              |
|            |                                                                                       |
|            v                                                                                       |
|    +----------------+                                                                              |
|    |     ACTIVE     |  <-- Approved version promoted and actively triaging live SIEM incidents     |
|    +----------------+                                                                              |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. The 6 Guided Checklist Stages

The service aggregates underlying technical gates into 6 human-readable stages:

| Stage ID | Human-Readable Name | Underlying Backend Checks | Completion Condition | Failure / Blocker Triggers |
|---|---|---|---|---|
| `define_detection` | 1. Define Detection | `RuleIntelligenceAnalyzer`, Semantics Resolver, Gate G1 | Rule definition status is `VERIFIED`; trigger threshold and aggregation window defined. | Rule lacks threshold logic; pattern logic unparsed; missing definition. |
| `verify_evidence` | 2. Verify Evidence | Machine Evidence Contract, Gates G2 & G3 | All mandatory core fields for archetype present; raw telemetry compatible. | Missing required telemetry fields; unmapped archetype attributes. |
| `validate_policy` | 3. Validate AI Policy | `PolicyQualityValidator`, Gates G4, G5, G6, G7 | Syntactic compilation passed; TP/FP indicators explicit; quality score ≥70 without hard blockers. | Incomplete policy sections; ambiguous indicators; missing abstention guidance. |
| `analyst_learning` | 4. Analyst Learning | `RuleLearningService`, Double-Blind Queue | ≥30 verified reviews for pilot; ≥100 verified reviews for production. | Insufficient sample size; unadjudicated disputes. |
| `test_accuracy` | 5. Test AI Accuracy | Simulation Replay, Gate G8 | Empirical FP Precision ≥0.98, Wilson Lower Bound ≥0.96, TP Recall ≥0.95; zero critical false negatives. | Replay accuracy below threshold; critical missed attack; regression detected. |
| `production_approval` | 6. Production Approval | `PromptStudioService.approve_version` | Server-side gate re-evaluation clean; cryptographically bound digests; approved by Admin. | Unapproved candidate; pending review blockers; unverified promotion request. |

---

## 4. Smart Next Action Derivation

The service implements a deterministic cascade to select exactly one prioritized next action:

```python
if definition_incomplete:
    return SmartNextAction(
        title="Verify FortiSIEM Detection Semantics",
        target_tab="advanced", target_section="intelligence", action_type="NAVIGATE"
    )
elif contract_missing_fields:
    return SmartNextAction(
        title="Resolve Missing Evidence Fields",
        target_tab="advanced", target_section="contract", action_type="NAVIGATE"
    )
elif quality_blockers or quality_score < 70:
    return SmartNextAction(
        title="Improve AI Policy Quality",
        target_tab="advanced", target_section="editor", action_type="NAVIGATE"
    )
elif total_reviews < 30:
    return SmartNextAction(
        title="Review Pending Incidents in Workbench",
        target_tab="learning", action_type="NAVIGATE"
    )
elif not sim_passed:
    return SmartNextAction(
        title="Run Accuracy Validation & Simulation Replay",
        target_tab="advanced", target_section="simulation", action_type="SIMULATE"
    )
elif approval_eligible and not is_approved:
    return SmartNextAction(
        title="Request Production Approval",
        target_tab="overview", action_type="APPROVE"
    )
else:
    return SmartNextAction(
        title="Monitor Production Performance",
        target_tab="overview", action_type="NAVIGATE"
    )
```

---

## 5. Statistical Benchmarks & Formulas

The engine evaluates three mathematical thresholds for production eligibility:

1. **Observed False Positive Precision:**
   $$\text{Precision}_{\text{FP}} = \frac{\text{Agreed FP}}{\text{Agreed FP} + \text{AI False Alarm}} \ge 0.98$$

2. **Wilson 95% Score Lower Bound (Asymmetric Binomial Interval):**
   $$W_{\text{lower}} = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}} \ge 0.96$$
   *(where $z = 1.96$ for 95% confidence, $n = \text{total verified reviews}$, $\hat{p} = \text{observed precision}$)*

3. **True Positive Recall (Attack Detection Sensitivity):**
   $$\text{Recall}_{\text{TP}} = \frac{\text{Agreed TP}}{\text{Agreed TP} + \text{Critical Missed TP}} \ge 0.95$$

Any occurrence of **Critical Missed TP** ($\text{AI: FP}, \text{Analyst: TP}$) triggers immediate fail-closed suspension.
