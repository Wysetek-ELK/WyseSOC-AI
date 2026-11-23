# AIS 2.1b — 02: Root-Cause Investigation: Population Discrepancies

## 1. Executive Summary

During the AIS 2.1a operational audit, multiple apparent population count discrepancies were documented:
- Main warning stated: 45 verified reviews, 0 TP / 45 FP, 30 abstentions, 15 initial benchmarks without stored inference.
- Detailed accuracy breakdown stated: 13 ground-truth reviews, 0 TP / 45 FP, 13 abstentions, 0 missing inference.
- AI Evaluation Tracking enumerated 15 current incidents.

This investigation determined the exact root cause behind each discrepancy.

---

## 2. Root Cause Breakdown

### Issue A: Conflation of Current Incidents with Historical Review Cohorts
- **Root Cause:** The earlier accuracy reporting aggregated `total_analyst_reviews` from the lifetime `rule_learning_profiles` record (45 reviews), but attempted to pair it with the current live incident list (13 or 15 incidents) within a single narrative sentence: `13 Reviews (0 TP / 45 FP)`.
- **Mathematical Impossibility:** 45 false positives cannot belong to a population of 13 incidents.
- **Resolution:** Strict dual-scope separation:
  - `current_inventory`: Displays strictly the current operational incident population ($N = 15$) and their associated analyst reviews ($N = 15$ verified, 0 TP / 15 FP).
  - `historical_cohort`: Displays the cumulative lifetime learning cohort ($N = 47$ reviews, 0 TP / 47 FP).

### Issue B: Partition Invariant Gap for Asynchronous Tasks
- **Root Cause:** In `AisEvaluationService`, incidents with status `STATUS_QUEUED` or `STATUS_RUNNING` incremented `cnt_queued` and `cnt_running` but bypassed `cnt_not_evaluated`. As a result, when tasks were executing or queued, the five primary status counters did not sum to `total_incidents`:
  $$\text{Current Incidents} \neq \text{Decisive} + \text{Abstained} + \text{Rejected} + \text{Failed} + \text{Not Evaluated}$$
- **Resolution:** Re-architected status classification in `AisEvaluationService` so that all uncompleted evaluations are classified under `cnt_not_evaluated` while maintaining `cnt_queued` and `cnt_running` as precise sub-indicators. This guarantees that:
  $$\text{Total Incidents} = \text{Decisive} + \text{Abstained} + \text{Rejected} + \text{Failed} + \text{Not Evaluated}$$

### Issue C: Synthetic Test Fixture Provenance
- **Root Cause:** Patterned UUID test fixtures (`10000000-0000-0000-0000-000000000001`) from synthetic test suites had previously been written to shared tables, creating risk of polluting production ground truth with fake TP verdicts.
- **Resolution:** `RuleLearningService` and `AisEvaluationService` apply strict regex-based test fixture exclusion (`^10000000-`, `^20000000-`), ensuring synthetic records never enter empirical calibration.

### Issue D: Browser Acceptance Assertion Flaws in AIS 2.1a
- **Root Cause 1 (`hasTotalCards = false`):** In AIS 2.1a, Card 1 had the label `Current Incidents`. The acceptance script asserted `text.includes('Total Incidents')`, which failed despite valid metrics being displayed.
- **Root Cause 2 (`containsIncident335 = false`):** The Review Incidents tab loads incident records dynamically via async fetch. The test checked body text before the fetch resolved and before row selection opened the evidence drawer.
- **Resolution:** Card 1 now includes both `Current Incidents` and `Total Incidents` in its subtitle (`Current Operational Scope · Total Incidents`). The acceptance test waits for asynchronous data hydration and activates incident inspection.
