# 04 — Backend Aggregation and Query Fix

**Verdictum AI — AIS 2.1a Unified Population Hotfix**  
**Component:** Backend Aggregation Services  
**Modified Files:**
- `backend/app/services/ais_evaluation_service.py`
- `backend/app/services/rule_learning_service.py`
**Timestamp:** 2026-11-21T11:16:10+05:30  
**Status:** IMPLEMENTED & TESTED  

---

## 1. Targeted Backend Changes

### Change 1: Dual-Scope Population Aggregation in `AisEvaluationService`
In `backend/app/services/ais_evaluation_service.py`:
- Added counters `cnt_current_verified_tp` and `cnt_current_verified_fp` computed exclusively from the current operational incident cohort (`inc_rows`).
- Queried `RuleLearningService.get_or_create_profile` to retrieve cumulative historical cohort metrics (`profile.total_analyst_reviews`, `profile.verified_fp_count`, `profile.verified_tp_count`, `analyst_resolved_abstention`, `analyst_only_initial_benchmark`).
- Constructed structured payloads for both scopes:
  - `summary["current_inventory"]`:
    - `population_name`: `"Current Incident Inventory"`
    - `total_incidents`: 13
    - `verified_reviews`: 13
    - `verified_tp`: 0
    - `verified_fp`: 13
    - `abstained`: 13
    - `decisive`: 0
  - `summary["historical_cohort"]`:
    - `population_name`: `"Cumulative Historical Ground Truth"`
    - `total_reviews`: 45
    - `verified_tp`: 0
    - `verified_fp`: 45
    - `abstained`: 30
    - `initial_benchmarks_missing_inference`: 15
    - `decisive`: 0

### Change 2: Current Inventory Audit in `RuleLearningService`
In `backend/app/services/rule_learning_service.py` (`evaluate_rule_accuracy`):
- Added an operational incident query to retrieve distinct incidents for the rule.
- Calculated current inventory ground-truth distribution (`curr_matched_revs`, `curr_tp`, `curr_fp`, `curr_abstained`).
- Stored both `current_inventory` and `historical_cohort` inside `profile.error_distribution` and returned them in the API response dictionary.

### Change 3: Synthetic Fixture Exclusion Guard
In both services, implemented a strict regex filter:
```python
import re

def is_patterned_test_uuid(val: Optional[str]) -> bool:
    if not val:
        return False
    return bool(re.match(r"^[0-9]0000000-0000-0000-0000-[0-9a-f]{12}$", str(val).strip().lower()))

reviews = [
    r for r in all_candidate_reviews
    if not is_patterned_test_uuid(r.incident_id) and not is_patterned_test_uuid(r.id)
]
```
This guarantees that test fixture IDs like `10000000-0000-0000-0000-000000000001` can never contaminate operational learning profiles or certification metrics.

---

## 2. API Response Validation

An authenticated call to `/api/ais/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/evaluation-status?policy_version_number=7` returns:

```json
{
  "rule_id": "40498741-ee6b-4a71-9101-0d6d3f77154c",
  "policy_version_number": 7,
  "summary": {
    "total_incidents": 13,
    "evaluated_decisive": 0,
    "abstained": 13,
    "not_evaluated": 0,
    "verified_reviews": 13,
    "matched_verified_reviews": 13,
    "verified_tp_count": 0,
    "verified_fp_count": 13,
    "eligible_decisive_comparisons": 0,
    "selective_accuracy": null,
    "accuracy_status": "NOT_MEASURABLE",
    "accuracy_explanation": "Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts. All 13 current operational incidents evaluated under policy v7 received abstentions (REQUIRES_ATTENTION) or missing evaluations.",
    "current_inventory": {
      "population_name": "Current Incident Inventory",
      "total_incidents": 13,
      "verified_reviews": 13,
      "verified_tp": 0,
      "verified_fp": 13,
      "abstained": 13,
      "decisive": 0
    },
    "historical_cohort": {
      "population_name": "Cumulative Historical Ground Truth",
      "total_reviews": 45,
      "verified_tp": 0,
      "verified_fp": 45,
      "abstained": 30,
      "initial_benchmarks_missing_inference": 15,
      "decisive": 0
    }
  }
}
```

Both scopes are completely self-consistent and mathematically sound.
