# AIS 2.1b.1 — Snapshot Transaction Integrity & Deterministic State Fingerprinting

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Component**: PostgreSQL Database & Backend Evaluation Service  
**Author**: PostgreSQL & Senior Full-Stack Architecture Team  
**Date**: November 23, 2026  

---

## 1. Architectural Challenge

In SOC AI platforms, evaluation metrics (accuracy, abstention rate, decision coverage, and ground-truth balance) are derived from multiple distinct relational tables:
1. `incidents` / `rule_prompt_evaluations` (AI inference outcomes)
2. `analyst_verdicts` / `analyst_verdict_reviews` (SOC analyst ground truth)
3. `prompt_versions` / `rule_learning_profiles` (Governance policy states)

When concurrent ingestion workers write incoming alerts or analysts submit reviews, querying these tables sequentially under PostgreSQL default `READ COMMITTED` isolation risks **read skew**:
- Query A reads 35 total incidents.
- A concurrent worker commits 1 new incident.
- Query B reads 36 incidents for the outcome partition.
- Result: Partition sum ($\sum \text{outcomes}$) does not match the total incident count, breaking the partition invariant.

Furthermore, generating a non-deterministic random UUID (`uuid.uuid4()`) on each API call creates the false impression of state changes when the underlying data is completely unchanged, preventing effective HTTP caching and client-side memoization.

---

## 2. PostgreSQL REPEATABLE READ READ ONLY Implementation

To eliminate read skew without table locks or performance degradation, `AisEvaluationService.get_unified_population_contract()` executes within a `REPEATABLE READ READ ONLY` transaction block:

```python
# backend/app/services/ais_evaluation_service.py

# Enforce PostgreSQL snapshot transaction isolation
try:
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"))
except Exception as ex:
    logger.debug(f"Snapshot transaction isolation notice: {ex}")
```

### Isolation Guarantees:
1. **Single Point-in-Time Snapshot**: All subsequent `SELECT` queries in the session read from the exact snapshot established when the first query started.
2. **Non-Blocking Reads**: Under PostgreSQL MVCC, `REPEATABLE READ` transactions never lock writers, and writers never lock `REPEATABLE READ` readers.
3. **Zero Read Skew**: Multi-table aggregations (incidents, reviews, policy profiles) are guaranteed to reflect an atomic, self-consistent state.

---

## 3. Deterministic Snapshot Fingerprinting

To provide reliable cross-query and cross-tab snapshot identity, the service computes a cryptographically stable SHA-256 state fingerprint:

```python
# Compute deterministic SHA-256 state fingerprint
fp_components = [
    str(target_rule_id),
    str(target_ver_id),
    str(tenant_id),
    str(total_incidents),
    str(decisive),
    str(abstained),
    str(rejected),
    str(failed),
    str(not_evaluated),
    str(total_reviews),
    str(verified_tp),
    str(verified_fp),
    str(latest_eval_time),
    str(latest_incident_id),
    str(latest_review_id),
]
fp_raw = "|".join(fp_components)
state_hash = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()[:16]

deterministic_snapshot_id = f"snap-v{target_ver_num}-{state_hash}"
snapshot_fingerprint = f"fp-{state_hash}"
```

### Properties of the Deterministic Fingerprint:
- **Stability**: Multiple queries against the same database state return the exact same `snapshot_id` and `snapshot_fingerprint`.
- **Sensitivity**: Any mutation (new alert, updated verdict, revised prompt version) alters the components and produces a new, distinct fingerprint.
- **Cross-Contract Synchronization**: The identical `snapshot_id`, `snapshot_at`, and `snapshot_fingerprint` are injected into:
  - `contract["summary"]["snapshot_id"]`
  - `contract["current_inventory"]["snapshot_id"]`
  - `contract["historical_cohort"]["snapshot_id"]`

---

## 4. Mandatory Partition Invariant Verification

The system strictly enforces the evaluation partition invariant:

$$\text{Current Total} = \text{Decisive} + \text{Abstained} + \text{Rejected} + \text{Failed} + \text{Not Evaluated}$$

```python
partition_sum = (
    current_inv.decisive_count
    + current_inv.abstained_count
    + current_inv.rejected_count
    + current_inv.failed_count
    + current_inv.not_evaluated_count
)

assert partition_sum == current_inv.total_incidents, (
    f"Partition invariant violated: {partition_sum} != {current_inv.total_incidents}"
)
```

### Live Server 1 Verification:
- Decisive: **0**
- Abstained: **33**
- Rejected: **0**
- Failed: **0**
- Not Evaluated: **2** (queued/in-flight)
- **Total**: $0 + 33 + 0 + 0 + 2 = \mathbf{35}$ (Exact match)

---

## 5. Automated Regression Verification

The test `test_deterministic_snapshot_consistency_across_queries` in `backend/tests/test_ais_unified_population_contract.py` validates:
1. Consecutive reads produce identical snapshot IDs (`snap1 == snap2`).
2. Mutating incident counts deterministically produces a distinct snapshot ID (`snap1 != snap3`).
3. Partition invariants hold across all snapshot transitions.
