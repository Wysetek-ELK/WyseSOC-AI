# Root Cause Analysis: Missing "View Actual LLM Prompt" Button

**Document ID:** AIS-2.0-PROMPT-INSPECT-01  
**Feature:** Actual LLM Prompt Inspector 1.1  
**Date:** 2026-11-14  
**Author:** Antigravity AI Engine  
**Status:** RESOLVED & VERIFIED  

---

## 1. Executive Summary

During testing of the Agent Intelligence Studio 2.0 Actual LLM Prompt Inspector, users and SOC engineers reported that the **"View Actual LLM Prompt"** button was not visible anywhere in the live user interface. Although backend APIs and schema models had been registered, the button was completely inaccessible in the primary workflow.

A comprehensive architectural and front-end code investigation was conducted across `frontend/src/app/agent-intelligence-studio/page.tsx`, `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`, and `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx`. 

Three distinct root causes were identified and resolved.

---

## 2. Root Cause Breakdown

### Root Cause 1: Conditional Early Return in Table View (`page.tsx`)
In `frontend/src/app/agent-intelligence-studio/page.tsx`:
```tsx
// Line 1009
if (viewMode === "table") {
  return (
    <div className="space-y-4">
      ...
    </div>
  );
}
```
At line 1054 of the table header, a trigger button for "View Actual LLM Prompt" had been placed. However, `<ActualPromptInspectorModal />` was mounted at line 3970, which resided exclusively within the `viewMode === "studio"` return statement.

**Consequence:** When an analyst was on the Rules Directory Table (the landing view of Agent Intelligence Studio), clicking the button updated React state (`setPromptInspectorOpen(true)`), but because the modal component was not present in the DOM tree of that return block, absolutely nothing rendered on screen.

### Root Cause 2: Complete Absence from Compact Mode (`AgentIntelligenceStudioOverview.tsx`)
In Verdictum AI, the default user interface is **Compact Mode (3-Tab Architecture)** (`compactUi === true`). When an analyst navigates from the table to a rule's details, the application mounts `<AgentIntelligenceStudioOverview />`.

Inspection of `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` revealed:
- Section 1 (Quick Actions Strip, lines 480–540) included buttons for:
  - `CompactVersionSelector`
  - `Synthesize Draft`
  - `Validate Quality`
  - `Simulation`
  - `Approve`
- **There was zero code or button for "View Actual LLM Prompt" or "Preview Compiled Prompt".**
- `AgentIntelligenceStudioOverviewProps` did not expose any callback props to open the prompt inspector.

**Consequence:** 100% of users operating in the default, modern Compact UI mode could not see or access the prompt inspector.

### Root Cause 3: Omission from Legacy Studio Actions & Rule Details
Even if a user manually toggled to the Legacy 7-Tab View (`compactUi === false`), lines 1838–1890 contained only:
- `Synthesize Intelligent Draft`
- `Validate Quality`
- `Run Simulation`
- `Approve & Activate`

The button was omitted from the legacy studio hero action column as well.

---

## 3. Remediation & Implementation Details

To make the feature universally accessible and intuitive for L1 analysts and SOC engineers, four entry points were implemented:

### Location 1 — Rule Details (Compact Mode)
Added prominent, accessible buttons in `AgentIntelligenceStudioOverview.tsx` Section 1 (Quick Actions & Version Selector):
1. **View Actual LLM Prompt** (Emerald badge with `Terminal` icon): Opens the inspector modal in runtime capture mode for the active rule, preloading recent execution captures.
2. **Preview Compiled Prompt** (Sky badge with `Eye` icon): Opens the inspector in live compiled template preview mode, allowing analysts to inspect the exact prompt structure even before runtime executions exist.

### Location 1 — Rule Details (Legacy 7-Tab Mode)
Added both **View Actual LLM Prompt** and **Preview Compiled Prompt** buttons in the action column of the legacy studio view (`page.tsx` lines 1905–1935).

### Location 1 — Rules Directory Table Header & Rows
1. Added modal mount `<ActualPromptInspectorModal />` inside `viewMode === "table"`, so clicking the header button immediately renders the inspector modal.
2. Added an inline `Terminal` icon button in every rule row of the Rules Directory table (`page.tsx` line 1435), enabling 1-click prompt inspection directly from the catalog.

### Location 2 — Incident Results & Simulation Drilldowns
1. **Per-Incident Simulation Verdicts:** Enhanced the simulation results table (`page.tsx` line 3530) with an inline **Inspect Prompt** button on every incident result row.
2. **Simulation Drilldown Modal:** Added an inline `Terminal` inspection button next to the incident ID in all 6 simulation drilldown stages (Scanned, Rule-Matched, Analyst-Labeled, Eligible Ground Truth, Excluded, Evaluated).
3. **AI Triage Workbench:** Added a **View Actual LLM Prompt** button directly inside the authoritative AI Verdict banner in `frontend/src/app/ai-triage-workbench/[id]/page.tsx`.

---

## 4. Verification Matrix

| Entry Point | Location in UI | Trigger Behavior | Verification Status |
|:---|:---|:---|:---|
| **Rule Details (Compact)** | Quick Actions Strip in Overview | Preloads rule captures or opens capture modal | **VERIFIED (Pass)** |
| **Rule Details (Preview)** | Quick Actions Strip in Overview | Opens template preview with synthetic telemetry | **VERIFIED (Pass)** |
| **Header Action** | CompactPageHeader Top Bar | Opens prompt inspector for current rule | **VERIFIED (Pass)** |
| **Legacy 7-Tab** | Studio Action Column | Opens prompt inspector for current rule/version | **VERIFIED (Pass)** |
| **Rules Directory** | Table Header & Table Row | Opens prompt inspector without leaving catalog | **VERIFIED (Pass)** |
| **Simulation Rows** | Per-Incident Results Table | Inspects exact prompt sent for that simulation case | **VERIFIED (Pass)** |
| **Drilldown Modal** | Drilldown Inspection Rows | Inspects prompt for individual evaluated incidents | **VERIFIED (Pass)** |
| **Triage Workbench** | AI Verdict Header | Inspects prompt sent to Local LLM for that incident | **VERIFIED (Pass)** |
