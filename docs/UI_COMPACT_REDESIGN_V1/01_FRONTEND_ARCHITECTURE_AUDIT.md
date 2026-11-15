# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 01. Frontend Architecture Audit

**Document Version:** 1.0.0  
**Phase:** Phase 1 — Comprehensive Architecture Audit  
**Auditor:** Principal Enterprise UI/UX Architect & SOC Platform Systems Specialist  
**Target Repository:** `c:\Users\amit\OneDrive\Documents\SOC-AI-Agent`  
**Frontend Root:** `frontend/`  
**Build & Test Verification Date:** 2026-11-15  

---

## 1. Executive Summary & Tech Stack Discovery

A forensic examination of the Verdictum AI frontend codebase was conducted to establish the exact architecture, dependencies, styling mechanisms, layout patterns, and routing topologies without unverified assumptions.

### Discovered Technology Stack

| Technology Layer | Discovered Dependency / Version | Configuration File | Source Evidence |
|---|---|---|---|
| **Core Framework** | **Next.js 16.4.5** (App Router, Turbopack enabled) | `frontend/package.json`<br>`frontend/next.config.ts` | `"next": "16.4.5"` |
| **Runtime Library** | **React 19.3.0** & **React-DOM 19.3.0** | `frontend/package.json` | `"react": "19.3.0"` |
| **CSS & Design Engine**| **Tailwind CSS v4** (`@tailwindcss/postcss` 4.3.3) | `frontend/src/app/globals.css`<br>`frontend/postcss.config.mjs` | `@import "tailwindcss";` |
| **Iconography** | **Lucide React 1.69.0** | `frontend/package.json` | `"lucide-react": "^1.69.0"` |
| **Class Merging Utilities** | **clsx 2.1.1** & **tailwind-merge 3.7.0** | `frontend/package.json` | Utility composition |
| **Language & Engine** | **TypeScript 5.x** | `frontend/tsconfig.json` | Strict mode enabled |
| **Test Runner** | Node.js Built-in Test Runner (`node --test`) | `frontend/package.json` | 4 test suites present |

### Build & Test Health Baseline

Prior to planning any modifications, the existing production build and automated test suites were verified:
- **Build Status:** `next build` executed with exit code 0; 32 route endpoints compiled cleanly (both static and server-rendered dynamic endpoints).
- **Test Baseline:** `npm test` executed with 100% pass rate:
  - `admin-guide.test.mjs`: 8/8 tests passed.
  - `phase3-compact-ui.test.mjs`: 7/7 tests passed.
  - `production-readiness.test.mjs`: 5/5 tests passed.
  - `quality-export.test.mjs`: 8/8 tests passed (when run inside `frontend` working directory).

---

## 2. Application Shell & Layout Architecture

The application layout is structured as a client-side single-page shell orchestrated across three primary layers:

```
[ RootLayout (src/app/layout.tsx) ]
  └── [ AppProvider (src/context/AppContext.tsx) ]
        └── [ Shell (src/components/layout/Shell.tsx) ]
              ├── <Sidebar> (src/components/layout/Sidebar.tsx) [w-56 expanded / w-12 collapsed]
              └── <div className="flex-1 flex-col min-w-0">
                    ├── <Header> (src/components/layout/Header.tsx) [h-10 / 40px]
                    └── <main className="theme-main-canvas p-2 sm:p-2.5 overflow-y-auto">
                          {children} [Page Component]
```

### 2.1 Global Context (`src/context/AppContext.tsx`)
- **State Managed:**
  - `user`: Authenticated operator (`User | null`, username, role: `Administrator` | `SOC Analyst` | `Read-Only Viewer`).
  - `blindReviewMode`: Double-blind triage mode toggle (persisted in `localStorage.getItem("ai_verdict_blind_review")`). When enabled, historical SIEM resolution verdicts and AI explanations are masked to eliminate analyst bias.
  - `theme`: Dual-theme mode (`obsidian` default vs `classic` slate).
- **Session Sync:** Checks session state via `api.getMe()`, stores JWT bearer token in `localStorage`.

### 2.2 Shell Wrapper (`src/components/layout/Shell.tsx`)
- **Structure:**
  ```tsx
  <div className="relative flex h-screen w-full overflow-hidden theme-body font-sans text-xs">
    <div aria-hidden="true" className="theme-ambient-backdrop pointer-events-none fixed inset-0 z-0" />
    <Sidebar />
    <div className="relative z-10 flex flex-1 flex-col overflow-hidden min-w-0">
      <Header />
      <main className="flex-1 overflow-y-auto theme-main-canvas p-2 sm:p-2.5">
        {children}
      </main>
    </div>
  </div>
  ```
- **Architectural Observations:**
  1. The shell sets `font-sans text-xs` (12px) at the root `div`. Every child component inherits 12px unless explicitly overridden, which suppresses standard typographical scale.
  2. The main canvas padding is locked to `p-2 sm:p-2.5` (8px to 10px), leaving little breathing room between outer page margins and edge boundaries.
  3. `overflow-hidden` on parent flex columns paired with `overflow-y-auto` on `<main>` ensures full-screen viewport pinning without window scrolling, but child containers frequently suffer from nested horizontal scroll traps.

### 2.3 Navigation Sidebar (`src/components/layout/Sidebar.tsx`)
- **Widths:** `w-56` (224px / 14rem) expanded; `w-12` (48px / 3rem) collapsed.
- **Header:** Verdictum Brand Logo with dual-line typography (`Verdictum AI`, `Agentic SOC Intelligence`).
- **Grouping:** 4 categorized navigation sections with 14 canonical items:
  1. **SOC OPERATIONS:** Agent Mission Control, AI Triage Workbench, Telemetry Hub, Human Review Queue, Verdictum Sentinel (`COPILOT`).
  2. **AGENT INTELLIGENCE:** Agent Intelligence Studio, Detection Intelligence, Agent Memory.
  3. **VALIDATION & TRUST:** Agent Simulation Lab, Verdict Intelligence.
  4. **PLATFORM CONTROL:** Inference Control, Agent Configuration, Governance & Access, Verdictum AI Admin Guide.
- **Inference Telemetry Footer:** Real-time dual-server health widget displaying Server 2 status (`ONLINE` / `OFFLINE` / `HTTP_MOCK`), active architecture, and loaded model name (`Qwen 2.5 7B`). Polls every 15s and listens to `window` event `llm-status-change`.

### 2.4 Header Bar (`src/components/layout/Header.tsx`)
- **Dimensions:** Fixed height `h-10` (40px).
- **Controls:**
  1. Global search input field (`w-72 sm:w-80 md:w-96`, submits to `/ai-triage-workbench?search=...`).
  2. Blind Review toggle button with warning glow.
  3. Theme toggle switch (`Obsidian` vs `Classic`).
  4. Operator profile badge showing username and role pill (`Administrator`, `SOC Analyst`, `Read-Only Viewer`).
  5. Sign out button.

---

## 3. Design Tokens & Styling Mechanism

### 3.1 Dual-Theme System (`src/app/globals.css`)

Verdictum AI implements two themes using CSS custom properties on `<html>`:

1. **Obsidian Glass (Default Theme — `html:not([data-theme="classic"])`):**
   - Background: `#070609` (deep obsidian).
   - Surfaces: Translucent glass layers `rgba(27, 22, 29, 0.74)` with `backdrop-filter: blur(18px) saturate(135%)`.
   - Accent Primary: Warm Amber / Burnt Orange (`--color-cyan-500: #f97316`, `--color-cyan-600: #ea580c`).
   - Accent Secondary: Luminous Gold (`--color-sky-500: #f59e0b`, `--color-sky-400: #fbbf24`).
   - Shadows: Ambient glow shadows (`--shadow-glow-cta: 0 0 22px -2px rgba(249, 115, 22, 0.55)`).
   - Canvas Decor: Radial background bokeh with a 44px technical grid.

2. **Classic Slate (`html[data-theme="classic"]`):**
   - Background: `#090d16` (deep navy slate).
   - Surfaces: Solid slate surfaces `#020617` and `rgba(15, 23, 42, 0.45)`.
   - Accents: Electric Cyan (`#06b6d4`, `#0891b2`) and Sky Blue.
   - Glass blur: Disabled (`none`).

### 3.2 Critical Styling Defect: Brute-Force Descendant Overrides

Lines 171–244 of `src/app/globals.css` contain a severe architectural flaw:

```css
/* Global High-Density Compact Spacing across Workspace Pages */
.theme-main-canvas .p-6 { padding: 0.75rem; }
.theme-main-canvas .p-5 { padding: 0.625rem; }
.theme-main-canvas .p-4, .theme-main-canvas .sm\:p-4 { padding: 0.5625rem; }
.theme-main-canvas .p-3\.5, .theme-main-canvas .sm\:p-3\.5 { padding: 0.5rem; }
.theme-main-canvas .p-3, .theme-main-canvas .sm\:p-3 { padding: 0.4375rem; }
.theme-main-canvas .px-6 { padding-inline: 0.75rem; }
.theme-main-canvas .py-6 { padding-block: 0.625rem; }
.theme-main-canvas .space-y-6 > :not(:last-child) { margin-block-end: 0.625rem; }
.theme-main-canvas .space-y-4 > :not(:last-child) { margin-block-end: 0.5rem; }
.theme-main-canvas .gap-6 { gap: 0.625rem; }
.theme-main-canvas .gap-4 { gap: 0.5rem; }
.theme-main-canvas table th, .theme-main-canvas table td {
  padding-top: 0.35rem;
  padding-bottom: 0.35rem;
}
```

#### Why This Breaks Layouts Across the Application:
1. **Destroys Tailwind Utility Predictability:** When a developer or component writes `p-6` intending 24px of whitespace, it silently renders as 12px (`0.75rem`).
2. **Arbitrary Partial Overrides:** It overrides `p-6`, `p-5`, `p-4`, and `p-3`, but does **not** override `p-8`, `p-2`, `p-1`, `gap-8`, or `gap-2`. This creates wild density mismatches: an inner container with `p-8` is suddenly 4 times larger than an outer container with `p-6`.
3. **Collapses Critical Interactive Tap Targets:** Buttons and badges using `p-3` or `py-3` have their heights crushed to 7px padding, violating accessibility minimums.
4. **CSS Specificity Clashes in Tailwind v4:** Because `@import "tailwindcss";` in Tailwind v4 manages cascade layers differently, these descendant overrides unpredictably win over standard breakpoint modifiers (e.g. `md:p-4`).

---

## 4. Routing Topology & URL Architecture

The application defines 32 route entries in Next.js App Router, which map to 17 canonical operational views and 15 convenience alias redirects:

| Canonical Route | Page Path | Alias Routes Pointing Here | Primary Purpose |
|---|---|---|---|
| `/` | `src/app/page.tsx` | `/agent-mission-control` | Top-level SOC Operations Dashboard & Infrastructure Status |
| `/ai-triage-workbench` | `src/app/ai-triage-workbench/page.tsx` | `/incidents` | Incident triage listing, canonical rule filtering, batch AI verdict |
| `/ai-triage-workbench/[id]` | `src/app/ai-triage-workbench/[id]/page.tsx` | `/incidents/[id]` | 4-dimension incident matrix, deep forensic telemetry inspector |
| `/telemetry-hub` | `src/app/telemetry-hub/page.tsx` | `/imports` | Continuous poller, batch ingest, FortiSIEM single pull, ZIP archive |
| `/human-review-queue` | `src/app/human-review-queue/page.tsx` | `/analyst-attention` | Double-blind human verification, escalation queue, disputed alerts |
| `/soc-chatbot` | `src/app/soc-chatbot/page.tsx` | *(None)* | Verdictum Sentinel AI copilot chat interface |
| `/agent-intelligence-studio` | `src/app/agent-intelligence-studio/page.tsx` | `/prompt-studio` | Policy directory table & 3-tab / legacy 7-tab rule studio |
| `/detection-intelligence` | `src/app/detection-intelligence/page.tsx` | `/rules` | SIEM rule inventory, readiness stage status, event-type catalog |
| `/detection-intelligence/[id]` | `src/app/detection-intelligence/[id]/page.tsx` | `/rules/[id]` | Raw rule definitions, correlation criteria, triggered attributes |
| `/agent-memory` | `src/app/agent-memory/page.tsx` | `/learning-history` | Stored ground truth training cases, vector similarity lookup |
| `/agent-simulation-lab` | `src/app/agent-simulation-lab/page.tsx` | `/dry-run` | Offline deterministic replay engine, regression testing |
| `/verdict-intelligence` | `src/app/verdict-intelligence/page.tsx` | `/evaluation-reports` | Quality metric graphs, pilot console, trustworthiness metrics |
| `/inference-control` | `src/app/inference-control/page.tsx` | `/infrastructure` | Server 1 & Server 2 telemetry, token bifurcation, GPU stats |
| `/agent-configuration` | `src/app/agent-configuration/page.tsx` | `/settings` | FortiSIEM credentials, local vLLM host/port, context budget |
| `/governance-access` | `src/app/governance-access/page.tsx` | `/admin` | User management, RBAC assignment, audit logs |
| `/admin-guide` | `src/app/admin-guide/page.tsx` | *(None)* | Interactive architecture reader, 17-stage workflow diagram |
| `/login` | `src/app/login/page.tsx` | *(None)* | Authentication portal |

---

## 5. Reusable Component Inventory & Evaluation

The repository contains shared component primitives located in `src/components/`:

### 5.1 `src/components/compact/CompactDesignSystem.tsx` (792 lines)
- **`CompactPageHeader`:** Top strip with title, subtitle, archetype pill, lifecycle status badge, back button, and selector slot.
  - *Defect:* Contains `truncate` on `h1` and forces right-side action buttons into `shrink-0`, which causes severe clipping on viewports under 1440px.
- **`MetricSummaryCard`:** Compact KPI card with label, value, subtext, status colors, and optional click handler.
- **`NextActionCard`:** High-contrast callout directing the operator to the next operational requirement (e.g. "Run AI Verdict", "Synthesize Draft").
- **`CompactVersionSelector`:** Dropdown selector for rule versions with Active/Approved tags and history modal link.
- **`EvidenceCompletenessIndicator`:** Progress bar showing core SIEM telemetry mapping.
- **`StatusBadge`:** Multi-variant pill for lifecycle and gate statuses.
- **`IssueSummary`:** Collapsible accordion listing prioritized diagnostic defects.

### 5.2 `src/components/compact/IncidentVerdictMatrix.tsx` (172 lines)
- **Purpose:** 4-dimension verdict clarity container rendering:
  1. AI Proposed Verdict (raw Local LLM output).
  2. Validated Verdict (passed through deterministic policy gates).
  3. Historical Ground Truth (masked when `blindReviewMode` is true).
  4. Operational SIEM Closure Status.
- **Evaluation:** High-value operational component; well-structured but requires tighter padding and flexible column wrapping on tablet screens.

### 5.3 `src/components/prompt-inspector/ActualPromptInspectorModal.tsx` (1279 lines)
- **Purpose:** Full-screen modal that shows the exact JSON payload and text prompt transmitted between Server 1 and Server 2 (Local LLM), including cryptographic hash verification and copy functions.
- **Evaluation:** Essential security transparency feature. Works reliably; needs compact header tabs and better monospace font sizing.

### 5.4 `src/components/system/ServerInfrastructureMonitor.tsx` (759 lines)
- **Purpose:** Real-time dual-server monitor displaying CPU, RAM, GPU VRAM, token latency, and live charts for Server 1 (Ingest/Backend) and Server 2 (vLLM inference).
- **Evaluation:** Very large visual footprint (height > 380px) on Mission Control; needs a compact mode toggle or condensed summary row.

---

## 6. Architecture Audit Verdict & Key Takeaways

1. **Stack Maturity:** The Next.js 16.4.5 + React 19 + Tailwind v4 stack is modern and performs exceptionally well (clean build in 1.5s). There is **zero technical debt** in the underlying bundler or framework layer.
2. **No Backend Refactoring Required:** All 17 canonical routes communicate with standard REST endpoints in `src/lib/api.ts`. The UI modernization can be accomplished purely on the frontend layer.
3. **The Root Cause of Visual Disarray is Cascading CSS & Unbalanced Flexbox:**
   - Brute-force descendant selector overrides in `globals.css`.
   - Global root `text-xs` forcing in `Shell.tsx`.
   - `shrink-0` on action button clusters competing against `min-w-0` title headers in flex rows.
   - Absence of a cohesive 12-column grid layout on complex detail pages.
