# 06. THREE-TAB WORKSPACE CONSOLIDATION & ADMINISTRATIVE SETTINGS ARCHITECTURE

## Verdictum AI — Agent Intelligence Studio 2.1
**Powered by WYSETEK Systems**

---

## 1. Executive Summary

In Agent Intelligence Studio 2.0, user feedback indicated significant cognitive load caused by excessive, multi-level nested navigation. Operational analysts were confronted with multiple conflicting toggles:
1. Workspace Level: Table View vs. Studio View.
2. Tab Level: Review Incidents vs. Test AI vs. Accuracy & Learning vs. Advanced Settings.
3. Subview Level: Incident Review Workbench vs. Policy Overview & 6 Stages.
4. Component Level: Queue Mode vs. Tracking Table Mode inside the incident review workbench.
5. Nested Configuration: 9 different modules across multiple sub-drawers.

In **Agent Intelligence Studio 2.1**, the user interface has been radically simplified and streamlined into a clean, role-tailored layout:
- **Three Operational Tabs** (focused on the daily workflow of SOC analysts):
  - **Tab 1: Incidents** (`incidents` / `overview`): Direct incident review workbench. The nested `reviewSubView` segmented control ("Incident Review Workbench" vs "Policy Overview & 6 Stages") and the redundant internal view switcher have been eliminated.
  - **Tab 2: AI Evaluation** (`ai_evaluation` / `test_ai`): Unified AI testing and evaluation tracking. Combines the 6-card Evaluation Coverage Summary, the Incident Evaluation Tracking Table with filter pills and search, and the interactive single-incident AI Test panel.
  - **Tab 3: Accuracy** (`accuracy` / `learning`): Accuracy & Learning summary, empirical confusion matrix, calibration metrics, and an expandable ground-truth review engine.
- **One Administrative Settings Control**:
  - A clean, prominent Settings button in the primary navigation header opening the Administrative Configuration workbench.
  - Houses all 10 administrative modules:
    0. Policy Overview & Readiness (6 Stages) — preserving the complete production readiness lifecycle without cluttering the daily incident review workflow.
    1. Investigation Policy (9 canonical sections)
    2. Quality Gates (G1–G8 validation)
    3. Evidence Contract Feasibility
    4. Rule XML & Detection Semantics
    5. Prompt Inspector & Telemetry
    6. Model Diagnostics & AWQ Settings
    7. Simulation Lab & Replay
    8. Production Governance & Drift
    9. Manage Version History & Provenance
  - Preserves the **Legacy 7-Tab View** toggle strictly for authorized administrators.
- **Enterprise Dual Branding**:
  - Prominently displays **Verdictum AI 2.1 • Powered by WYSETEK Systems** across catalog headers, studio toolbars, and operational banners.

---

## 2. Structural Comparison: AIS 2.0 vs. AIS 2.1

```
====================================================================================================
AGENT INTELLIGENCE STUDIO 2.0 (LEGACY NESTED NAVIGATION)
====================================================================================================
├── [Primary Tab: Review Incidents]
│   ├── [SubView Toggle: Incident Review Workbench]
│   │   ├── [Mode Toggle: Double-Blind Review Queue]
│   │   └── [Mode Toggle: Incident Evaluation Tracking Table] (Redundant duplicate)
│   └── [SubView Toggle: Policy Overview & 6 Stages]
├── [Primary Tab: Test AI]
│   └── [AiTestWorkbench] (Lacked tracking inventory)
├── [Primary Tab: Accuracy & Learning]
│   └── [AccuracyLearningSummary]
└── [Primary Tab: Advanced Settings]
    └── [9 Nested Sections]

====================================================================================================
AGENT INTELLIGENCE STUDIO 2.1 (CONSOLIDATED THREE-TAB + SETTINGS ARCHITECTURE)
====================================================================================================
├── [Primary Tab 1: Incidents] (data-testid="tab-overview")
│   └── Direct ReviewIncidentsWorkbench
│       ├── Double-Blind Review Queue
│       ├── Canonical Evidence Record Viewer (with Metadata Fallback)
│       └── Independent Analyst Determination Form
├── [Primary Tab 2: AI Evaluation] (data-testid="tab-test-ai")
│   └── Unified AiTestWorkbench
│       ├── Section A: 6 Evaluation Coverage Summary Cards (Total, Decisive, Abstained, Rejected, Failed, Not Evaluated)
│       ├── Section B: Incident Evaluation Tracking Table (Filter Pills, Search, Row Selection, Double-Blind Isolation)
│       └── Section C: Real Local AWQ Model Inference & Diagnostic Test Panel
├── [Primary Tab 3: Accuracy] (data-testid="tab-learning")
│   └── AccuracyLearningSummary
│       ├── Empirical Accuracy, Precision, Recall, F1 Scores
│       ├── Confusion Matrix (TP, FP, TN, FN, Abstentions)
│       └── Expandable Ground-Truth Review Engine
└── [Administrative Settings Control] (data-testid="tab-advanced")
    └── Administrative Settings & Configuration Workbench
        ├── Module 0: Policy Overview & Readiness (6 Stages) [Moved from Tab 1]
        ├── Module 1: Investigation Policy (9 Sections)
        ├── Module 2: Quality Gates (G1–G8)
        ├── Module 3: Evidence Contract Feasibility
        ├── Module 4: Rule XML & Detection Semantics
        ├── Module 5: Prompt Inspector & Telemetry
        ├── Module 6: Model Diagnostics & AWQ Settings
        ├── Module 7: Simulation Lab & Replay
        ├── Module 8: Production Governance & Drift
        ├── Module 9: Manage Version History & Provenance
        └── Legacy 7-Tab Layout Toggle (Admin-only)
```

---

## 3. Component Architecture & State Management

### 3.1 Primary Navigation State
In `frontend/src/app/agent-intelligence-studio/page.tsx`:
```typescript
const [primaryTab, setPrimaryTab] = useState<
  "incidents" | "ai_evaluation" | "accuracy" | "settings" | "overview" | "test_ai" | "learning" | "advanced"
>("incidents");
```
- Backwards compatibility is preserved for URL routing (`?tab=overview`, `?tab=test_ai`, `?tab=learning`, `?tab=advanced` normalize automatically to `incidents`, `ai_evaluation`, `accuracy`, and `settings`).
- All existing `data-testid` attributes (`tab-overview`, `tab-test-ai`, `tab-learning`, `tab-advanced`, `ais-primary-tabs`) remain active to ensure zero breakage for automated end-to-end regression test suites.

### 3.2 Tab 1: Review Incidents Consolidation
- File: `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx`
- The duplicate internal tracking view toggle (`activeViewMode: "queue" | "tracking"`) and embedded tracking table were removed, eliminating visual confusion with the AI evaluation tracking feature.
- The parent `page.tsx` no longer wraps Tab 1 in a segmented subview switcher. Selecting **Incidents** brings the analyst directly to the incident queue.
- Normalized evidence viewer automatically handles canonical field normalization and falls back to incident top-level metadata when child logs are absent.

### 3.3 Tab 2: AI Evaluation Tracking & Test Integration
- File: `frontend/src/components/compact/AiTestWorkbench.tsx`
- Integrated 6 Summary Cards: Total Incidents, Decisive Predictions, Abstained Cases, Validation Rejections, Execution Failures, and Not Evaluated.
- Incident Evaluation Tracking Table features:
  - Filter pills: `ALL`, `NOT_EVALUATED`, `EVALUATED_DECISIVE`, `ABSTAINED`, `VALIDATION_REJECTED`, `EVALUATION_FAILED`.
  - Text search: Matches FortiSIEM incident ID, source IP, or event type.
  - Double-blind masking: Obscures AI verdicts for unreviewed incidents when viewed by non-administrators.
  - Interactive row synchronization: Selecting an incident in the tracking table automatically loads it into Section C for immediate inference or actual prompt inspection.

### 3.4 Tab 3: Accuracy & Empirical Learning
- File: `frontend/src/components/compact/AccuracyLearningSummary.tsx`
- Visualizes empirical accuracy calculated strictly against verified human ground truth.
- Distinguishes clearly between 0 decisive predictions and low accuracy.
- Features deep links to Tab 1 (`Start Analyst Review`) and Tab 2 (`Run AI Verification`).

### 3.5 Administrative Settings Drawer & Policy Overview Integration
- When an administrator clicks **Settings**, the primary view switches to the 10-module configuration panel.
- Module 0: **Policy Overview & Readiness** provides full access to `AgentIntelligenceStudioOverview`, including the 6 lifecycle stages, hard gate enforcement, and rollback controls.
- The legacy 7-tab view toggle is preserved in the header actions for advanced configuration scenarios.

---

## 4. Verification & Validation Summary

| Requirement | Implementation Detail | Status |
| :--- | :--- | :---: |
| **Three Operational Tabs** | Incidents, AI Evaluation, Accuracy | **VERIFIED** |
| **One Settings Control** | Dedicated Settings button opening 10 modules | **VERIFIED** |
| **Tab 1 Subview Removed** | Segmented switcher eliminated; direct queue render | **VERIFIED** |
| **Tab 2 Unified Tracking** | 6 KPI cards + Tracking table + Test panel | **VERIFIED** |
| **Tab 3 Accuracy Display** | Empirical metrics + Ground truth dashboard | **VERIFIED** |
| **Policy Overview Relocation**| Relocated to Module 0 in Settings | **VERIFIED** |
| **Enterprise Branding** | Verdictum AI 2.1 • Powered by WYSETEK Systems | **VERIFIED** |
| **TestID Stability** | `tab-overview`, `tab-test-ai`, `tab-learning`, `tab-advanced` preserved | **VERIFIED** |
