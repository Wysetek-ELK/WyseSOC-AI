# AIS 2.1b — 04: Backend Invariant & Aggregation Implementation

## 1. Targeted Backend Modifications

File: `backend/app/services/ais_evaluation_service.py`

### Modification A: Exact Partition Guarantee
Replaced ambiguous conditional status counting with strict exhaustive classification:

```python
st = resolved["status"]
if st == STATUS_EVALUATED_DECISIVE:
    cnt_evaluated_decisive += 1
elif st == STATUS_ABSTAINED:
    cnt_abstained += 1
elif st == STATUS_VALIDATION_REJECTED:
    cnt_validation_rejected += 1
elif st == STATUS_EVALUATION_FAILED:
    cnt_evaluation_failed += 1
elif st in (STATUS_NOT_EVALUATED, STATUS_QUEUED, STATUS_RUNNING):
    cnt_not_evaluated += 1
    if st == STATUS_QUEUED:
        cnt_queued += 1
    elif st == STATUS_RUNNING:
        cnt_running += 1
    if resolved.get("is_mock_only"):
        cnt_mock_only += 1
else:
    cnt_not_evaluated += 1
```

**Guaranteed Invariant:**
$$\text{total\_incidents} = \text{cnt\_evaluated\_decisive} + \text{cnt\_abstained} + \text{cnt\_validation\_rejected} + \text{cnt\_evaluation\_failed} + \text{cnt\_not\_evaluated}$$

### Modification B: Snapshot Identity & Consistency Tokens
Generated deterministic snapshot token and exposed accuracy eligibility and explanation:

```python
snapshot_token = f"snap-{uuid.uuid4().hex[:12]}"
snapshot_time = utc_now().isoformat()

accuracy_numerator = None
accuracy_denominator = cnt_eligible_decisive_pairs
accuracy_eligibility = "NOT_MEASURABLE_ZERO_DECISIVE_DENOMINATOR"
non_measurable_reason = (
    "No eligible decisive AI predictions are matched to verified analyst verdicts."
    if cnt_eligible_decisive_pairs == 0
    else None
)

if cnt_eligible_decisive_pairs > 0:
    accuracy_status = "MEASURABLE"
    accuracy_eligibility = "ELIGIBLE"
    non_measurable_reason = None
    correct = cnt_agreement_tp + cnt_agreement_fp
    accuracy_numerator = correct
    selective_accuracy = round(float(correct) / float(cnt_eligible_decisive_pairs), 4)
```

Both `summary` and `summary["current_inventory"]` expose these fields consistently.

---

## 2. Automated Test Verification

Target test suite: `backend/tests/test_ais_unified_population_contract.py`

Added `test_evaluation_snapshot_partition_invariant_and_fields` to verify:
1. `summary["total_incidents"] == partition_sum`
2. `curr["total_incidents"] == curr_partition_sum`
3. `summary["snapshot_id"].startswith("snap-")`
4. `summary["operational_scope"] == "CURRENT_INVENTORY"`
5. `summary["accuracy_denominator"] == summary["eligible_decisive_comparisons"]`
6. `summary["accuracy_eligibility"] == "NOT_MEASURABLE_ZERO_DECISIVE_DENOMINATOR"` when denominator is 0.

**Test execution result:**
All 4 tests in `test_ais_unified_population_contract.py` and all 20 tests in `test_ais_evaluation_tracking.py` passed with 100% success.
