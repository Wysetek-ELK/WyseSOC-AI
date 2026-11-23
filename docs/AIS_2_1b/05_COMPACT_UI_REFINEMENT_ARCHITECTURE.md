# AIS 2.1b — 05: Compact UI Refinement Architecture

## 1. Visual Hierarchy & Vertical Space Reduction

The primary UI objective of AIS 2.1b is transforming Agent Intelligence Studio into a compact, clean, modern SOC analyst workspace without reducing any underlying functional capabilities.

### Before vs. After Vertical Budget Comparison (1440x900 Desktop)

| Layout Component | Pre-Refinement (AIS 2.1a) | Post-Refinement (AIS 2.1b) | Space Saved |
| :--- | :--- | :--- | :--- |
| **Section 1: Rule Header & Status** | `CompactPageHeader` (65px) + Decoupled Strip (48px) = **113px** | Unified Compact Header = **42px** | **-71px (-63%)** |
| **Section 2: Recommended Next Action** | Multi-line Banner = **78px** | Slim Contextual Notice = **36px** | **-42px (-54%)** |
| **Section 3: Primary Navigation** | Multi-line Subtitled Tabs = **44px** | Compact 3-Tab Bar + Settings = **34px** | **-10px (-23%)** |
| **Section 4: Model & Policy Strip** | Heavy Technical Container = **62px** | Slim Context Strip = **32px** | **-30px (-48%)** |
| **Section 5: Summary Metric Cards** | 6 Full-Sized Cards = **110px** | 4 Prominent Cards + Secondary Strip = **74px** | **-36px (-33%)** |
| **Cumulative Top-of-Screen Offset** | **407px** | **218px** | **-189px (-46%)** |
| **Incident Table Top Position** | **~675px** (Near fold) | **~420px** (Dominant working area) | **Table rows fully visible without scrolling** |

---

## 2. Component Design Specifications

### Section 1: Compact Rule Toolbar
- **Unified Structure:** Renders Back to Rules button, Rule Title, Active Policy Status (`v7 Approved`), Candidate Draft (`v8 Draft`), Rule Selector dropdown, and Action Menu on a single line.
- **Secondary Details:** Technical archetype (`DETECTION ENGINE`), SIEM Status (`SIEM Active`), Customer Tenant (`DEFAULT`), and Detection Objective are encapsulated in a collapsible **Details** drawer, completely eliminating permanent vertical waste.

### Section 2: Recommended Next Action Notice
- **Contextual Strip:** Replaced oversized banner with a single-line alert:
  `Next Recommended Action: Action needed: Pilot class-balance deficit: requires >= 10 TP and >= 10 FP for Tier 2 Supervised Pilot qualification.`
- **Action Control:** Features a single high-contrast button (`data-testid="next-action-button"`) linked directly to `Review Incidents`.

### Section 3: Primary Navigation
- **3 Primary Tabs:**
  1. `Review Incidents` (Overview)
  2. `Test AI` (AI Evaluation Tracking)
  3. `Accuracy & Learning` (Analyst Review & Learning)
- **Secondary Settings:** `Advanced Settings` positioned as a distinct secondary control with tooltip and blocker badge, rather than an equal primary workflow tab.

### Section 4: Model & Policy Context Strip
- Within Test AI tab: replaced large container with:
  `Model: Qwen2.5-7B | GPU Online | Policy v7 Active` + Target policy dropdown + Missing evaluation button.

### Section 5: Prioritized Evaluation Summary Cards
- **4 Prominent Cards (2x2 on mobile, 1x4 on desktop):**
  1. `Current Incidents` (neutral slate, displaying both Current Incidents and Total Incidents)
  2. `Decisive Verdicts` (emerald)
  3. `Abstained` (amber)
  4. `Not Evaluated` (gray)
- **Secondary Outcomes:** `Rejected` and `Failed/Timeout` indicators are integrated into a slim sub-strip (`Secondary Outcomes: Rejected: 0 • Failed/Timeout: 0`), avoiding wasted card space when 0 while highlighting actionable failures if present.

### Section 6: Dominant Incident Evaluation Table
- Tightened container padding to `p-3`, keeping search, status filter pills, and table headers above 450px on standard desktop screens.
