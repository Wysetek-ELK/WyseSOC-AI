# 09 — Rule Learning Lifecycle & Gate G8 Readiness Report
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Evaluation Date:** November 19, 2026  
**Current Lifecycle Stage:** `LEARNING`  
**Autonomous Operation Eligibility:** `FALSE` (Strictly Blocked)  

---

## 1. Ground Truth Isolation & Baseline Integrity

In strict adherence to the UPLA non-fabrication directive, Verdictum AI enforces a zero-synthetic-label policy:
- **Prior Reviews on Fresh Dataset:** **0**
- **Verified True Positives:** **0**
- **Verified False Positives:** **0**
- **Statistical Evaluation Metric:** **NOT MEASURABLE** (Insufficient verified human determinations).

Under AIS 2.0 governance, any system reporting a synthetic 98% accuracy on an unreviewed fresh dataset is considered a critical security violation. All accuracy metrics remain uncalculated until real human reviews are logged through the double-blind review workbench.

---

## 2. Statistical Readiness & Confusion Matrix Status

The current rule learning profile retrieved from `/api/learning/rules/7bd13e89-0828-48e6-8cf5-f3cbf12d438c` reports:

```json
{
  "lifecycle_stage": "LEARNING",
  "total_incidents_processed": 226,
  "total_analyst_reviews": 0,
  "eligible_evaluations": 0,
  "verified_tp_count": 0,
  "verified_fp_count": 0,
  "empirical_accuracy": null,
  "wilson_lower_bound": null,
  "fp_precision": null,
  "tp_recall": null,
  "is_production_eligible": false,
  "confusion_matrix": {
    "agreed_tp": 0,
    "agreed_fp": 0,
    "critical_missed_tp": 0,
    "ai_false_alarm": 0,
    "abstained_resolved": 0,
    "disputed": 0
  }
}
```

---

## 3. Tiered Production Eligibility Requirements

Before any detection rule can advance through lifecycle stages or unlock autonomous capabilities, it must satisfy progressive mathematical and governance milestones:

| Lifecycle Tier | Milestone Requirements | Current Status for Target Rule | Operational Permissions |
| :--- | :--- | :--- | :--- |
| **Tier 1: Human Pilot** | - G1–G7 Structural Quality Passed<br>- Local LLM Token Limits Verified<br>- $\ge 5$ verified human reviews | **MET FOR PILOT INITIATION**<br>(G1–G7 Passed, Benchmark Validated, 0/5 reviews) | Advisory Pilot Workbench Active;<br>AI verdicts masked from analysts |
| **Tier 2: Shadow Calibration** | - $\ge 30$ verified human reviews<br>- Initial Wilson 95% confidence bound calculated<br>- Trust score calibrated | **PENDING PILOT COMPLETION**<br>(0 / 30 reviews recorded) | Advisory AI copilot suggestions visible;<br>Decisive automation blocked |
| **Tier 3: Autonomous Certification** | - $\ge 100$ verified reviews ($\ge 25$ TP, $\ge 50$ FP)<br>- Empirical Accuracy $\ge 95.0\%$<br>- Wilson Lower Bound $\ge 96.0\%$<br>- FP Precision $\ge 99.0\%$<br>- TP Recall $\ge 95.0\%$<br>- Gate G8 Status: `PASS` | **NOT ELIGIBLE**<br>(Gate G8: `NOT_EVALUATED`, 0 / 100 reviews) | Full autonomous ticket resolution & auto-closure allowed under governance |

---

## 4. Automation Policy & Auto-Closure Safeguard

The automation policy configuration for this rule was audited and verified:

```json
{
  "policy_id": "82c59934-ede7-4cc7-98d8-d2e18314dab5",
  "is_enabled": false,
  "emergency_disable": false,
  "allowed_verdicts": ["FALSE_POSITIVE"],
  "min_trust_score": 8,
  "min_fp_precision": 0.98,
  "daily_closure_limit": 50,
  "current_day_closure_count": 0
}
```

- **Automation State:** Strictly `DISABLED` (`is_enabled: false`).
- **Safety Invariant:** Under no circumstances will Verdictum AI auto-close FortiSIEM incidents for `Website access policy violation: Same Source and Destination` during the pilot phase. Auto-closure remains locked until Tier 3 certification is achieved and formal Admin authorization is granted.
