# 02 — Semantic Icon Mapping & Design Specification

**Date:** 2026-11-18  
**Design System:** Verdictum Compact Design System (VCDS 1.0) + Obsidian Glass / Classic Slate Dual Theme

---

## 1. Canonical 14-Page Semantic Icon Mapping

All 14 recommended Lucide icons were verified directly against the installed `lucide-react@1.69.0` package (`dist/lucide-react.d.ts` and `dist/esm/lucide-react.mjs`). **Zero deviations were required.**

| # | Category | Sidebar Page | Route | Previous Icon | New Lucide Icon | React Export | Semantic Color | RGB Triplet |
|---|---|---|---|---|---|---|---|---|
| 1 | SOC OPERATIONS | Agent Mission Control | `/agent-mission-control` | `LayoutDashboard` | `layout-dashboard` | `LayoutDashboard` | `#38BDF8` | `56, 189, 248` |
| 2 | SOC OPERATIONS | AI Triage Workbench | `/ai-triage-workbench` | `AlertTriangle` | `shield-alert` | `ShieldAlert`\* | `#FB923C` | `251, 146, 60` |
| 3 | SOC OPERATIONS | Telemetry Hub | `/telemetry-hub` | `UploadCloud` | `radio-tower` | `RadioTower` | `#22D3EE` | `34, 211, 238` |
| 4 | SOC OPERATIONS | Human Review Queue | `/human-review-queue` | `UserCheck` | `user-round-check` | `UserRoundCheck` | `#4ADE80` | `74, 222, 128` |
| 5 | SOC OPERATIONS | Verdictum Sentinel | `/soc-chatbot` | `MessageSquareCode` | `bot` | `Bot` | `#A78BFA` | `167, 139, 250` |
| 6 | AGENT INTELLIGENCE | Agent Intelligence Studio | `/agent-intelligence-studio` | `Cpu` | `brain-circuit` | `BrainCircuit` | `#C084FC` | `192, 132, 252` |
| 7 | AGENT INTELLIGENCE | Detection Intelligence | `/detection-intelligence` | `FileCode2` | `radar` | `Radar` | `#FBBF24` | `251, 191, 36` |
| 8 | AGENT INTELLIGENCE | Agent Memory | `/agent-memory` | `Brain` | `database` | `Database` | `#818CF8` | `129, 140, 248` |
| 9 | VALIDATION & TRUST | Agent Simulation Lab | `/agent-simulation-lab` | `FlaskConical` | `flask-conical` | `FlaskConical` | `#FB923C` | `251, 146, 60` |
| 10 | VALIDATION & TRUST | Verdict Intelligence | `/verdict-intelligence` | `BarChart3` | `chart-no-axes-combined` | `ChartNoAxesCombined` | `#2DD4BF` | `45, 212, 191` |
| 11 | PLATFORM CONTROL | Inference Control | `/inference-control` | `Server` | `server-cog` | `ServerCog` | `#60A5FA` | `96, 165, 250` |
| 12 | PLATFORM CONTROL | Agent Configuration | `/agent-configuration` | `Settings` | `sliders-horizontal` | `SlidersHorizontal` | `#CBD5E1` | `203, 213, 225` |
| 13 | PLATFORM CONTROL | Governance & Access | `/governance-access` | `ShieldCheck` | `shield-check` | `ShieldCheck` | `#4ADE80` | `74, 222, 128` |
| 14 | PLATFORM CONTROL | Verdictum AI Admin Guide | `/admin-guide` | `BookOpenCheck` | `book-open-text` | `BookOpenText` | `#FBBF24` | `251, 191, 36` |

*\*Note:* In `lucide-react@1.69.0`, `ShieldAlert` is an official exported alias for `ShieldExclamationPoint` (confirmed in both `.d.ts` and `.mjs`).

---

## 2. Centralized Architecture

To eliminate duplicated icon/color tables while keeping pure metadata importable in Node unit tests (`--experimental-strip-types`), the architecture splits cleanly into two modules:

1. **`frontend/src/config/navigationIcons.ts`** (Pure TypeScript, zero React imports):
   - `NAVIGATION_ICON_METADATA`: Canonical record of all 14 pages (`id`, `title`, `href`, `groupTitle`, `iconName`, `componentName`, `color`, `rgb`, `tintOpacity`, `hoverTintOpacity`, `activeTintOpacity`).
   - `NAVIGATION_PAGE_IDS` & `NAVIGATION_GROUP_ORDER`: Ordered readonly arrays preserving exact category and page order.
   - `ROUTE_TO_PAGE_ID`: Route lookup table including `/` -> `agent-mission-control`.
   - `resolveNavigationPageId()`, `getNavigationIconMetadata()`, `getSemanticIconCssVars()`: Safe resolvers with neutral `#CBD5E1` fallback.
2. **`frontend/src/components/navigation/NavigationIcon.tsx`** (Reusable Client Component):
   - `NAVIGATION_ICON_COMPONENTS`: Single `Record<NavigationPageId, LucideIcon>` map binding all 14 Lucide icons.
   - Size profiles:
     - `expanded`: `18px` SVG inside `26px × 26px` (`rounded-[7px]`) semantic-tinted badge.
     - `collapsed`: `20px` SVG inside `32px × 32px` (`rounded-lg`) centered badge.
     - `compact`: `16px` SVG inside `24px × 24px` (`rounded-md`) badge for Admin Guide sidebar & cards.
     - `xs`: `14px` SVG for inline chips and workspace shortcuts.
   - Stroke weight: `1.9` for crisp dark-mode legibility without visual heaviness.

---

## 3. Visual & Interaction Design Tokens

| State | Icon Color | Icon Container Fill | Icon Container Border | Row Surface |
|---|---|---|---|---|
| **Inactive** | Semantic Hex (`--nav-icon-color`) | `10%` opacity (`rgba(rgb, 0.10)`) | `16%` opacity (`rgba(rgb, 0.16)`) | Transparent (`text-slate-300/90`) |
| **Hover / Focus** | Semantic Hex (`1.04` subtle scale) | `16%` opacity (`rgba(rgb, 0.16)`) | `36%` opacity (`rgba(rgb, 0.36)`) | `bg-slate-900/70` (`text-slate-100`) |
| **Active (Obsidian)** | Semantic Hex retained | `18%` opacity (`rgba(rgb, 0.18)`) | `36%` opacity (`rgba(rgb, 0.36)`) | `.theme-nav-active` warm amber/gold/subtle purple gradient + `3px` amber left indicator bar (`::before`) |
| **Active (Classic)** | Semantic Hex retained | `18%` opacity (`rgba(rgb, 0.18)`) | `36%` opacity (`rgba(rgb, 0.36)`) | `.theme-nav-active` cyan slate surface + `3px` cyan left indicator bar (`::before`) |

---

## 4. WCAG 2.1 Contrast Verification (Mathematically Computed)

All 14 semantic colors were evaluated using the W3C WCAG 2.1 relative luminance formula against:
- Obsidian sidebar dark surface (`#121015`)
- Composited `10%` semantic tint container over Obsidian (`#121015`)
- Classic Slate sidebar dark surface (`#020617`)

| Page | Color | Contrast vs Obsidian (`#121015`) | Contrast vs 10% Tinted Badge | Contrast vs Classic (`#020617`) | WCAG AA Non-Text (`>= 3.0:1`) |
|---|---|---|---|---|---|
| Agent Mission Control | `#38BDF8` | `8.83:1` | `7.61:1` | `9.42:1` | PASS |
| AI Triage Workbench | `#FB923C` | `8.35:1` | `7.23:1` | `8.91:1` | PASS |
| Telemetry Hub | `#22D3EE` | `10.46:1` | `8.82:1` | `11.16:1` | PASS |
| Human Review Queue | `#4ADE80` | `10.85:1` | `9.10:1` | `11.58:1` | PASS |
| Verdictum Sentinel | `#A78BFA` | `6.95:1` | `6.09:1` | `7.41:1` | PASS |
| Agent Intelligence Studio | `#C084FC` | `7.16:1` | `6.24:1` | `7.63:1` | PASS |
| Detection Intelligence | `#FBBF24` | `11.33:1` | `9.42:1` | `12.08:1` | PASS |
| Agent Memory | `#818CF8` | `6.34:1` | `5.61:1` | `6.76:1` | PASS |
| Agent Simulation Lab | `#FB923C` | `8.35:1` | `7.23:1` | `8.91:1` | PASS |
| Verdict Intelligence | `#2DD4BF` | `10.16:1` | `8.60:1` | `10.84:1` | PASS |
| Inference Control | `#60A5FA` | `7.44:1` | `6.47:1` | `7.93:1` | PASS |
| Agent Configuration | `#CBD5E1` | `12.73:1` | `10.40:1` | `13.59:1` | PASS |
| Governance & Access | `#4ADE80` | `10.85:1` | `9.10:1` | `11.58:1` | PASS |
| Verdictum AI Admin Guide | `#FBBF24` | `11.33:1` | `9.42:1` | `12.08:1` | PASS |

Every icon exceeds `5.6:1` even on top of its tinted container (well above both `3.0:1` non-text UI contrast and `4.5:1` normal text contrast).

---

## 5. Verification Classification

- **Verified:** Lucide icon export existence in `lucide-react@1.69.0`, exact RGB-to-hex fidelity, WCAG 2.1 contrast math for all 14 items across Obsidian, tinted badge, and Classic surfaces.
- **Unexecuted:** Perceptual visual tuning on a live rendered canvas (blocked by missing local Node.js runtime).
- **Remaining Issues:** None at the design specification level.
