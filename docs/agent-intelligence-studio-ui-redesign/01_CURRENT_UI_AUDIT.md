# Audit of Existing Implementation: Agent Intelligence Studio 2.0
**Document ID:** `01_CURRENT_UI_AUDIT.md`  
**Date:** 2026-11-19  
**System:** Verdictum AI — Agent Intelligence Studio 2.0  
**Scope:** Frontend UI/UX Architecture, Routes, State, Workspaces, and Controls  
**Target:** Modern Dark-Mode Enterprise Cybersecurity UI Modernization (Zero Functional Regression)

---

## 1. Executive Summary

Agent Intelligence Studio 2.0 (AIS 2.0) is Verdictum AI's central AI policy workbench. It empowers SOC security engineers and analysts to parse SIEM detection rules across 12 detection archetypes, synthesize structured AI decision policies, evaluate deterministic Quality Gates (G1–G8), conduct double-blind analyst incident reviews, monitor policy drift, run regression simulations, and manage policy version lifecycle and production readiness.

While the underlying domain model, policy compiler, and verification engines are rigorous, the existing user interface suffers from severe visual clutter, excessive vertical and horizontal spacing, inconsistent button hierarchies, loud saturated badges, redundant navigation tabs, and dense unformatted text blocks that overwhelm analysts.

This audit documents the current frontend architecture, existing UX friction points, and shared component dependencies to establish a baseline for a premium, compact, dark-mode cybersecurity redesign.

---

## 2. Frontend Framework & Architecture

| Layer | Technology | Details |
|---|---|---|
| **Framework** | Next.js 16.4.5 (App Router, Turbopack) | Server & Client Components (`"use client"` for interactive workspaces) |
| **UI Library** | React 19.3.0 | Modern Hooks (`useState`, `useEffect`, `useMemo`, `useRef`, `useCallback`) |
| **Styling** | Tailwind CSS v4 (`@tailwindcss/postcss`, `tailwindcss: ^4`) | Utility-first classes, custom CSS variables in `globals.css` |
| **Icons** | Lucide React (`^1.69.0`) | Consistent vector iconography |
| **State & Cache** | React Local State + Context | `AppContext` for global auth, role, customer, blind review toggle |
| **API Client** | Typed REST Fetcher (`frontend/src/lib/api.ts`) | Strict TypeScript interfaces for rules, prompts, gates, readiness, and metrics |

### Core Route Structure
- Primary Route: `/agent-intelligence-studio`
- Query Parameters:
  - `rule_id`: Deep links directly into a specific detection rule's studio workspace (e.g. `?rule_id=rule-heavy-tcp-fixed-port`).
  - `tab`: Direct navigation to primary workspaces (`overview`, `learning`, `advanced`).
  - `version_id`: Deep links to a specific policy version.

---

## 3. Component Hierarchy

```
frontend/src/app/agent-intelligence-studio/page.tsx (Main Controller)
├── VIEW 1: Rules Directory Table (viewMode === "table")
│   ├── Page Header (Title, Archetype Badge, Refresh, Bulk Audit, View LLM Prompt, Download Config, Open Studio)
│   ├── Top Metrics Cards (6 KPI tiles: Monitored Rules, Approved, Drafts, Avg Quality, Incomplete Specs, Drift)
│   ├── Informational Architecture Banner (Governance explanation)
│   ├── Filter & Search Toolbar (Search query, Archetype filter, Completeness, Severity, Baseline, Readiness)
│   ├── Rules Table (Columns: Rule Name, Severity, Archetype, Definition, Quality Score, Baseline Status, Readiness, Drift, Sticky Action)
│   ├── Pagination Controls (Items counter, Page size, Prev/Next buttons)
│   ├── Bulk Audit Modal (Batch audit progress & summary)
│   └── ActualPromptInspectorModal (Prompt payload capture/reconstruction)
│
└── VIEW 2: Rule Detail Workspace (viewMode === "studio")
    ├── Fail-Safe Error States:
    │   ├── ais-rule-not-found (404 Rule)
    │   └── ais-version-unavailable (404 Policy Version)
    ├── CompactPageHeader (Decoupled Rule Name, Subtitle, Archetype, SIEM Status, Policy Lifecycle, Rule Selector, Actions)
    ├── Primary Navigation Bar (3 Tabs: Overview, Review & Learning, Advanced Configuration)
    ├── Workspace 1: Overview (primaryTab === "overview")
    │   └── AgentIntelligenceStudioOverview.tsx
    │       ├── Decoupled 4-Part Status Strip (SIEM Rule, Active Policy, Selected Version, Readiness)
    │       ├── Metric Summary Cards (Quality, Structural Gates, Empirical G8, Production Readiness)
    │       ├── Contextual Next Action Card (Attention required & primary remediation action)
    │       ├── Guided Readiness Checklist (6 Stages: Define Detection -> Generate Policy -> Validate Quality -> Run Simulation -> Verify Ground Truth -> Evaluate Readiness)
    │       ├── Action Command Strip (Synthesize Draft, Validate Quality, Run Simulation, Review Incidents, Inspect Prompt)
    │       └── Rule Diagnostic Detail Accordion (Expandable technical metadata)
    ├── Workspace 2: Review & Learning (primaryTab === "learning")
    │   └── RuleLearningDashboard.tsx
    │       ├── Learning Profile Header & Lifecycle Transition Bar
    │       ├── 5 Statistical KPI Cards (Total Verified Reviews, Rule Accuracy, FP Precision, TP Recall, Wilson 95% Bound)
    │       ├── Sub-Navigation (Accuracy & Matrices, Double-Blind Queue, Promotion & Automation)
    │       ├── 2x2 Empirical Confusion Matrix (AI vs Ground Truth)
    │       ├── Double-Blind Review Workbench (Concealed AI labels, Incident Triage, Determination submission)
    │       └── Promotion & Safety Controls (Controlled/Autonomous requests, Kill-switch)
    └── Workspace 3: Advanced Configuration (primaryTab === "advanced")
        ├── Compact Section Sub-Navigation (Editor, Quality Gates, SIEM Semantics, Evidence Contract, Simulation, Drift, History)
        ├── Sub-view: Policy Editor (System prompt, strategy, questions builder, manual/intelligent draft save)
        ├── Sub-view: Quality Gates (G1-G8 cards, validation trigger, download JSON/MD/CSV export)
        ├── Sub-view: SIEM Semantics (Rule mapping, detection criteria, archetype classification)
        ├── Sub-view: Evidence Contract (Required SIEM fields, missing fields, token budget)
        ├── Sub-view: Simulation Lab (Replay engine, regression batch tester, incident evaluation)
        ├── Sub-view: Drift & Monitoring (Drift alerts, SIEM change log, acknowledge drift)
        ├── Sub-view: Version History (Historical version selector, details drawer, rollback/revoke actions)
        ├── Revoke Version Modal
        └── Rollback Confirmation Modal
```

---

## 4. Current UX Problems & Design Debt

### 4.1. Rules Directory Table (`viewMode === "table"`)
1. **Toolbar Overcrowding:** The top action bar displays 5 to 6 equally weighted buttons (Refresh, Bulk Audit, View Actual LLM Prompt, Download Config, Open Studio) without visual hierarchy.
2. **Horizontal Table Density:** 9 columns compete for horizontal width. Long rule names wrap awkwardly or push sticky action columns off smaller screens.
3. **Loud Badge Colors:** Saturated background colors (bright neon blues, greens, ambers, roses) fight for visual attention, creating "badge fatigue".
4. **Permanent Governance Banner:** A large static cyan info banner occupies 80px of vertical space above the table on every page load.
5. **Secondary Actions in Rows:** Each row includes loose icon buttons for Inspect Prompt, Download JSON, Download Markdown, and Open Studio.

### 4.2. Rule Detail Header
1. **Header Complexity:** The legacy view features a massive multi-row card with huge 4xl typography (`85/100`), decorative progress bars, and multiple status pills scattered horizontally.
2. **Metadata Redundancy:** Technical identifiers (rule UUID, raw event types, backend hashes) clutter the primary reading area instead of being cleanly nested under an on-demand details drawer.
3. **Selector Clutter:** The rule switcher dropdown and version selector are mixed with global action buttons without distinct grouping.

### 4.3. Overview Workspace (`AgentIntelligenceStudioOverview.tsx`)
1. **Information Fragmentation:** Analysts must scroll past large multi-line banners to see the 4 core health indicators.
2. **Nested Details Exposure:** Technical checklist steps expand into dense multi-paragraph debug texts that push actionable remediation out of view.
3. **Attention Card Noise:** Warning and error banners use heavy solid colored borders rather than polished enterprise card elevation.

### 4.4. Review & Learning Workspace (`RuleLearningDashboard.tsx`)
1. **Tab Proliferation:** Nested sub-tabs inside the learning workspace create cognitive overload.
2. **Dense Confusion Matrix:** The 2x2 matrix renders dense raw text without clear visual spatial mapping between AI prediction (X-axis) and Ground Truth determination (Y-axis).
3. **Misleading Baseline Fallbacks:** In scenarios where reviews are zero, several helper widgets previously attempted to display `0%` rather than clearly indicating `"Not Measurable"`.

### 4.5. Advanced Configuration Workspace
1. **Horizontal Tab Explosion:** Rendering 7 horizontal tabs (`editor`, `quality`, `intelligence`, `contract`, `simulation`, `drift`, `history`) causes horizontal wrapping or overflow on laptops and tablets.
2. **Simultaneous Technical Overload:** Heavy JSON editors, YAML syntax views, and simulation graphs are presented in large full-width blocks without clear visual breathing room.
3. **Permanent Version History Bar:** Historical version selection occupied a wide permanent column rather than a clean on-demand drawer or selector.

### 4.6. Quality Gates G1–G8
1. **Card Repetition:** Gates G1 through G8 are rendered as 8 large individual cards with full verbose details always visible, requiring excessive scrolling.
2. **Structural vs Empirical Blurring:** Structural gates (G1–G7) and empirical gate (G8) need crisp separation so users instantly grasp whether static compilation passed versus whether live incident data is missing.

---

## 5. Shared Dependencies & Impact Analysis

| Dependency | Location | Consumers | Modernization Guardrail |
|---|---|---|---|
| `CompactPageHeader` | `components/compact/CompactDesignSystem.tsx` | AIS Studio, AI Triage Workbench, Telemetry Hub | Maintain all prop contracts (`title`, `subtitle`, `archetype`, `siemStatus`, `lifecycleStatus`, `selector`, `actions`, `backAction`). |
| `IncidentVerdictMatrix` | `components/compact/IncidentVerdictMatrix.tsx` | AI Triage Workbench | Do not alter shared matrix props or classes. |
| `RuleLearningDashboard` | `components/learning/RuleLearningDashboard.tsx` | AIS Studio, Learning History | Ensure zero regression on API calls (`api.submitAnalystReview`, `api.adjudicateAnalystReview`, etc.). |
| `diagnostics.ts` | `lib/diagnostics.ts` | AIS Studio, Diagnostics, Overview | Preserve all 7 operational states and SIEM status derivation without changing return signatures. |
| `qualityExport.ts` | `lib/qualityExport.ts` | AIS Studio (Quality tab), Quality Tests | Preserve all export functions (`buildQualityGatesExportFile`, `formatQualityGatesMarkdown`, `formatQualityGatesCsv`, `escapeCsvCell`). |
| `ActualPromptInspectorModal` | `components/prompt-inspector/ActualPromptInspectorModal.tsx` | AIS Studio Table, Studio Workspace, Workbench | Modal interface must remain fully wired with identical props. |

---

## 6. Pre-Existing Defects Identified

1. **Table View Primary Action:** The table view lacked a dedicated primary draft generation trigger in the top bar when no rule was selected.
2. **Advanced Section Tab Overflow:** On viewport widths under 1280px, the 7 horizontal tabs in Advanced Configuration wrapped into 2 rows, disrupting layout alignment.
3. **Version History Drawer:** Historical version comparison lacked an instant toggleable drawer, forcing users to click through multiple tabs to view revoked or archived policies.
4. **G1–G8 Gate Details Density:** All 8 gates expanded verbose technical payloads simultaneously, making identifying the specific failing gate tedious.

---
*Audit completed. Proceed to Functionality Preservation Matrix (`02_FUNCTIONALITY_PRESERVATION_MATRIX.md`).*
