# AIS 2.1b.1 — Root Cause Analysis Report

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Developer**: Wysetek Systems Technologists Pvt. Ltd.  
**Release**: AIS 2.1b.1 (Targeted Corrective Release)  
**Target Rule**: Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Active Policy**: v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a` / `pv-eval-contract-v7`) — APPROVED  
**Draft Policy**: v8 (`20d4f788-85a5-437d-afbe-fe7fd80abca1`) — DRAFT  
**Date**: November 23, 2026  

---

## Executive Summary

Following the deployment and evaluation of AIS 2.1b, a rigorous audit of GUI acceptance evidence and automated screenshots revealed five specific anomalies (Issues A through E). This report details the root cause investigation for each issue, verifying whether each represented a software defect, a display synchronization error, an invalid test assertion, or genuine real-time system evolution.

---

## Issue A: Accuracy Scope Mismatch

### Problem Statement
In the AIS 2.1b acceptance screenshots, the **Accuracy & Learning** tab displayed older, contradictory scope counts:
- *Historical Cohort (45)*
- *Current Inventory (13)*
- Total reviews: *13*

Concurrently, other UI elements (e.g., Tab 1 incident summaries and backend API payloads) reported newer counts:
- *47* historical reviews (later growing to 65)
- *15* current reviews (later growing to 33)

### Investigation & Root Cause
Inspection of `frontend/src/components/compact/AccuracyLearningSummary.tsx` revealed:
1. **Hardcoded Fallbacks and String Literals**:
   ```tsx
   // Defect in AIS 2.1b:
   const currentTotal = summary?.current_inventory?.total_incidents ?? 13;
   const histTotal = summary?.historical_cohort?.total_reviews ?? 45;
   ...
   <span className="font-semibold text-slate-800">Current Incident Inventory (13)</span>
   ...
   <span className="font-semibold text-slate-800">Cumulative Historical Cohort (45)</span>
   ```
2. **Impact**: Even when the backend correctly returned dynamic counts, the static JSX labels remained fixed at `(13)` and `(45)`. Furthermore, when partial data or empty fields loaded during initial query transitions, the hardcoded fallback values of `13` and `45` surfaced in the UI instead of dynamic counts (`${currentTotal}` and `${histTotal}`).
3. **Resolution**: Replaced all hardcoded string templates and static fallbacks with dynamic bindings connected directly to the authoritative evaluation contract.

---

## Issue B: Test AI Population Mismatch

### Problem Statement
An acceptance screenshot of **Tab 2: Test AI** showed:
- Total Incidents: **30**
- Abstained: **27**
- Not Evaluated: **3**

Earlier baseline documentation recorded **15** total incidents.

### Investigation & Root Cause
1. **Live Ingestion Verification**: Investigation of the PostgreSQL database on Server 1 (`172.26.41.240`) confirmed that this was **not a software defect or aggregation error**, but rather **genuine ongoing incident ingestion** by the SOC pipeline over time.
2. **Partition Invariant Verification**: The partition invariant:
   $$\text{Current Total} = \text{Decisive} + \text{Abstained} + \text{Rejected} + \text{Failed} + \text{Not Evaluated}$$
   was rigorously upheld:
   $$30 = 0 + 27 + 0 + 0 + 3$$
   At the time of AIS 2.1b.1 testing, additional live incidents had ingested, bringing the totals to:
   $$35 = 0 + 33 + 0 + 0 + 2$$
3. **Conclusion**: The population difference between 15, 30, and 35 reflects legitimate time-series growth of operational telemetry. The critical invariant is that all UI components viewing the same snapshot must reflect the identical total.

---

## Issue C: Snapshot Consistency & Transaction Isolation

### Problem Statement
In AIS 2.1b, snapshot identifiers were generated using `snap-{uuid.uuid4().hex[:12]}`. A random UUID identifies an HTTP response, but does not guarantee that separate database queries within the same request read from a point-in-time consistent database snapshot.

### Investigation & Root Cause
1. **Multi-Query Read Skew**: `AisEvaluationService` executes multiple database queries:
   - Incident counts grouped by evaluation status
   - Analyst review counts grouped by verdict (TP/FP)
   - Prompt version metadata and rule profile
2. Under PostgreSQL default `READ COMMITTED` isolation, if a new incident or review is written between Query 1 and Query 2, Query 2 reads data committed after Query 1 began. This produces read skew, where incident counts do not reconcile with review counts.
3. **Resolution**:
   - Implemented `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;` at the beginning of `get_unified_population_contract()`.
   - Replaced random UUID generation with a **deterministic SHA-256 fingerprint** that binds rule UUID, policy version ID, tenant ID, outcome counts, latest incident ID, latest review ID, and evaluation timestamps.

---

## Issue D: Policy GUI Assertion Failure (`hasV7Approved = false`)

### Problem Statement
In `docs/AIS_2_1b/gui_acceptance_results.json`, the browser test recorded:
```json
"ruleHeader": {
  "hasV7Approved": false
}
```

### Investigation & Root Cause
1. **UI Component Omission**: When entering the Agent Intelligence Studio page (`/agent-intelligence-studio`), the page defaults to **Tab 1: Review Incidents**.
2. In AIS 2.1b, the `CompactPageHeader` displayed the rule title, severity badge, and action buttons, but omitted the active and draft policy version pills (`v7 APPROVED` and `v8 DRAFT`). The policy pills were only rendered inside the inner action ribbon of Tab 2.
3. Because the acceptance script evaluated `ruleHeader` at the top of Tab 1 before switching tabs, the query for `v7 APPROVED` returned `false`.
4. **Resolution**: Updated `CompactDesignSystem.tsx` and `page.tsx` so that `CompactPageHeader` directly accepts `activePolicy` and `draftPolicy` props and renders `data-testid="header-active-policy-status"` (`v7 APPROVED`) and `data-testid="header-draft-policy-status"` (`v8 DRAFT`) prominently in the compact header toolbar on all tabs.

---

## Issue E: GUI Geometry Contradiction (338px vs 522px)

### Problem Statement
AIS 2.1b documentation claimed the incident evaluation table started at approximately **338px**, whereas browser CDP measurements recorded **522px**.

### Investigation & Root Cause
1. **Theoretical vs Live Layout Measurement**: The 338px figure in early design notes was a theoretical wireframe calculation that accounted only for the global navigation bar and a minimal tab header, omitting:
   - Global application header (52px)
   - Breadcrumb & rule context ribbon
   - Compact incident action notice
   - Model context & GPU inference status strip
   - KPI metric card grid
2. **Actual Live Geometry**: Live CDP measurement in headless Chrome at 1440×900 records:
   - Header Toolbar top: `52px`
   - Tab Navigation top: `223px`
   - Dominant Incident Table top: `550px`
3. **Usability Invariant Verification**: At `550px`, the incident table is **completely visible above the 900px fold** without initial scrolling (`tableVisibleWithoutScroll: true`). The documentation has been corrected to reflect actual live DOM coordinates.
