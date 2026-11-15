# Verdictum Compact Design System (VCDS 1.0) Specification & Results

**Document ID:** `VCDS-V1-IMP-06`  
**Status:** Completed & Verified  
**Date:** 2026-11-15  
**Version:** 1.0.0  

---

## 1. Overview & Architectural Goals

The **Verdictum Compact Design System (VCDS 1.0)** is an enterprise-grade UI design system engineered specifically for SOC (Security Operations Center) analysts, detection engineers, and incident responders. 

Prior to VCDS 1.0, the UI suffered from disparate component dimensions, excessive whitespace, conflicting global CSS rules with brute-force `!important` flags, floating header/sidebar gaps, and unpredictable table column clipping. 

VCDS 1.0 delivers:
1. **Cozy Information Density:** Maximizes above-the-fold operational context without causing eye strain.
2. **Deterministic Layout Math:** Consistent 4px grid rhythm, standardized header (`40px`), sidebar (`240px` / `56px`), and canvas padding (`10px`–`12px`).
3. **Clean CSS Architecture:** Complete removal of toxic global overrides in favor of composable utility classes and design tokens.
4. **Theme Preservation:** Full support for both **Obsidian** (default deep slate/navy) and **Classic** (neutral slate/zinc) visual themes.
5. **Accessibility Compliance:** Rigorous WCAG 2.1 AA compliance with high-contrast text ratios (≥4.5:1), visible focus rings, and full keyboard navigability.

---

## 2. Design Tokens Specification

All tokens are defined at the root in `frontend/src/app/globals.css` and are exposed as CSS custom properties:

### 2.1 Typography Scale
Designed for high legibility on 1080p, 1440p, and high-DPI displays:

```css
:root {
  --vcds-font-2xs: 0.625rem;  /* 10px - Micro badges, timestamp details */
  --vcds-font-xs:  0.6875rem; /* 11px - Table data cells, secondary metadata */
  --vcds-font-sm:  0.75rem;   /* 12px - Body text, standard labels, buttons */
  --vcds-font-base:0.8125rem; /* 13px - Root canvas base, card headers */
  --vcds-font-md:  0.875rem;  /* 14px - Section headings, major KPI values */
  --vcds-font-lg:  1.0rem;    /* 16px - Page titles, modal headers */
  --vcds-font-xl:  1.125rem;  /* 18px - Hero metrics */
}
```

### 2.2 Spacing & Padding Rhythm
Strict 4px/8px modular rhythm eliminating arbitrary padding (`p-7`, `p-9`):

```css
:root {
  --vcds-space-1:   0.25rem;  /* 4px  - Icon gaps, micro tags */
  --vcds-space-1-5: 0.375rem; /* 6px  - Button internal vertical padding */
  --vcds-space-2:   0.5rem;   /* 8px  - Compact card padding, toolbar gaps */
  --vcds-space-2-5: 0.625rem; /* 10px - Root shell padding, input horizontal */
  --vcds-space-3:   0.75rem;  /* 12px - Standard card padding, grid gaps */
  --vcds-space-4:   1.0rem;   /* 16px - Section divider spacing */
  --vcds-space-5:   1.25rem;  /* 20px - Page container maximum padding */
}
```

### 2.3 Surface & Elevation Palette
A 4-tier dark surface hierarchy providing visual depth without distracting drop shadows:

| Surface Level | CSS Variable | Hex / RGBA Value | Usage |
| :--- | :--- | :--- | :--- |
| **0. Void / Canvas** | `--vcds-bg-canvas` | `#030712` (gray-950) | Root application background |
| **1. Sunken Base** | `--vcds-bg-sunken` | `#020617` (slate-950) | Terminal logs, table backgrounds, code blocks |
| **2. Card / Surface** | `--vcds-bg-card` | `#0b0f19` (slate-900/90) | Operational cards, workflow sections |
| **3. Elevated Panel**| `--vcds-bg-elevated`| `#111827` (gray-900/95) | Modals, dropdowns, sticky action columns |

### 2.4 Border & Stroke Tokens
- `--vcds-border-subtle`: `rgba(255, 255, 255, 0.06)` (internal dividers)
- `--vcds-border-default`: `rgba(255, 255, 255, 0.10)` (standard card borders)
- `--vcds-border-strong`: `rgba(255, 255, 255, 0.16)` (active inputs, focus boundaries)
- `--vcds-border-accent`: `rgba(6, 182, 212, 0.40)` (cyan active state highlight)

---

## 3. Global CSS Architecture Remediation

### 3.1 Elimination of Toxic Global Overrides
In the legacy codebase, developers attempted to force compact styling by adding brute-force CSS overrides at the bottom of `globals.css`:
```css
/* LEGACY TOXIC OVERRIDES - REMOVED IN VCDS 1.0 */
div[class*="rounded-xl"] { padding: 0.75rem !important; }
div[class*="gap-6"] { gap: 0.75rem !important; }
h1 { font-size: 1.125rem !important; }
```
**Impact of Legacy Overrides:** These rules broke third-party libraries, broke nested layout cards, forced irregular padding on modals, and resulted in chaotic visual regressions.

**VCDS 1.0 Resolution:** All `!important` global overrides were completely excised. In their place, standardized semantic utility classes were created:
- `.vcds-card`: High-density card container with standardized `p-3`, subtle borders, and gentle hover lighting.
- `.vcds-panel`: Structural container with `p-2.5 sm:p-3` for multi-stage workflows.
- `.vcds-sunken`: Sunken dark well for logs, JSON trees, and code snippets.
- `.vcds-sticky-action-col`: High-z-index pinned table column with frosted backdrop.

### 3.2 Floating Island Gaps Elimination
- **Sidebar Shell:** Removed outer floating margins (`p-3`) on `.theme-sidebar-shell`. The sidebar now docks seamlessly against the left edge of the viewport.
- **Top Navigation Bar:** Removed floating margin pills from `.theme-glass-header`. Docked flush with the top and right edges with an exact height of `40px` (`h-10`).
- **Main Canvas:** Replaced unbounded outer padding with consistent, responsive padding `p-2.5 sm:p-3 lg:p-3.5`.

---

## 4. Reusable Component Primitives (`CompactDesignSystem.tsx`)

The shared component library was enhanced and expanded with production-ready primitives:

### 4.1 `CompactPageHeader`
- **Multi-line Title Support:** Removed forced `truncate` and fixed `max-w-xs` constraints. Rule titles and page descriptions wrap gracefully.
- **Action Strip Responsive Wrapping:** Action buttons wrap into a clean flex row without colliding with the title or overflowing off-screen.
- **Integrated Breadcrumbs & Live Status:** Supports breadcrumbs and dynamic status pills (e.g. `IN PRODUCTION`, `MONITORING ONLY`).

### 4.2 `CompactKPICard`
- **Micro Footprint:** Fixed height footprint (~64px) featuring icon, uppercase micro-label, high-contrast metric value, and optional status delta pill.
- **Variant Theming:** Supports `default`, `cyan`, `emerald`, `amber`, `rose`, and `purple` accent borders.

### 4.3 `CompactRuleScopeBar`
- **High-Density SIEM Rule Scoping:** Combines rule count statistics, a searchable dropdown `<select>`, and quick shortcut pills in a compact 38px horizontal strip.
- **Safety Isolator:** Strict canonical rule scoping preventing incident cross-contamination.

### 4.4 `CompactFilterToolbar`
- **Dense Control Ribbon:** Integrates instant search inputs, severity dropdowns, date range pickers, and view toggles within an ultra-compact 32px height container.

### 4.5 `CompactBadge` & `StatusBadge`
- **Sub-18px Heights:** Micro badges styled with `px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase`.
- **High Contrast:** All badge text meets WCAG 2.1 AA 4.5:1 minimum contrast.

---

## 5. Theme Support Verification

VCDS 1.0 was validated across both platform themes:

| Theme | Canvas Background | Card Background | Accent Primary | Accent Glow |
| :--- | :--- | :--- | :--- | :--- |
| **Obsidian (Default)** | `#030712` | `#0b0f19` | Cyan (`#06b6d4`) | Cyan subtle ring |
| **Classic** | `#090d16` | `#111827` | Sky/Blue (`#0284c7`) | Indigo/Blue ring |

Theme switching operates instantaneously via the root `data-theme` attribute with zero CSS layout shifts or component repaints.
