# UI/UX Design Specification: Agent Intelligence Studio 2.0
**Document ID:** `03_UI_UX_DESIGN_SPECIFICATION.md`  
**Date:** 2026-11-19  
**System:** Verdictum AI — Agent Intelligence Studio 2.0  
**Design Standard:** Enterprise Cybersecurity Workbench | Modern Obsidian & Navy Theme

---

## 1. Visual Hierarchy & Design System Tokens

The visual design system is strictly scoped to the Agent Intelligence Studio experience and harmonizes with Verdictum AI's Obsidian dark theme.

### 1.1. Color Tokens
```css
/* Backgrounds & Surfaces */
--surface-canvas:      #0B1020; /* Deep obsidian navy canvas */
--surface-card:        #111827; /* Dark charcoal card background */
--surface-elevated:    #171F32; /* Elevated workspace & modal surface */
--surface-overlay:     #1E293B; /* Dropdowns, tooltips, flyouts */

/* Borders & Dividers */
--border-subtle:       rgba(255, 255, 255, 0.06);
--border-card:         rgba(255, 255, 255, 0.09);
--border-interactive:  rgba(139, 92, 246, 0.35); /* Subtle purple ring */

/* Primary & Secondary Brand Accents */
--accent-purple:       #8B5CF6; /* AI Synthesis & Policy intelligence */
--accent-sky:          #38BDF8; /* Telemetry, Detection & Navigation */
--accent-cyan:         #06B6D4; /* SIEM Semantics & Active indicators */

/* Status & Lifecycle Accents (WCAG AA Non-Text Contrast >= 3.0:1) */
--status-success:      #10B981; /* Approved, Verified, Passing */
--status-warning:      #F59E0B; /* Revalidation, Drift, Needs Action */
--status-critical:     #F43F5E; /* Hard Gate Failure, Revoked, Blocked */
--status-neutral:      #64748B; /* Not evaluated, Unavailable */

/* Text Hierarchy */
--text-primary:        #F8FAFC; /* Headings, primary values, active labels */
--text-secondary:      #94A3B8; /* Subtitles, column headers, metadata */
--text-tertiary:       #64748B; /* Inactive tabs, disabled states, timestamps */
```

### 1.2. Spacing & Radius Rules
- **Grid Baseline:** 8px system (`gap-2`, `gap-3`, `gap-4`, `p-3`, `p-4`, `p-6`).
- **Corner Radius:**
  - Cards & Workspaces: `rounded-xl` (12px) to `rounded-2xl` (16px).
  - Controls, Badges, Buttons: `rounded-lg` (8px) or `rounded-md` (6px).
  - Category Pills: `rounded-full` (9999px).
- **Elevation:** Soft ambient shadow (`shadow-md`, `shadow-xl`) paired with 1px border. No loud glowing borders.

---

## 2. Button & Control Hierarchy

Instead of displaying multiple equal-priority buttons in toolbars, all actions follow a disciplined 3-tier hierarchy:

1. **Tier 1 (Primary Call to Action):**
   - High-contrast, solid fill button (`bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold`).
   - Represents the single logical "Next Step" (e.g. *Synthesize Draft*, *Validate Quality*, *Approve Policy*).
2. **Tier 2 (Secondary Operations):**
   - Ghost or border button (`border border-slate-700/80 bg-slate-900/80 hover:bg-slate-800 text-slate-200`).
   - Used for immediate contextual actions (e.g. *Refresh*, *Inspect LLM Prompt*, *Simulation Replay*).
3. **Tier 3 (Overflow Menu & Dropdowns):**
   - Compact three-dots (`...`) or *More Actions* dropdown (`ChevronDown`).
   - Houses less frequently executed commands (e.g. *Bulk Quality Audit*, *Download JSON/MD Config*, *Revoke Version*, *Rollback*).

---

## 3. Screen-by-Screen Layout Specifications

### 3.1. Rules Directory Table (`viewMode === "table"`)
```
+---------------------------------------------------------------------------------------------------+
|  [Logo/Icon] Agent Intelligence Studio                                  [Refresh] [More v] [Open] |
|  Build, validate, and govern AI detection policies.                                              |
+---------------------------------------------------------------------------------------------------+
|  [6 Compact KPI Cards: Monitored | Approved | Drafts | Avg Quality | Incomplete | Drift Alert]    |
+---------------------------------------------------------------------------------------------------+
|  [Search Input (w-full)]  [Archetype v] [Completeness v] [Severity v] [Baseline v] [Readiness v]  |
+---------------------------------------------------------------------------------------------------+
|  Rule Name & Event Type | Severity | Archetype | Quality | Policy Status | Readiness | [Actions]  |
|  -----------------------+----------+-----------+---------+---------------+-----------+----------- |
|  Heavy TCP Host Scan... | MEDIUM   | NET_SCAN  | 85/100  | v7 Active     | EVALUATED | [Open] [.] |
|  Suspicious PowerShell  | HIGH     | PROC_EXEC | 92/100  | v2 Draft      | PILOT     | [Open] [.] |
+---------------------------------------------------------------------------------------------------+
|  Showing 1-15 of 48 detection rules                                            [Prev] [1] [2] [Next]
+---------------------------------------------------------------------------------------------------+
```
- **Sticky Actions Column:** Rightmost column remains sticky with blurred background.
- **Progressive Table Headers:** Sortable indicators, clean monospaced event types, subtle hover states.

### 3.2. Rule Detail Workspace Header (`viewMode === "studio"`)
```
+---------------------------------------------------------------------------------------------------+
|  [<- Rules List]  Heavy TCP Host Scan On Fixed Port                      [Rule: v] [Version: v]    |
|  NETWORK_SCAN · Medium Severity · SIEM Active · Policy Approved           [Validate] [Primary CTA] |
|  [v View Rule Details & Authoritative Metadata]                                                   |
+---------------------------------------------------------------------------------------------------+
|  [ Overview ]          [ Review & Learning ]          [ Advanced Configuration ]                  |
+---------------------------------------------------------------------------------------------------+
```
- **Expandable Rule Details Section:** Toggling reveals rule ID (`rule-heavy-tcp-fixed-port`), full detection objective, SIEM query syntax, data sources, and correlation thresholds in a clean 3-column drawer without pushing the workspace down permanently.

### 3.3. Overview Workspace (`primaryTab === "overview"`)
Answers four vital operational questions at a glance:
1. **What is this rule?** -> Top header + Rule Details drawer.
2. **Is the policy valid?** -> 4-Indicator Rule Health Strip (Quality Score, G1–G7 Structural Status, G8 Empirical Status, Production Readiness).
3. **Is it safe and ready?** -> Contextual Attention Panel explaining exact blockers (e.g. *"Empirical validation is pending 30 verified analyst reviews"*).
4. **What should I do next?** -> 6-Stage Guided Workflow checklist with interactive step jumping.

### 3.4. Review & Learning Workspace (`primaryTab === "learning"`)
- **Summary Cards (5 Metrics):**
  - Total Verified Reviews (e.g. `0` or `35`)
  - Rule Accuracy (e.g. `Not Measurable` when reviews < 10, or `94.2%`)
  - False Positive Precision
  - True Positive Recall
  - Wilson 95% Confidence Lower Bound
- **Sub-Navigation Tabs:**
  - `Accuracy & Matrices`: 2x2 Empirical Confusion Matrix, agreement rates, disagreement impact.
  - `Double-Blind Review Queue`: Focused incident review workbench with concealed AI labels.
  - `Promotion & Safety Governance`: Controlled/Autonomous promotion requests, kill-switch.

### 3.5. Advanced Configuration Workspace (`primaryTab === "advanced"`)
Replaces the crowded 7 horizontal tabs with a modern two-column enterprise layout:
```
+---------------------------+-----------------------------------------------------------------------+
| CONFIGURATION MODULES     | [SELECTED MODULE WORKSPACE]                                           |
|                           |                                                                       |
| > Policy Editor           | (Renders focused workspace for Policy Editor)                         |
|   Quality Gates (G1-G8)   |                                                                       |
|   SIEM Semantics          | - Full width available for code/schema editing                        |
|   Evidence Contract       | - Clean toolbar at top of workspace                                   |
|   Simulation Lab          | - Unsaved changes indicators                                          |
|   Drift Monitoring        | - Dedicated validation triggers                                       |
|   Version History         |                                                                       |
+---------------------------+-----------------------------------------------------------------------+
```
- **Responsive Adaptability:** On viewports < 1024px, the left sidebar becomes a compact horizontal scroll pill-bar or dropdown selector.

### 3.6. Quality Gates Presentation (G1–G8)
- Top Card: **Policy Validation Summary**
  - Overall Quality Score (`85/100`)
  - Structural Status (G1–G7: `7/7 Passed`)
  - Empirical Status (G8: `Insufficient Data` or `Verified`)
  - Blocking Findings Count (`0` or `N issues`)
  - Export Menu (JSON, Markdown, CSV)
- Interactive G1–G8 Accordion / Grid:
  - Collapsed Gate: Gate Code (e.g. `G1`), Name (`Rule Definition Integrity`), Status Pill (`PASSED · 10/10`), One-line summary.
  - Expanded Gate: Full rationale, missing fields, validation payload, and direct remediation action.

### 3.7. Version History Simplification
- Default state: Compact version badge & selector in the top-right header: `Current: v7 · Approved (Active)`.
- On demand: Clicking opens the **Version History Workspace** or slide-over drawer showing chronological history:
  - Version Number & Timestamp
  - Author / Generator (AI Synthesizer vs Manual Edit)
  - Lifecycle Status (Draft, Approved, Revoked, Archived)
  - Active runtime association
  - Contextual actions: *Compare Diff*, *Rollback to Version*, *Revoke Version*.

---

## 4. Accessibility & Micro-Interactions

- **Keyboard Focus:** High-visibility outline (`focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:outline-none`).
- **Reduced Motion:** Respects `prefers-reduced-motion: reduce` for smooth CSS transitions.
- **Empty & Error States:** Clear SVG illustrations, diagnostic descriptions, and non-blocking retry buttons.
- **Strict Non-Fabrication:** Authoritative responses from backend API are displayed directly without artificial rounding or simulated pass badges.

---
*Specification approved. Proceed to Phase 4: Implementation Report (`04_IMPLEMENTATION_REPORT.md`).*
