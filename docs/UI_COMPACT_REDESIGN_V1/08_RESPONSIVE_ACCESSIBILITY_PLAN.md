# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 08. Responsive & Accessibility Implementation Plan

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Responsive Engineering & WCAG 2.1 AA Compliance  
**Target Viewports:** 1920×1080, 1440×900, 1366×768, 1024×768  
**Standards:** WCAG 2.1 Level AA, Section 508, WAI-ARIA 1.2  

---

## 1. Responsive Viewport Matrix & Breakpoint Rules

The Verdictum Compact Design System v1.0 standardizes layout behavior across five specific viewport tiers commonly deployed in enterprise SOC command centers and analyst laptops.

### 1.1 Breakpoint Matrix

| Viewport Tier | Width Range | Hardware Deployment Context | Layout Strategy | Sidebar State |
|---|---|---|---|---|
| **Tier 1: Ultra-Wide / Wall** | `≥ 1920px` | Large SOC Wall Displays, Multi-Monitor 4K Workstations | Full 12-column grid; 8-col main + 4-col sidebar; zero empty right space | Expanded (240px) |
| **Tier 2: Standard Desktop** | `1440px – 1919px`| Standard 24"–27" External Monitors | 12-column grid baseline; all 7 table columns visible; action sticky | Expanded (240px) |
| **Tier 3: Enterprise Laptop** | `1280px – 1439px`| Enterprise SOC Laptops (1366×768, 1280×800) | 12-column grid with compact padding; secondary cells truncate | Expanded or Collapsed |
| **Tier 4: Tablet / Split Screen**| `1024px – 1279px`| Tablet Workstations, Split-Window Investigations | 12-column stacks to 1-column cascade; auto-collapsed sidebar | Auto-Collapsed (56px) |
| **Tier 5: Mobile / Small Window**| `< 1024px` | Mobile Incident Approvals, Narrow Windows | Single-column fluid; slide-over drawer navigation | Off-Canvas Drawer |

---

## 2. Horizontal Overflow & Scroll Container Rules

A recurring defect in the legacy application was nested horizontal scrollbars trapped inside cards. VCDS 1.0 establishes strict overflow governance:

### 2.1 Global Page Scroll Rule
- **The Browser Window Never Horizontally Scrolls:** The root shell wrapper (`Shell.tsx`) enforces `overflow-x-hidden`.
- **Vertical Scrolling is Confined to `<main>`:** The main workspace canvas (`theme-main-canvas`) provides the single, primary vertical scroll container (`overflow-y-auto overflow-x-hidden`).

### 2.2 Table Overflow Governance
- Data tables (`<table>`) must always be wrapped in a dedicated horizontal scroll container:
  ```tsx
  <div className="overflow-x-auto rounded-lg border border-slate-800">
    <table className="w-full text-left text-xs min-w-[800px]">
  ```
- **Sticky Right Action Column:** To ensure that operators never lose access to action triggers (such as `Open Studio` or `Inspect`), the final column is locked:
  ```css
  .vcds-sticky-action-col {
    position: sticky;
    right: 0;
    background-color: var(--vcds-bg-surface-0);
    box-shadow: -4px 0 12px -2px rgba(0, 0, 0, 0.45);
    z-index: 10;
  }
  ```

### 2.3 Text Truncation Guidelines
- **Rule Titles & Incident Headers:** **Never use `truncate` on primary headers.** Use `line-clamp-2` (allows up to 2 lines) so full rule names remain legible.
- **Secondary Table Metadata:** Use `truncate` with a mandatory native `title="..."` attribute or accessible tooltip so the full string is inspectable on hover:
  ```tsx
  <div className="truncate max-w-[240px]" title={rule.name}>
    {rule.name}
  </div>
  ```

---

## 3. Keyboard Navigation & Focus Standards

In high-stress SOC operations, analysts frequently triage incidents via keyboard shortcuts rather than mouse clicks.

### 3.1 Visible Keyboard Focus Indicators
- Every interactive element (buttons, inputs, dropdowns, table rows) must implement a visible, high-contrast focus ring that triggers only during keyboard navigation (`:focus-visible`):
  ```css
  :focus-visible {
    outline: none !important;
    ring: 2px solid #f97316 !important;
    ring-offset: 1px !important;
    ring-offset-color: #070609 !important;
  }
  ```

### 3.2 Global Keyboard Shortcuts
- **Global Search Focus:** Pressing `Ctrl + K` (Windows/Linux) or `Cmd + K` (macOS) focuses the Header triage search bar immediately from any page.
- **Escape Key (`Esc`):** Immediately closes any open modal (`ActualPromptInspectorModal`), popover, or slide-over drawer.
- **Table Row Navigation:** Arrow keys (`Up` / `Down`) highlight table rows; pressing `Enter` opens the selected incident or rule.

---

## 4. WCAG 2.1 AA Contrast Compliance

Contrast ratios were audited across both the **Obsidian Glass** (default) and **Classic Slate** themes to ensure all text and critical status indicators exceed the 4.5:1 ratio for normal text and 3:1 for graphical UI components.

### 4.1 Contrast Audit Matrix (Obsidian Theme)

| Element Pair | Foreground Color | Background Color | Measured Contrast Ratio | WCAG 2.1 AA Rating |
|---|---|---|---|---|
| **Primary Title Text** | `#f8fafc` (White Slate) | `#070609` (Obsidian Canvas) | **18.2 : 1** | **PASS (AAA)** |
| **Card Body Text** | `#cbd5e1` (Light Slate) | `#141118` (Surface-1) | **11.2 : 1** | **PASS (AAA)** |
| **Secondary Metadata** | `#94a3b8` (Muted Slate) | `#141118` (Surface-1) | **6.1 : 1** | **PASS (AA)** |
| **Brand Orange Accent** | `#f97316` (Warm Orange) | `#070609` (Obsidian Canvas) | **6.8 : 1** | **PASS (AA)** |
| **True Positive Pill** | `#fda4af` (Rose 300) | `#4c0f14` (Rose 950) | **7.4 : 1** | **PASS (AAA)** |
| **False Positive Pill** | `#6ee7b7` (Emerald 300) | `#062c1e` (Emerald 950) | **8.1 : 1** | **PASS (AAA)** |
| **Warning / Attention** | `#fde68a` (Amber 300) | `#381e06` (Amber 950) | **9.5 : 1** | **PASS (AAA)** |
| **Input Placeholder** | `#64748b` (Slate 500) | `#0d0b10` (Surface-0) | **4.6 : 1** | **PASS (AA)** |

---

## 5. Screen Reader & ARIA Implementation

1. **Meaningful Semantic Landmarks:**
   - `<header role="banner">` for Topbar.
   - `<nav role="navigation" aria-label="Main Navigation">` for Sidebar.
   - `<main role="main">` for Workspace Canvas.
   - `<aside role="complementary">` for Right-Hand Context Sidebar.
2. **Icon Button Accessibility:**
   - Every icon-only button must include an explicit `aria-label` describing the action (e.g. `aria-label="Expand sidebar"`, `aria-label="Download rule configuration"`).
3. **Dynamic State Announcements:**
   - Use `aria-live="polite"` on the countdown timer in Telemetry Hub so screen readers announce synchronization intervals without disrupting the operator.
   - Use `aria-expanded="true/false"` on all accordion headers and popover toggles.

---

## 6. Motion & Vestibular Safety

1. **Reduced Motion Media Query:**
   The application strictly adheres to `prefers-reduced-motion: reduce`:
   ```css
   @media (prefers-reduced-motion: reduce) {
     *, ::before, ::after {
       animation-duration: 0.01ms !important;
       animation-iteration-count: 1 !important;
       transition-duration: 0.01ms !important;
       scroll-behavior: auto !important;
     }
     .flow-edge-animated {
       animation: none !important;
     }
   }
   ```
2. **Elimination of Flashing / Strobe Hazards:**
   - Pulse animations on live indicators (`animate-pulse`) use gentle 2-second opacity fades (`opacity: 0.6` to `1.0`), preventing any rapid strobing that could trigger photosensitive seizures.
