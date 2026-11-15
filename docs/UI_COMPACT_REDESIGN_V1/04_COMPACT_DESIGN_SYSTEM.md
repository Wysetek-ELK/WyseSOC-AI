# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 04. Verdictum Compact Design System v1.0

**Document Version:** 1.0.0  
**Phase:** Phase 3 — Design System Blueprint  
**System Name:** **Verdictum Compact Design System v1.0 (VCDS 1.0)**  
**Target Architecture:** Next.js 16 + React 19 + Tailwind CSS v4  

---

## 1. Visual Direction & Design Philosophy

The Verdictum Compact Design System v1.0 transforms the interface into a **premium, cozy, high-density, professional Agentic SOC Intelligence platform**.

### Core Tenets:
1. **Simple by Default — Advanced on Demand:** Deliver immediate operational clarity for Tier 1 SOC analysts while keeping deep technical telemetry (SHA-256 digests, JSON contracts, tokens) accessible via progressive disclosure.
2. **True Compactness Without Mutilation:** Achieve compact visual density by eliminating redundant headers, collapsing whitespace, and standardizing component heights—**never** by clipping critical titles, hiding safety gates, or shrinking typography below legibility limits.
3. **Enterprise SOC Dark Identity:** Refined obsidian surfaces (`#070609` to `#16131b`) with Verdictum warm amber (`#f97316`) and luminous gold (`#f59e0b`) accents, paired with crisp semantic indicators (Emerald, Rose, Sky, Amber).
4. **Predictable Layout Grids:** Strict 12-column page layouts and fixed-height table rows preventing visual jumping and ragged wrapping.

---

## 2. Design Tokens & CSS Custom Properties

### 2.1 Color Palette & Semantic Status Colors

```css
:root,
html[data-theme="obsidian"] {
  /* Canvas & Base Surfaces */
  --vcds-bg-canvas: #070609;
  --vcds-bg-surface-0: #0d0b10;   /* Deepest card background */
  --vcds-bg-surface-1: #141118;   /* Primary card / panel */
  --vcds-bg-surface-2: #1b1721;   /* Elevated card / hover state */
  --vcds-bg-surface-3: #26212d;   /* Modal / Popover / Dropdown */
  --vcds-bg-sunken: #09070c;      /* Inset text / code containers */

  /* Borders & Dividers */
  --vcds-border-subtle: rgba(255, 235, 215, 0.07);
  --vcds-border-medium: rgba(255, 235, 215, 0.12);
  --vcds-border-strong: rgba(255, 235, 215, 0.20);
  --vcds-border-accent: rgba(249, 115, 22, 0.50);

  /* Primary Brand Accents (Verdictum Warm Amber & Gold) */
  --vcds-accent-primary: #f97316;       /* Warm Orange 500 */
  --vcds-accent-primary-hover: #fb923c; /* Warm Orange 400 */
  --vcds-accent-primary-active: #ea580c;/* Warm Orange 600 */
  --vcds-accent-secondary: #f59e0b;     /* Luminous Gold 500 */
  --vcds-accent-secondary-hover: #fbbf24;

  /* Semantic SOC Status Colors */
  /* TRUE POSITIVE / MALICIOUS / BLOCKED */
  --vcds-status-danger-bg: rgba(76, 15, 20, 0.60);
  --vcds-status-danger-border: rgba(225, 29, 72, 0.65);
  --vcds-status-danger-text: #fda4af;
  --vcds-status-danger-dot: #f43f5e;

  /* FALSE POSITIVE / BENIGN / APPROVED / COMPLETED */
  --vcds-status-success-bg: rgba(6, 44, 30, 0.60);
  --vcds-status-success-border: rgba(16, 185, 129, 0.65);
  --vcds-status-success-text: #6ee7b7;
  --vcds-status-success-dot: #10b981;

  /* SUSPICIOUS / REQUIRES ATTENTION / LEARNING / PENDING */
  --vcds-status-warning-bg: rgba(56, 30, 6, 0.60);
  --vcds-status-warning-border: rgba(245, 158, 11, 0.65);
  --vcds-status-warning-text: #fde68a;
  --vcds-status-warning-dot: #f59e0b;

  /* INFORMATIONAL / VALIDATED / TEMPLATE / ONLINE */
  --vcds-status-info-bg: rgba(12, 35, 60, 0.60);
  --vcds-status-info-border: rgba(14, 165, 233, 0.65);
  --vcds-status-info-text: #7dd3fc;
  --vcds-status-info-dot: #0ea5e9;

  /* NEUTRAL / IDLE / UNLABELED / ARCHIVED */
  --vcds-status-neutral-bg: rgba(25, 22, 28, 0.60);
  --vcds-status-neutral-border: rgba(100, 90, 105, 0.50);
  --vcds-status-neutral-text: #cbd5e1;
  --vcds-status-neutral-dot: #64748b;

  /* Text & Contrast */
  --vcds-text-primary: #f8fafc;     /* High contrast title text */
  --vcds-text-secondary: #cbd5e1;   /* Standard body & label text */
  --vcds-text-muted: #94a3b8;       /* Secondary description text */
  --vcds-text-disabled: #475569;    /* Disabled / placeholder */

  /* Shadows & Glows */
  --vcds-shadow-card: 0 4px 16px -2px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  --vcds-shadow-glow-primary: 0 0 18px -2px rgba(249, 115, 22, 0.45);
  --vcds-shadow-popover: 0 12px 32px -4px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.10);
}
```

---

## 3. Typographical Scale & Hierarchy

To resolve the flat typographical hierarchy caused by root `text-xs` forcing, VCDS 1.0 defines an explicit **5-Tier Typographical Scale**:

| Level | Size (rem / px) | Weight | Line Height | Tracking | Recommended Usage |
|---|---|---|---|---|---|
| **Display / H1** | `1.125rem` (18px) | 700 (Bold) | `1.35` | `-0.015em` | Page Titles (e.g. Rule Name, Dashboard Header) |
| **Section Title / H2**| `0.875rem` (14px) | 600 (Semibold) | `1.4` | `-0.01em` | Card Headers, Panel Group Titles |
| **Subheader / H3** | `0.75rem` (12px) | 700 (Bold) | `1.4` | `+0.05em` | Uppercase Section Labels (`text-[11px] uppercase tracking-wider`) |
| **Body Primary** | `0.8125rem` (13px)| 500 (Medium) | `1.45` | `normal` | Incident descriptions, explanations, checklist text |
| **Body Compact** | `0.75rem` (12px) | 400 (Regular) | `1.4` | `normal` | Standard table cell text, metadata lines |
| **Technical Mono** | `0.6875rem` (11px)| 600 (Semibold) | `1.3` | `+0.02em` | IP addresses, Event Types, Rule IDs, SHAs, timestamps |

---

## 4. Spacing Scale & Layout Grid

VCDS 1.0 employs an uncompromising **4px Base Rhythm**:

| Token Name | Rem Value | Pixel Value | Standard Application |
|---|---|---|---|
| `--vcds-space-1` | `0.25rem` | 4px | Icon-to-text gap, badge internal padding |
| `--vcds-space-1-5`| `0.375rem`| 6px | Tight button horizontal gap, tag margins |
| `--vcds-space-2` | `0.5rem` | 8px | Compact card internal padding, toolbar element gap |
| `--vcds-space-2-5`| `0.625rem`| 10px | Standard card vertical padding |
| `--vcds-space-3` | `0.75rem` | 12px | Standard card padding (`p-3`), row spacing (`space-y-3`) |
| `--vcds-space-4` | `1.0rem` | 16px | Major section gutters, page canvas margin |
| `--vcds-space-5` | `1.25rem` | 20px | Hero card padding on high-res monitors |

### Standard Container Metrics:
- **Card Padding:**
  - Compact Cards (KPIs, Mini-Widgets): `0.625rem` (10px).
  - Standard Cards (Checklists, Data Panels): `0.75rem` (12px).
- **Card Corner Radius:** `0.5rem` (8px / `rounded-lg`). *Discontinue 12px–16px oversized bubble corners.*
- **Outer Page Canvas Padding:** `0.75rem` (12px / `p-3`).

---

## 5. Standard Component Dimension Specifications

### 5.1 Buttons & Interactive Controls

| Variant | Height | Padding (X / Y) | Font Size | Border Radius | Styling & Hover |
|---|---|---|---|---|---|
| **Primary Action** | 30px (`h-7.5`) | `12px` / `0` | `12px` (Bold) | `6px` (`rounded-md`) | Amber gradient, white text, subtle glow |
| **Secondary Action** | 30px (`h-7.5`) | `10px` / `0` | `12px` (Medium)| `6px` (`rounded-md`) | Surface-2, subtle border, hover border-accent |
| **Ghost / Icon-Only**| 28px (`h-7`) | `6px` / `0` | `12px` | `6px` (`rounded-md`) | Transparent, hover surface-2 |
| **Compact Table Action**| 24px (`h-6`) | `8px` / `0` | `11px` (Semibold)| `4px` (`rounded`) | Surface-1, colored border |

### 5.2 Form Inputs & Dropdowns

| Control Type | Height | Padding (X) | Font Size / Family | Border & Focus States |
|---|---|---|---|---|
| **Search Input** | 32px (`h-8`) | `32px left (icon), 12px right` | `12px` / Sans | Border subtle, focus border-accent, ring-1 |
| **Select Dropdown** | 30px (`h-7.5`)| `8px left, 24px right` | `11.5px` / Sans | Surface-0, custom chevron, truncate |
| **Date / Fixture Tag** | 22px (`h-5.5`)| `6px left, 6px right` | `10.5px` / Mono | Sunken bg, border subtle |

### 5.3 Data Tables

| Element | Height / Padding | Font Size | Text Alignment | Special Behavior |
|---|---|---|---|---|
| **Table Header (`<th>`)** | 32px height, `px-2.5 py-1.5` | `10.5px` (Bold, Mono, Uppercase) | Left (Right for Action) | Sticky top, surface-0 background |
| **Standard Row (`<tr>`)** | 36px fixed height (`h-9`) | `px-2.5 py-1.5` | `12px` (Primary) / `11px` (Mono) | Left | Hover surface-2, cursor-pointer |
| **Action Cell (`<td>`)** | 36px height, `px-2` | `11px` | Right | **Sticky right-0**, z-index 10, shadow-l |

### 5.4 Badges & Status Pills

| Badge Type | Height | Padding | Font | Visual Indicators |
|---|---|---|---|---|
| **Lifecycle Stage Badge** | 20px | `px-2 py-0.5` | `10px` Mono Bold | 6px status dot + text label |
| **Severity Badge** | 18px | `px-1.5 py-0.2` | `9.5px` Sans Bold | Critical: Rose, High: Orange, Med: Amber, Low: Slate |
| **Verdict Pill (TP/FP/Attn)**| 20px | `px-2 py-0.5` | `10.5px` Mono Bold | TP: Red, FP: Emerald, Attn: Amber |
| **Gate Status Badge** | 18px | `px-1.5 py-0.2` | `9.5px` Mono | PASSED (Emerald), FAILED (Rose), PENDING (Slate) |

---

## 6. Shell & Navigation Dimensions

```
┌────────────────────────────────────────────────────────────────────────┐
│ TOP HEADER: Height = 44px (h-11)                                       │
│ [Logo / Breadcrumb]  [Global Search: w-80]  [Blind Toggle] [Theme] [User] │
├───────────────┬────────────────────────────────────────────────────────┤
│ SIDEBAR       │ MAIN CONTENT CANVAS                                    │
│ Expanded:     │ Padding: 12px (p-3)                                    │
│ Width = 240px │ Max Width: 100% fluid                                  │
│ Collapsed:    │ Overflow: overflow-y-auto                              │
│ Width = 56px  │                                                        │
│               │                                                        │
└───────────────┴────────────────────────────────────────────────────────┘
```

---

## 7. Responsive Breakpoint Rules

| Viewport Category | Width Constraint | Layout Adaptations |
|---|---|---|
| **Large SOC Wall / 4K** | `≥ 1920px` | 12-column grid active; 8-col main + 4-col context sidebar; zero dead space |
| **Standard Desktop** | `1440px – 1919px` | Optimal baseline; 8-col / 4-col balance; tables show all 7 primary columns |
| **Compact Laptop** | `1280px – 1366px` | 8-col / 4-col maintained; secondary table columns truncate with tooltips |
| **Tablet / Small Display**| `1024px – 1279px` | Sidebar collapses to 56px automatically; 12-col stacks to single column |
| **Mobile / Small Screen**| `< 1024px` | Hamburger drawer navigation; full-width stacked cards |

---

## 8. Accessibility & Keyboard Standards

1. **Target Tap / Click Sizes:** Every clickable button, link, or row maintains a minimum bounding box of **28px × 28px** with adequate padding.
2. **Keyboard Focus Rings:** Every interactive control implements an explicit, high-contrast focus ring:
   ```css
   focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500 focus-visible:border-amber-400
   ```
3. **Contrast Compliance:** All text tokens exceed **WCAG 2.1 AA** contrast ratios:
   - Primary text (`#f8fafc`) on Surface-1 (`#141118`): **15.8:1** (Passes AAA).
   - Secondary text (`#cbd5e1`) on Surface-1: **11.2:1** (Passes AAA).
   - Muted text (`#94a3b8`) on Surface-1: **6.1:1** (Passes AA).
4. **Reduced Motion:** Fully honors `prefers-reduced-motion: reduce`: all animated pulses, transitions, and SVG workflow edge dashes are immediately neutralized.
