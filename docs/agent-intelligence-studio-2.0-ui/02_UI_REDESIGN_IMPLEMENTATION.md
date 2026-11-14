# 02 - UI Redesign Implementation

## 1. Overview & Visual Design Language

The Agent Intelligence Studio 2.0 UI simplifies a previously complex, multi-tab operational tool into an intuitive, Level-1 friendly interface adhering to Verdictum AI's dark slate design system (`slate-950`, `cyan-400`, `emerald-400`, `amber-400`, `rose-400`).

The redesign follows four core UX principles:
1. **Status Hierarchy (STATUS -> REASON -> NEXT ACTION):** Every check clearly states its current state, why it is in that state, and the exact next step to advance.
2. **L1 Plain-English Terminology:** Statistical formulas and raw JSON trees are replaced by guided natural-language descriptions.
3. **Progressive Disclosure:** Deep technical details (G1–G8 individual gate results, evidence schema fields, raw telemetry) are preserved but collapsed by default, expandable with one click.
4. **Actionable Contextual Buttons:** Every stage and issue card provides a direct action button that opens the relevant workflow without manual navigation.

---

## 2. Three-Tab Architecture

```
+---------------------------------------------------------------------------------------------------------+
|                                  AGENT INTELLIGENCE STUDIO 2.0                                          |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  [ TAB 1: OVERVIEW (Default, L1) ]   [ TAB 2: ANALYST LEARNING ]   [ TAB 3: ADVANCED CONFIGURATION ]    |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  TAB 1: OVERVIEW                                                                                        |
|  ====================================================================================================   |
|  A. Rule Identity & Quick Action Strip                                                                  |
|     - Rule Name, Rule ID, Severity Badge, Archetype Pill, Baseline Status, Plain-English Description   |
|                                                                                                         |
|  B. Production Readiness Summary Card                                                                    |
|     - Readiness Status (BLOCKED, LEARNING, VALIDATING, READY FOR APPROVAL, APPROVED, ACTIVE)            |
|     - Quality Gates: X/8 Passed                                                                         |
|     - Rule Quality: XX/100                                                                              |
|     - Verified Analyst Reviews: X/30                                                                    |
|     - Empirical Accuracy: XX.X% or N/A                                                                  |
|     - Readiness Progress Bar (0-100%)                                                                   |
|                                                                                                         |
|  C. Smart Next Action Banner                                                                            |
|     - Single prioritized recommended action determined by backend blocking dependencies                |
|     - Primary CTA button (e.g., "Verify Semantics", "Review Pending Incidents", "Run Simulation")       |
|                                                                                                         |
|  D. 6 Guided Checklist Stages                                                                           |
|     1. Define Detection   [ Completed / Needs Action / Blocked / Pending ]                              |
|     2. Verify Evidence    [ Completed / Needs Action / Blocked / Pending ]                              |
|     3. Validate AI Policy [ Completed / Needs Action / Blocked / Pending ]                              |
|     4. Analyst Learning   [ Completed / Needs Action / Blocked / Pending ]                              |
|     5. Test AI Accuracy   [ Completed / Needs Action / Blocked / Pending ]                              |
|     6. Production Approval[ Completed / Needs Action / Blocked / Pending ]                              |
|                                                                                                         |
|     Each stage includes:                                                                                |
|     - What this check means                                                                             |
|     - Why it matters                                                                                    |
|     - What is required to complete it                                                                   |
|     - Contextual Action Button                                                                          |
|     - Collapsible Technical Details (G1-G8 Breakdown, Evidence Schema)                                  |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Tab 1: Overview Breakdown

Implemented in `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:

### Section A: Rule Identity
- Displays rule title, event type, canonical rule ID, and data source.
- Shows severity indicator (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- Displays primary detection archetype (e.g. `NETWORK_SCAN`, `BRUTE_FORCE`).
- Plain-English description synthesizing detection logic and trigger thresholds.
- SIEM Baseline Status (`ACTIVE`, `INACTIVE`) displayed separately from readiness.

### Section B: Production Readiness Summary
- Authoritative readiness state rendered with large readable badges:
  - `BLOCKED / INCOMPLETE` (Rose / Slate)
  - `LEARNING` (Amber)
  - `VALIDATING` (Blue)
  - `READY FOR APPROVAL` (Cyan with pulse animation)
  - `APPROVED` (Teal)
  - `ACTIVE` (Emerald)
- Four core metrics:
  - Quality Gates Passed: `X/8 Passed`
  - Rule Quality Score: `XX/100`
  - Verified Reviews: `X/30`
  - Empirical Replay Accuracy: `XX.X%` or `N/A` (never fabricated when unverified)
- Progress bar displaying completed percentage across the 6 stages.

### Section C: Smart Next Action Card
- Automatically highlights the single blocking task required to progress:
  - *Verify FortiSIEM Detection Semantics*
  - *Resolve Missing Evidence Fields*
  - *Improve AI Policy Quality*
  - *Review Pending Incidents*
  - *Run Accuracy Validation*
  - *Run Simulation Replay*
  - *Request Production Approval*
- Clicking the button directly transitions to the required tab or sub-workflow.

### Section D: 6 Guided Checklist Stages
Each stage maps directly to verified backend checks:
1. **Define Detection:** Validates correlation conditions, thresholds, and aggregation window (Gate G1).
2. **Verify Evidence:** Verifies telemetry mapping against the archetype contract (Gates G2 & G3).
3. **Validate AI Policy:** Evaluates policy completeness, indicators, and abstention safety (Gates G4–G7).
4. **Analyst Learning:** Tracks double-blind verified determinations (minimum 30 pilot / 100 prod).
5. **Test AI Accuracy:** Evaluates empirical replay precision (≥98%), recall (≥95%), and Wilson lower bound (≥96%) (Gate G8).
6. **Production Approval:** Final governance gate with cryptographic integrity and human approval.

---

## 4. Tab 2: Analyst Review & Learning Implementation

Implemented in `frontend/src/components/learning/RuleLearningDashboard.tsx`:
- **Metrics Grid:** Total Verified Reviews, Required Pilot Target (30), Required Prod Target (100), Observed FP Precision, Wilson 95% Lower Bound, TP Recall.
- **2x2 Ground-Truth Confusion Matrix:**
  - `Agreed FP` (Benign - Auto-close candidate)
  - `Critical Missed TP` (Missed Attack - Immediate suspension trigger)
  - `AI False Alarm` (False Alarm - Escalation, precision loss)
  - `Agreed TP` (True Attack - Valid escalation confirmed)
- **Double-Blind Review Workbench:**
  - Masked AI verdict until human submits review.
  - Three distinct determination buttons: `FALSE POSITIVE`, `TRUE POSITIVE`, `INCONCLUSIVE`.
  - Analyst notes and evidence references input.
  - Post-submission comparison reveal and agreement rate logging.
- **Dispute Adjudication Workflow:** Senior analyst override for divergent classifications.
- **Educational Explanation Box:** Explicitly clarifies the four levels of evidence:
  1. *Reviews Collected*
  2. *Verified Ground Truth*
  3. *Sufficient Statistical Evidence*
  4. *Production Accuracy Eligibility*

---

## 5. Tab 3: Advanced Configuration Reorganization

Implemented in `frontend/src/app/agent-intelligence-studio/page.tsx`:
Reorganized into collapsible, focused sub-sections:
- **Policy Editor (9 Sections):** Common Prompt, Rule-Specific Prompt, Detection Conditions, Required Evidence, TP Indicators, FP Indicators, Missing Info Criteria, Escalation Conditions, Analyst Questions.
- **Quality Gates (G1–G8):** Interactive gate cards with individual score, status badge, blocking issues, and recommendation pills.
- **SIEM Semantics:** Correlation logic, threshold definitions, window size, and detection pattern.
- **Evidence Contract:** Mandatory archetype fields, optional fields, and live extraction telemetry.
- **Simulation Lab:** Regression replay runner, test suite configuration, and baseline comparison.
- **Drift & Monitoring:** Event log for rule definition changes, policy drift, and revalidation alerts.
- **Version History & Production Safety:** Version comparison, cryptographic digests, approval gating, and emergency rollback.

---

## 6. Rule Listing Page Enhancements

Implemented in `frontend/src/app/detection-intelligence/page.tsx` and Studio Table Mode:
- Added compact **"Production Readiness"** column:
  - Readiness status badge (`ACTIVE`, `APPROVED`, `READY FOR APPROVAL`, `VALIDATING`, `LEARNING`, `BLOCKED`, `INCOMPLETE`).
  - Completed gates count (`X/8`).
  - Missing requirements count (`(Y missing)` in amber).
- Added **Production Readiness Filter Dropdown**:
  - `All Production Readiness`
  - `Blocked / Incomplete`
  - `Learning`
  - `Validating`
  - `Ready for Approval`
  - `Approved`
  - `Active`
- Maintained SIEM Baseline Status (`ACTIVE`, `INACTIVE`) in a distinct column.
- Clicking any rule row or "Studio" action button opens the simplified Studio Overview.
