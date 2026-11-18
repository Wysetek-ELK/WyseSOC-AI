# 01 — Current UI Configuration Audit

**Audit Date:** 2026-11-18  
**Scope:** Verdictum AI Frontend (`frontend/`) — Sidebar Navigation, Theme Tokens, Admin Guide Sidebar, Accessibility, and RBAC Visibility  
**Status:** Verified via Direct Codebase Inspection

---

## 1. Frontend Architecture & Installed Libraries

| Component | Verified Value | Source |
|---|---|---|
| Framework | Next.js `16.4.5` (App Router under `frontend/src/app/`) | `frontend/package.json` |
| UI Runtime | React `19.3.0`, React DOM `19.3.0` | `frontend/package.json` |
| Language | TypeScript `^5` (`strict: true`, `@/*` -> `./src/*`) | `frontend/tsconfig.json` |
| Styling System | Tailwind CSS `v4` (`@tailwindcss/postcss ^4.3.3`), `clsx ^2.1.1`, `tailwind-merge ^3.7.0` | `frontend/package.json`, `frontend/src/app/globals.css` |
| Icon Library | `lucide-react` `^1.69.0` (verified installed v`1.69.0`) | `frontend/node_modules/lucide-react/package.json` |
| Test Runner | Node built-in test runner (`node --experimental-strip-types --test`) | `frontend/package.json` |

**Result:** `lucide-react@1.69.0` is already installed and exports all 14 target icons (verified directly in `dist/lucide-react.d.ts` and `dist/esm/lucide-react.mjs`). No new dependencies are required.

---

## 2. Theme Configuration & Design Tokens

Verdictum AI uses a dual-theme design system controlled via `data-theme` on `<html>` (`frontend/src/app/layout.tsx`, `frontend/src/context/AppContext.tsx`, `frontend/src/app/globals.css`):

1. **Default Theme — `obsidian` (`html:not([data-theme="classic"])`):**
   - Background: `#070609`, Foreground: `#faf8fb`.
   - Sidebar shell (`.theme-sidebar-shell`): `--surface-sidebar: linear-gradient(180deg, rgba(24, 20, 26, 0.84) 0%, rgba(12, 10, 14, 0.90) 100%)` with `backdrop-filter: blur(18px) saturate(135%)` and `--border-glass: rgba(255, 240, 224, 0.11)`.
   - Active nav styling (`.theme-nav-active`): warm amber/orange translucent gradient (`rgba(249, 115, 22, 0.24)` -> `rgba(245, 158, 11, 0.12)`), warm amber border (`rgba(251, 146, 60, 0.62)`), and `--shadow-glow-nav`.
   - **Critical Token Remapping Finding:** Obsidian remaps Tailwind v4 `--color-cyan-*` to warm amber/burnt orange (`#f97316`–`#fb923c`) and `--color-sky-*` to luminous gold (`#f59e0b`–`#fbbf24`). Therefore, applying Tailwind classes such as `text-sky-400` or `text-cyan-400` causes icons to render gold/amber rather than true blue/cyan under Obsidian. Semantic multicolor icons must therefore bind explicit hex/RGB custom properties so they retain accurate semantic hues in both Obsidian and Classic themes.
2. **Alternate Theme — `classic` (`html[data-theme="classic"]`):**
   - Background: `#090d16`, Sidebar: `#020617`, Active nav: cyan-tinted surface (`rgba(8, 51, 68, 0.6)`) with `#67e8f9` text.
   - Theme switching persists via `localStorage` key `ai_verdict_theme` and toggles from `Header.tsx`.

---

## 3. Main Sidebar & Navigation Audit (`frontend/src/components/layout/Sidebar.tsx`)

- **Shell Placement:** Rendered inside `Shell.tsx` (`flex h-screen w-full overflow-hidden`) for all routes except `/login`.
- **Dimensions:** Expanded `w-60` (`240px`), Collapsed `w-14` (`56px`), toggled via local React state `collapsed`.
- **Navigation Registry (`NAV_GROUPS`):** 4 categories, 14 items total:
  1. `SOC OPERATIONS`: Agent Mission Control (`/agent-mission-control`), AI Triage Workbench (`/ai-triage-workbench`), Telemetry Hub (`/telemetry-hub`), Human Review Queue (`/human-review-queue`), Verdictum Sentinel (`/soc-chatbot`, `COPILOT` badge).
  2. `AGENT INTELLIGENCE`: Agent Intelligence Studio (`/agent-intelligence-studio`), Detection Intelligence (`/detection-intelligence`), Agent Memory (`/agent-memory`).
  3. `VALIDATION & TRUST`: Agent Simulation Lab (`/agent-simulation-lab`), Verdict Intelligence (`/verdict-intelligence`).
  4. `PLATFORM CONTROL`: Inference Control (`/inference-control`), Agent Configuration (`/agent-configuration`), Governance & Access (`/governance-access`), Verdictum AI Admin Guide (`/admin-guide`).
- **Active Matching Logic:** `isItemActive(href)` matches `/` and `/agent-mission-control` for Mission Control, and `pathname === href || pathname.startsWith(href + "/")` for all other destinations.
- **Footer Widget:** Real-time Inference Health widget (`data-testid="sidebar-inference-widget"`) polling `api.getLlmStatus()` every 15s and listening for `llm-status-change` events.

### Pre-Enhancement Visual & Structural Findings

1. **Monochrome Icon Presentation:** All inactive sidebar icons used `text-slate-400` and all active icons used `text-cyan-300` (warm peach in Obsidian). No semantic color differentiation existed across operational domains.
2. **Undersized Icons:** Sidebar icons rendered at `h-3.5 w-3.5` (`14px`) in both expanded and collapsed modes (below the target `18px` expanded / `20px` collapsed visual hierarchy).
3. **No Semantic Icon Containers:** Icons rendered bare without subtle semantic tint containers (`8–12%` opacity).
4. **Collapsed Mode Alignment:** Collapsed `<Link>` items retained `px-2 py-1` and `gap-2` instead of centered compact icon alignment, and lacked subtle category dividers when group labels hid.
5. **Accessibility Gaps:** Active `<Link>` items lacked `aria-current="page"`, `<nav>` lacked `aria-label`, collapse toggle lacked `aria-expanded`, and sidebar transitions lacked `prefers-reduced-motion` safeguards.

---

## 4. Admin Guide & Shared Navigation Audit

- **Admin Guide Internal Sidebar (`frontend/src/components/admin-guide/AdminGuideInteractiveReader.tsx`):**
  - **Duplicate Icon Mapping Identified:** Defined its own hardcoded `ICON_MAP` (lines 47–62) duplicating all 14 sidebar Lucide icons (`LayoutDashboard`, `AlertTriangle`, `UploadCloud`, `UserCheck`, `MessageSquareCode`, `Cpu`, `FileCode2`, `Brain`, `FlaskConical`, `BarChart3`, `Server`, `Settings`, `ShieldCheck`, `BookOpenCheck`) and `GROUP_ORDER`.
  - **Monochrome Hardcoding:** Every Admin Guide sidebar item and search result rendered `<PageIcon className="w-3.5 h-3.5 shrink-0 text-sky-400" />`, which appeared uniform gold under Obsidian.
  - **Page References Without Icons:** Related page buttons (`currentPage.relatedPages`), page detail headers, and `PLATFORM_PAGE_LINKS` cards/chips across `GlossaryTroubleshootingSection.tsx`, `GuidedTourSection.tsx`, and `app/admin-guide/page.tsx` did not display matching semantic page icons.
- **Existing Test Contract Identified:** `frontend/tests/admin-guide.test.mjs` reads `Sidebar.tsx` directly and asserts regex matches for `PLATFORM CONTROL`, `Verdictum AI Admin Guide`, and `/admin-guide`. Any refactor must preserve those strings inside `Sidebar.tsx`.

---

## 5. RBAC, Responsive Behavior & Tooltips Audit

- **RBAC Visibility:** Audited across `Sidebar.tsx`, `AppContext.tsx`, and all route pages. `Sidebar.tsx` displays all 14 navigation links uniformly across roles (`Administrator`, `SOC Analyst`, `Read-Only Viewer`); role-based access enforcement is performed at the page component level (e.g., `agent-configuration`, `governance-access`, `agent-intelligence-studio`, `PilotControlAndDashboard`) and backend API layer. No RBAC rules will be altered.
- **Tooltips:** Collapsed sidebar links expose native `title={collapsed ? item.title : undefined}` tooltips; Brand header and Inference widget also expose descriptive `title` attributes.
- **Responsive Layout:** Main shell uses `flex h-screen w-full overflow-hidden` with `min-w-0` on the main column. Admin Guide uses `flex-col lg:flex-row` with `w-full lg:w-80` internal sidebar.

---

## 6. Verification Classification

- **Verified Checks:** Full source audit of `package.json`, `tsconfig.json`, `next.config.ts`, `layout.tsx`, `globals.css`, `AppContext.tsx`, `Shell.tsx`, `Sidebar.tsx`, `Header.tsx`, `BrandLogo.tsx`, `AdminGuideInteractiveReader.tsx`, `pagesGuideData.ts`, `glossaryAndTroubleshootingData.ts`, `GlossaryTroubleshootingSection.tsx`, `GuidedTourSection.tsx`, `admin-guide/page.tsx`, existing test files, and installed `lucide-react@1.69.0` declarations/ESM exports.
- **Unexecuted Checks:** Live runtime inspection of the pre-change UI (no local Node.js runtime or running dev server on this host).
- **Remaining Issues Identified for Implementation:** Duplicate icon registries (`Sidebar.tsx` vs `AdminGuideInteractiveReader.tsx`), monochrome icon styling, undersized `14px` sidebar icons, collapsed alignment/dividers, and missing `aria-current` / reduced-motion rules.
