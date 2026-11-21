# 03 — Canonical Population and Scope Contract

**Verdictum AI — AIS 2.1a Unified Population Hotfix**  
**Specification:** Unified Backend & Frontend Data Contract  
**Timestamp:** 2026-11-21T11:15:50+05:30  
**Status:** APPROVED & ENFORCED  

---

## 1. Population Hierarchy and Definitions

To prevent ambiguity, data collisions, and contradictory UI displays, all backend and frontend services must strictly adhere to the following six canonical populations:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Population A: Operational Incident Inventory                           │
│ (Eligible distinct incidents for rule + tenant + time window)          │
│ Total: 13 incidents                                                    │
├────────────────────────────────────────────────────────────────────────┤
│ Population B: Analyst Review Records                                   │
│ (Authenticated analyst submissions, historical + current)              │
│ Total: 45 submissions                                                  │
├────────────────────────────────────────────────────────────────────────┤
│ Population C: Verified Ground Truth                                    │
│ (Authoritatively verified TP or FP determinations)                     │
│ Current Scope: 13 (0 TP / 13 FP)  |  Historical Scope: 45 (0 TP / 45 FP)│
├────────────────────────────────────────────────────────────────────────┤
│ Population D: Model Execution History                                  │
│ (Real Local LLM inference attempts under policy v7)                    │
│ Total: 26+ capture attempts                                            │
├────────────────────────────────────────────────────────────────────────┤
│ Population E: Matched Evaluation Cohort                                │
│ (Eligible incidents possessing BOTH verified human label and AI capture)│
│ Current Scope: 13 (all 13 abstained)                                   │
│ Historical Scope: 30 abstained, 15 un-inferred initial benchmarks      │
├────────────────────────────────────────────────────────────────────────┤
│ Population F: Decisive Evaluation Cohort                               │
│ (Subset of E with accepted decisive verdict: TRUE_POSITIVE / FP)       │
│ Total: 0 decisive comparisons (Both scopes)                            │
│ Mathematical Consequence: Accuracy is NOT MEASURABLE                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Invariant Rules and Contracts

### Invariant 1: Total Ground Truth Identity
For any evaluated scope $S$, the total verified ground truth must equal the sum of verified True Positives and verified False Positives:
$$\text{TotalVerified}_S = \text{VerifiedTP}_S + \text{VerifiedFP}_S$$
- For $S = \text{Current}$: $13 = 0 + 13$.
- For $S = \text{Historical}$: $45 = 0 + 45$.
- Violations (such as displaying $13 = 0 + 45$) are strictly blocked by typed schema contracts and UI state binding.

### Invariant 2: Scope Decoupling
The UI must never render counts from Population A (Current Inventory) alongside label breakdowns from Population C (Historical Ground Truth) in a single card or sentence without clear, explicit scope demarcation.

### Invariant 3: Zero-Denominator Safety
When the Decisive Evaluation Cohort (Population F) equals 0:
$$\text{DecisiveComparisons} = 0 \implies \text{Accuracy} = \text{NULL} \equiv \text{"NOT MEASURABLE"}$$
- The system must **never** report $0.00\%$ or $0\%$ accuracy.
- Explanations must distinguish between:
  1. **Zero Decisive Predictions:** AI abstained (`REQUIRES_ATTENTION`) on all cases.
  2. **One-Class Dataset:** Only verified `FALSE_POSITIVE` labels exist; True Positive recall cannot be mathematically measured without authentic True Positive cases.

### Invariant 4: Synthetic Test Fixture Exclusion
Any record whose incident ID matches the patterned test UUID regex:
$$\verb|^[0-9]0000000-0000-0000-0000-[0-9a-f]{12}$|$$
is automatically excluded from production metrics and learning profiles.

---

## 3. JSON Data Contract Schema (`AisEvaluationSummary`)

```typescript
export interface PopulationScopeBreakdown {
  population_name: string;
  total_incidents?: number;
  total_reviews?: number;
  verified_reviews?: number;
  verified_tp: number;
  verified_fp: number;
  abstained: number;
  initial_benchmarks_missing_inference?: number;
  missing_evaluations_among_reviewed?: number;
  decisive: number;
}

export interface AisEvaluationSummary {
  rule_id: string;
  policy_version_number?: number;
  policy_version_id?: string;
  total_incidents: number;
  not_evaluated: number;
  evaluated_decisive: number;
  abstained: number;
  validation_rejected: number;
  evaluation_failed: number;
  verified_reviews: number;
  matched_verified_reviews: number;
  verified_tp_count: number;
  verified_fp_count: number;
  eligible_decisive_comparisons: number;
  selective_accuracy?: number | null;
  accuracy_status: "MEASURABLE" | "NOT_MEASURABLE";
  accuracy_explanation: string;
  one_class_dataset?: boolean;
  
  // Dual Population Scopes
  current_inventory: PopulationScopeBreakdown;
  historical_cohort: PopulationScopeBreakdown;
}
```
