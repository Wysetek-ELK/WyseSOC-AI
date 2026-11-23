# AIS 2.2 Report 02: AIS 2.1b.1 Discrepancy Reconciliation

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** RECONCILED & DEFECT RESOLVED  

---

## 1. Context of the Discrepancy

In AIS 2.1b.1, the backend evaluation tracking reports documented the following authoritative numbers for target rule **Heavy TCP Host Scan On Fixed Port** (`40498741-ee6b-4a71-9101-0d6d3f77154c`):
- 35 operational incidents in inventory.
- 33 abstentions (`REQUIRES_ATTENTION`).
- 2 not evaluated (`NOT_EVALUATED`).
- 0 decisive verdicts (`TRUE_POSITIVE` or `FALSE_POSITIVE`).
- 65 cumulative historical analyst reviews (all verified False Positives).
- Selective accuracy: `NOT_MEASURABLE` (null).

However, examination of the live Chrome browser acceptance captures (`03_test_ai_dominant_table_1440x900.png` and `04_accuracy_learning_tab_1440x900.png`) and `gui_acceptance_results.json` revealed:
- Tab 2 (Test AI): 0 Current Incidents, 0 Decisive Verdicts, 0 Abstained, 0 Not Evaluated, and table message: `"No incidents match the selected filter"`.
- Tab 3 (Accuracy & Learning): Amber banner displaying `"ZERO GROUND TRUTH LABELS"`, with no visible population scope buttons.
- `gui_acceptance_results.json`: `hasDualScopes: false`, `hasOneClassDataset: false`, `scopeButtons: []`.

The AIS 2.2 audit was instructed to definitively reconcile this contradiction and identify whether this was genuine data loss, an empty scope, a stale React cache, or a software defect.

---

## 2. Root Cause Investigation

### 2.1 Backend PostgreSQL Transaction Abort (25P02)

In commit `7a3c98b` (AIS 2.1b.1), to ensure strict repeatable read isolation across multi-table aggregation queries, the following code was added to `AisEvaluationService.get_rule_evaluation_tracking_overview()`:

```python
# backend/app/services/ais_evaluation_service.py (Commit 7a3c98b)
try:
    bind = db.get_bind()
    if getattr(bind.dialect, "name", "") == "postgresql":
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"))
except Exception as iso_err:
    logger.debug("Transaction isolation set skipped or not supported: %s", iso_err)
```

**The Mechanical Failure:**
1. In FastAPI, the route `/api/ais/rules/{rule_uuid}/evaluation-status` requires user authentication via `current_user = Depends(get_current_active_user)`.
2. The user authentication dependency runs a `SELECT` statement on the `users` table using the active SQLAlchemy `AsyncSession`.
3. In PostgreSQL, executing any SQL statement implicitly opens a transaction block.
4. According to PostgreSQL specification, `SET TRANSACTION ISOLATION LEVEL` can **only** be executed at the very beginning of a transaction, before any query has executed. Issuing it mid-transaction causes PostgreSQL to throw:
   ```
   ERROR: 25001: SET TRANSACTION ISOLATION LEVEL must be called before any query
   ```
5. While the Python `try/except` block caught the exception, PostgreSQL marks the transaction as permanently aborted (`TBLOCK_ABORT`):
   ```
   ERROR: 25P02: current transaction is aborted, commands ignored until end of transaction block
   ```
6. Every subsequent query inside `get_rule_evaluation_tracking_overview()` (fetching rules, prompt versions, incident counts, and reviews) immediately failed with `25P02`.
7. As a result, the FastAPI route failed with HTTP 500 Internal Server Error.

### 2.2 Frontend Error Suppression & Scope Selector Masking

1. In `AiTestWorkbench.tsx`, the function `fetchRuleSummary()` called `api.getRuleEvaluationStatus()`. The catch block logged the error to console but did not surface an error banner, leaving `evalSummary = null`.
2. With `evalSummary = null`, `evalSummary?.total_incidents ?? 0` evaluated to `0`, rendering 0 across all KPI cards and leaving the incident table empty.
3. In `AccuracyLearningSummary.tsx`, `currentTotal` evaluated to `0`. When `totalVerified === 0`, the component evaluated `!hasVerifiedLabels = true` and rendered the amber banner `"ZERO GROUND TRUTH LABELS"`.
4. Crucially, the **Population Scope Selector** (switching between Current Inventory and Cumulative Historical Cohort) was previously rendered **only inside** the `hasVerifiedLabels` branch. Because `hasVerifiedLabels` was false, the scope switcher was completely hidden from the DOM.
5. Consequently, the automated Playwright acceptance script recorded `hasDualScopes: false` and `scopeButtons: []`.

---

## 3. Remediation Implemented

### 3.1 Backend: Transaction Rollback Before Snapshot Isolation

In `backend/app/services/ais_evaluation_service.py`, lines 460-475 were updated to properly handle active PostgreSQL read transactions and guarantee safe fallback:

```python
# Guarantee transaction-level snapshot isolation under PostgreSQL
try:
    bind = db.get_bind()
    if getattr(bind.dialect, "name", "") == "postgresql":
        # If an implicit clean read transaction was started by auth dependencies,
        # rollback first so SET TRANSACTION ISOLATION LEVEL succeeds cleanly.
        if db.in_transaction():
            await db.rollback()
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"))
except Exception as iso_err:
    logger.debug("Transaction isolation set skipped or not supported: %s", iso_err)
    # If isolation setup failed, rollback so PostgreSQL clears TBLOCK_ABORT
    try:
        await db.rollback()
    except Exception:
        pass
```

### 3.2 Frontend: Persistent Scope Switcher & Error Feedback

1. **Persistent Scope Selector:** In `frontend/src/components/compact/AccuracyLearningSummary.tsx`, the Population Scope Selector was moved to the very top of the component, guaranteeing it renders unconditionally whether `currentTotal` is 0 or not.
2. **Contextual Scope Hint:** In the zero-label banner, if the current inventory is 0 while the historical cohort has labels, an explicit hint is displayed:
   `"Note: Cumulative Historical Cohort contains 65 verified labels (65 FP, 0 TP). Click the scope switcher above to view historical baseline metrics."`
3. **Visible API Error Feedback:** In `AiTestWorkbench.tsx`, `fetchRuleSummary()` now sets an informative warning banner in the UI if the evaluation status API fails or times out, preventing misleading zero counts.

---

## 4. Verification & Regression Coverage

A new regression test was added in `backend/tests/test_ais_unified_population_contract.py`:
- `test_transaction_isolation_safety_and_aborted_transaction_recovery`: Explicitly initiates a prior query on the session, calls `get_rule_evaluation_tracking_overview()`, and verifies that no `25P02` abort occurs and dual-scope summaries are returned cleanly.

**Test Results:**
- Backend regression suite: 33/33 tests PASSED (19.43s).
- Frontend regression suite: 16/16 test suites, 88/88 tests PASSED (1.9s).
