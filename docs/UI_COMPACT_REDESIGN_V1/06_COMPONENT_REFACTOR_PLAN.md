# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 06. Component Refactoring & Consolidation Plan

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Component Refactor Specifications  
**Design Reference:** Verdictum Compact Design System v1.0 (VCDS 1.0)  
**Target Repository:** `frontend/src/components/` & `frontend/src/app/`  

---

## 1. Overview of Component Architecture Changes

The Compact UI/UX Redesign transforms the presentation layer while strictly maintaining 100% backward compatibility with existing backend API data contracts (`src/lib/api.ts`) and unit test assertions.

### Core Strategy:
1. **Refactor Existing Primitives:** Enhance `CompactDesignSystem.tsx` components to support compact variants, proper text wrapping, and decoupled action toolbars.
2. **Consolidate Ad-Hoc UI Blocks:** Replace duplicated chip mappings, disparate status badges, and inconsistent table cells with reusable VCDS 1.0 primitives.
3. **No Breaking Interface Changes:** Preserve all existing prop interfaces or extend them with optional properties so existing pages continue functioning during phased rollout.

---

## 2. Shared Layout Components Refactoring

### 2.1 `src/components/layout/Shell.tsx`
- **Current State:** Hard-codes `font-sans text-xs` on the root container and applies minimal canvas padding `p-2 sm:p-2.5`.
- **Proposed Refactoring:**
  - Remove `text-xs` from the root `div`; set base font size to `text-sm` for natural typographical hierarchy.
  - Standardize `<main>` canvas padding to `p-3 sm:p-3.5` (12px to 14px).
  - Eliminate outer margin gaps so the shell fills the viewport seamlessly.

### 2.2 `src/components/layout/Header.tsx`
- **Current State:** Height `h-10` (40px) with `margin: 0.375rem` floating card in Obsidian mode. Contains duplicate blind review toggle.
- **Proposed Refactoring:**
  - Standardize height to `h-11` (44px) anchored to top edge (`margin: 0`).
  - Add keyboard shortcut pill (`Ctrl+K` / `⌘K`) to the global search input.
  - Refine role badge contrast and theme toggle button styling.

### 2.3 `src/components/layout/Sidebar.tsx`
- **Current State:** Width `w-56` (224px) / `w-12` (48px). Real-time inference card at the bottom occupies significant vertical space and truncates long model names.
- **Proposed Refactoring:**
  - Update widths to `w-60` (240px) expanded, `w-14` (56px) collapsed for better icon tap targets.
  - Refactor footer inference telemetry widget into a compact 2-line status bar:
    - Line 1: `● S2 Online: Qwen 2.5 7B`
    - Line 2: `Arch: S1+S2 vLLM · HTTP_MOCK / ACTIVE`
  - Tooltip reveals full provenance details without requiring vertical expansion.

---

## 3. Design System Primitives (`src/components/compact/CompactDesignSystem.tsx`)

### 3.1 `CompactPageHeader`
- **Defects Addressed:** Title clipping (`truncate` on `h1`), action button squeeze (`shrink-0` on action cluster).
- **Refactored Contract:**
```tsx
export interface CompactPageHeaderProps {
  title: string;
  subtitle?: string;
  archetype?: string;
  ruleId?: string;
  lifecycleStatus?: {
    label: string;
    badgeClass: string;
    dotClass: string;
  };
  backAction?: {
    label: string;
    onClick: () => void;
  };
  actions?: React.ReactNode;
  selector?: React.ReactNode;
  allowTitleWrap?: boolean; // New: Defaults to true, removes harsh truncate
}
```
- **Changes:**
  - Title wraps cleanly up to 2 lines (`text-base sm:text-lg font-bold line-clamp-2` instead of `truncate`).
  - Action container wraps onto a clean secondary row when viewport is under 1280px rather than compressing the title block.

### 3.2 `MetricSummaryCard`
- **Changes:**
  - Standardize fixed card height: `h-20` (80px) for compact viewports.
  - Value typography: `text-xl sm:text-2xl font-bold font-mono tracking-tight tabular-nums`.
  - Subtext: `text-[10px] text-slate-400 font-sans`.

### 3.3 New Component: `CompactRuleScopeBar`
- **Purpose:** Replaces the unbounded multi-rule chip cascade in `ai-triage-workbench/page.tsx`.
- **Props Interface:**
```tsx
export interface CompactRuleScopeBarProps {
  totalIncidents: number;
  distinctRuleCount: number;
  matchedRules: Array<{
    rule_uuid?: string | null;
    logical_rule_id: string;
    incident_count: number;
    event_type?: string;
  }>;
  selectedRuleId: string;
  onSelectRule: (ruleId: string) => void;
  onClearRule: () => void;
}
```
- **UI Structure:**
  - 1-line warning alert: `⚠️ Results combine {count} distinct SIEM rules across {total} incidents.`
  - Searchable rule popover dropdown.
  - Top 3 high-frequency rule chips with a `+{n} more rules...` popover trigger.

---

## 4. Agent Intelligence Studio Overview (`AgentIntelligenceStudioOverview.tsx`)

### Complete Structural Refactor:
The component is reorganized from a single vertical stack into a **balanced 12-column grid layout**:

```tsx
export function AgentIntelligenceStudioOverview(props: AgentIntelligenceStudioOverviewProps) {
  return (
    <div className="space-y-3">
      {/* 1. Header & Primary Action Toolbar */}
      <AISRuleHeaderStrip ... />

      {/* 2. Main 12-Column Balanced Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
        {/* Left Column (8 Columns / 66.6% Width) */}
        <div className="lg:col-span-8 space-y-3">
          {/* Smart Next Action Directive */}
          <NextActionCard ... />

          {/* Guided 6-Stage Production Readiness Checklist */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2.5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Guided Production Readiness Checklist
            </h2>
            {/* 6 Stage Cascade with Progressive Disclosure */}
          </div>

          {/* Consolidated Diagnostic Issues ("What Needs Attention?") */}
          <IssueSummary issues={consolidatedIssues} ... />
        </div>

        {/* Right Column (4 Columns / 33.3% Width) */}
        <div className="lg:col-span-4 space-y-3">
          {/* Production Readiness Status Card */}
          <ProductionReadinessCard ... />

          {/* 4 Hero Key Metrics (Quality, Reviews, Accuracy, Enforcement) */}
          <div className="grid grid-cols-2 gap-2">
            <MetricSummaryCard label="Quality Score" value={`${qualityScore}/100`} ... />
            <MetricSummaryCard label="Analyst Reviews" value={`${totalReviews}/30`} ... />
            <MetricSummaryCard label="Empirical Accuracy" value={accuracyDisplay} ... />
            <MetricSummaryCard label="Enforcement State" value={enforcementState} ... />
          </div>

          {/* Evidence Contract Feasibility Widget */}
          <EvidenceContractGlance ... />

          {/* Quick Version History */}
          <CompactVersionHistoryList ... />
        </div>
      </div>
    </div>
  );
}
```

---

## 5. Priority Page Component Refactor Summary

| Target Page / File | Existing Component Defect | Refactored Component Solution | Expected Layout Gain |
|---|---|---|---|
| `ai-triage-workbench/page.tsx` | Unbounded chip loop (L468–500) | `CompactRuleScopeBar` with popover | Saves 250px–400px vertical space; incident table visible above fold |
| `agent-intelligence-studio/page.tsx` | Clipped table action buttons (L1482–1520) | Sticky Right Action column with fixed-width headers | Zero action clipping on viewports down to 1024px |
| `telemetry-hub/page.tsx` | 5-level vertical stack (L276–850) | Dual-Column Ingestion Control Center + Tabbed Logs | Reduces page scrolling by >60%; unifies button styles |
| `ServerInfrastructureMonitor.tsx` | Tall fixed hardware charts (759 lines) | Collapsible hardware accordion (`compact={true}`) | Conserves 280px on Agent Mission Control |
| `IncidentVerdictMatrix.tsx` | Crowded 4-card grid on tablet screens | Responsive 2x2 grid on tablet, 4x1 on desktop | Eliminates horizontal scrollbar traps |

---

## 6. Safe Phased Implementation Guardrails

To prevent breaking regression across the 4 automated test suites:
1. **Retain All Data Test IDs:** All `data-testid` attributes (`exact-rule-filter-banner`, `multi-rule-search-warning`, `sidebar-inference-widget`, `header-user-name`, etc.) must be strictly preserved on the refactored elements.
2. **Preserve Rollout Toggle:** Retain `VERDICTUM_COMPACT_UI_ENABLED` in `localStorage` and keep the legacy 7-tab view fully operational for operator fallback.
3. **Zero Behavioral API Changes:** All refactored components consume the existing data types from `src/lib/api.ts` without modifying endpoint signatures or query parameters.
