# Report 03: Verdictum AI — Simplified UI Design and Implementation

**Platform**: Verdictum AI — Agent Intelligence Studio 2.0  
**Target Rule UUIDs Preserved**:
- `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` (Website access policy violation: Same Source and Destination — Active v2 APPROVED, Candidate v3 DRAFT)
- `40498741-ee6b-4a71-9101-0d6d3f77154c` (Heavy TCP Host Scan On Fixed Port — Active v7 APPROVED, Candidate v8 DRAFT)  
**Status**: COMPLETED & VERIFIED

---

## 1. Executive Summary & Design Principles

The Agent Intelligence Studio (AIS) 2.0 user interface was redesigned to eliminate cognitive overload, excessive text, conflicting readiness metrics, and deeply nested configuration menus. The new architecture provides a clean, attractive, highly focused workspace tailored to two distinct operational personas while preserving 100% of underlying backend capabilities and test assertions:

1. **SOC Analysts (Daily Operations)**: Need a clean, distraction-free environment to triage pending SIEM incidents under double-blind evaluation protocols, submit authoritative ground-truth determinations (True Positive / False Positive / Insufficient Evidence), and review AI model alignment post-submission.
2. **SOC Leads & AI Engineers (Technical & Governance Control)**: Need immediate access to real GPU inference testing, empirical accuracy metrics, confusion matrices, prompt inspections, and policy version lifecycle management.

---

## 2. 3-Tab Primary Navigation Architecture

| Tab Index | Tab Name | Primary Persona | Core Components & Capabilities |
|---|---|---|---|
| **Tab 1** | **Review Incidents** | SOC Analysts (Default) | `<ReviewIncidentsWorkbench />`: Pending/Reviewed/Verified count strip, double-blind masking notice, compact incident queue, normalized telemetry vs raw logs split-panel, TP/FP/Insufficient Evidence determination selectors, investigation notes & evidence field citations, single `Submit Review` action, post-submission AI comparison reveal, and `Next Incident` workflow. Includes instantaneous toggle to Guided Policy Overview (6 stages). |
| **Tab 2** | **Test AI** | SOC Leads / Admins | `<AiTestWorkbench />`: Real GPU AWQ model banner (`Qwen/Qwen2.5-7B-Instruct-AWQ`), GPU health indicator, policy version target selector (Active vs Candidate Drafts), incident selector, `Run Real AI Test` button, effective vs raw verdict comparison, evidence grounding %, trust score, and expandable panels for evidence citations, raw LLM completion, and token telemetry. |
| **Tab 3** | **Accuracy & Learning** | SOC Leads / Governance | `<AccuracyLearningSummary />`: Clear ground-truth distinction. When verified reviews < 30, displays `Accuracy: NOT MEASURABLE` and `Next Action: Begin Independent Analyst Reviews`. When verified labels exist, displays verified TP, verified FP, AI/analyst agreement, empirical accuracy, TP recall, FP precision, abstention rate, G8 status, and interactive confusion matrix. |
| **Tab 4** | **Advanced Settings** | Administrators / SecOps | Sequestered 9-module technical workspace (Policy Editor, Quality Gates G1–G8, Evidence Contract, Rule XML, Prompt Inspector, Model Diagnostics, Simulation History, Production Governance, Manage Version History). |

---

## 3. Simplified Rule Header & Authoritative Next Recommended Action

### Compact Rule Header
The header displays decoupled, authoritative statuses without clutter:
```
[Website Access Policy Violation: Same Source and Destination]
SIEM Active | v2 Approved | v3 Draft | Supervised Learning
```
- **Rule Name & Selector**: Clean dropdown allowing rapid switching between detection rules without losing state.
- **SIEM Status**: Authoritative deployment state from SIEM registry (`SIEM Active` / `SIEM Inactive`), completely decoupled from AI policy approval.
- **Active Policy Version**: `v2 Approved` (or `No Active Version` if unpromoted).
- **Candidate Draft Version**: `v3 Draft` (or `No Draft`).
- **Learning Stage**: `Supervised Learning` / `Validation Ready` / `Production Verified`.

### Next Recommended Action Engine
Directly beneath the header, a dynamic banner displays the exact next step derived authoritatively from backend state:
1. **No policy exists** → `Create Draft Policy` (Jumps to Investigation Policy Editor).
2. **Policy unvalidated** → `Validate Draft Policy` (Triggers deterministic Gates G1–G8 validation).
3. **Validation failed on mandatory gates** → `Inspect Validation Issues` (Navigates to Quality Gates with blockers highlighted).
4. **Fewer than 30 reviews** → `Start Analyst Review` (Directs analyst to Double-Blind Review Workbench).
5. **30+ reviews collected, uncalculated accuracy** → `Evaluate Accuracy` (Jumps to Accuracy & Learning).
6. **All gates pass & accuracy verified** → `Request Administrator Approval` (Opens Production Approval Sign-off modal).
7. **Production active** → `Run AI Simulation / Verification` (Navigates to Test AI workbench).

---

## 4. Reconciliation of Readiness & Quality-Gate Statuses

### Root Cause of Inconsistent Statuses
- Prior implementations showed conflicting quality gate numbers across different tabs (e.g. 8 passed gates in Quality view vs 0 passed gates in Overview).
- **Cause 1**: The backend schema returns gate status `"PASS"` (`status: "PASS"`), whereas the Overview component only checked `g.status === "PASSED"`, failing to count gates.
- **Cause 2**: On network timeout or readiness API failure (`readinessError`), `passedGates` defaulted to numeric `0`, falsely displaying a valid "0 / 8 Passed" score to analysts.

### Applied Fixes
1. Gate status counting now explicitly accepts both `"PASS"` and `"PASSED"`:
   ```typescript
   Object.values(qualityAssessment.gate_results).filter((g) => g.status === "PASSED" || g.status === "PASS").length
   ```
2. When readiness evaluation fails, the UI renders `Unavailable` and displays a high-visibility warning card with an explicit **Retry** button rather than fabricating a zero score:
   ```typescript
   {readinessError ? "Unavailable" : `${passedGates ?? 0} / 8 Passed`}
   ```
3. Fail-closed invariant maintained: `effectiveApprovalEligible` strictly requires `!readinessError && readinessData.approval_eligible`.
