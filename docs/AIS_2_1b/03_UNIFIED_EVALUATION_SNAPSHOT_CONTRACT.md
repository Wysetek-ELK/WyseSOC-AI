# AIS 2.1b — 03: Unified Evaluation Snapshot Contract

## 1. Objective

Establish an authoritative, backend-defined evaluation snapshot contract for all Agent Intelligence Studio tabs, KPI summary cards, filter pills, and accuracy calculations.

---

## 2. Canonical JSON Schema Contract

```json
{
  "summary": {
    "snapshot_id": "snap-a1b2c3d4e5f6",
    "snapshot_at": "2026-11-22T06:30:00.000000Z",
    "rule_uuid": "40498741-ee6b-4a71-9101-0d6d3f77154c",
    "policy_version_number": 7,
    "policy_version_id": "pv-eval-contract-v7",
    "policy_status": "APPROVED",
    "is_active_policy_bound": true,
    "active_binding_status": "ACTIVE",
    "active_version_id": "pv-eval-contract-v7",
    "customer": "DEFAULT",
    "population_scope": "CURRENT_INVENTORY",
    "operational_scope": "CURRENT_INVENTORY",
    "total_incidents": 15,
    "not_evaluated": 0,
    "evaluated_decisive": 0,
    "abstained": 15,
    "validation_rejected": 0,
    "evaluation_failed": 0,
    "queued": 0,
    "running": 0,
    "mock_only_count": 0,
    "total_analyst_reviews": 15,
    "matched_verified_reviews": 15,
    "verified_tp_count": 0,
    "verified_fp_count": 15,
    "eligible_decisive_comparisons": 0,
    "accuracy_numerator": null,
    "accuracy_denominator": 0,
    "accuracy_eligibility": "NOT_MEASURABLE_ZERO_DECISIVE_DENOMINATOR",
    "non_measurable_reason": "No eligible decisive AI predictions are matched to verified analyst verdicts.",
    "missing_evaluations_among_reviewed": 0,
    "decision_coverage_percent": 0.0,
    "abstention_rate_percent": 100.0,
    "accuracy_status": "NOT_MEASURABLE",
    "accuracy_explanation": "Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts.",
    "is_one_class_dataset": true,
    "one_class_notice": "One-Class Dataset — Verified FP performance can be evaluated, but TP recall and two-class certification require genuine TP cases.",
    "selective_accuracy": null,
    "fp_precision": null,
    "tp_recall": null,
    "specificity": null,
    "wilson_lower_bound": null,
    "agreement_tp": 0,
    "agreement_fp": 0,
    "ai_false_alarm": 0,
    "critical_missed_tp": 0,
    "class_balance_status": "PILOT_CLASS_BALANCE_DEFICIT",
    "class_balance_notice": "Pilot class-balance deficit: requires >= 10 TP and >= 10 FP for Tier 2 Supervised Pilot qualification.",
    "historical_total_reviews": 47,
    "historical_verified_tp": 0,
    "historical_verified_fp": 47,
    "historical_abstained": 30,
    "historical_missing_inference": 15,
    "historical_total_processed": 56,
    "current_inventory": {
      "population_name": "Current Incident Inventory",
      "snapshot_id": "snap-a1b2c3d4e5f6",
      "snapshot_at": "2026-11-22T06:30:00.000000Z",
      "operational_scope": "CURRENT_INVENTORY",
      "total_incidents": 15,
      "verified_reviews": 15,
      "verified_tp": 0,
      "verified_fp": 15,
      "abstained": 15,
      "evaluated_decisive": 0,
      "validation_rejected": 0,
      "missing_evaluations_among_reviewed": 0,
      "not_evaluated": 0,
      "failed": 0,
      "queued": 0,
      "running": 0,
      "accuracy_numerator": null,
      "accuracy_denominator": 0,
      "accuracy_eligibility": "NOT_MEASURABLE_ZERO_DECISIVE_DENOMINATOR",
      "non_measurable_reason": "No eligible decisive AI predictions are matched to verified analyst verdicts.",
      "decision_coverage_percent": 0.0,
      "selective_accuracy": null,
      "accuracy_status": "NOT_MEASURABLE"
    },
    "historical_cohort": {
      "population_name": "Cumulative Historical Ground Truth",
      "total_reviews": 47,
      "verified_tp": 0,
      "verified_fp": 47,
      "abstained": 30,
      "initial_benchmarks_missing_inference": 15,
      "decisive": 0,
      "selective_accuracy": null,
      "accuracy_status": "NOT_MEASURABLE",
      "total_processed": 56
    }
  }
}
```

---

## 3. Invariants Enforced by Contract

1. **Partition Invariant:**
   $$\text{total\_incidents} = \text{evaluated\_decisive} + \text{abstained} + \text{validation\_rejected} + \text{evaluation\_failed} + \text{not\_evaluated}$$
2. **Review Invariant (Current):**
   $$\text{verified\_reviews} = \text{verified\_tp} + \text{verified\_fp}$$
3. **Review Invariant (Historical):**
   $$\text{historical\_total\_reviews} = \text{historical\_verified\_tp} + \text{historical\_verified\_fp}$$
4. **Consistency Invariant:**
   $$\text{current.verified\_reviews} \le \text{historical.total\_reviews}$$
5. **Zero-Denominator Safety:**
   $$\text{eligible\_decisive\_comparisons} = 0 \implies \text{selective\_accuracy} = \text{null} \land \text{accuracy\_status} = \text{"NOT\_MEASURABLE"}$$
