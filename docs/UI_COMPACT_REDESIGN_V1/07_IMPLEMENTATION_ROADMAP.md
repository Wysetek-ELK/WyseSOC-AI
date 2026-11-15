# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 07. Implementation Roadmap & File-by-File Execution Plan

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Phased Implementation Roadmap  
**Execution Strategy:** Strict Zero-Backend-Change, Non-Breaking Frontend Refactoring  
**Total Estimated Effort:** 10–14 Engineering Days (Split across 5 Phases)  

---

## 1. Overview & Phasing Strategy

The redesign is divided into **five sequential, dependency-aware phases**. Each phase is self-contained, independently verifiable, and safe to roll back if necessary.

```
[ Phase A: Global Layout Foundation ]
       │
       ▼
[ Phase B: High-Priority Layout Repairs (AIS Detail & Table) ]
       │
       ▼
[ Phase C: Operational Density Optimization (Telemetry Hub & Workbench) ]
       │
       ▼
[ Phase D: Global Visual Refinement & Design Token Alignment ]
       │
       ▼
[ Phase E: Automated Verification, Accessibility & Regression Testing ]
```

---

## 2. Phase-by-Phase Plan

### PHASE A — Global Layout Foundation & Design Token Modernization

- **Goal:** Establish clean shell boundaries, eliminate conflicting CSS overrides, and configure VCDS 1.0 design tokens.
- **Dependencies:** None.
- **Effort Estimate:** 2 Engineering Days.

#### Files Requiring Modification:
1. `frontend/src/app/globals.css`:
   - Remove lines 171–244 (brute-force Tailwind utility overrides).
   - Inject VCDS 1.0 tokens (`--vcds-*`) for obsidian surfaces, borders, and status colors.
   - Remove outer floating island margins on `.theme-sidebar-shell` and `.theme-glass-header`.
2. `frontend/src/components/layout/Shell.tsx`:
   - Remove `text-xs` from root `div`; set base font size to `text-sm`.
   - Update `<main>` padding to standardized `p-3` (12px).
3. `frontend/src/components/layout/Header.tsx`:
   - Set height to `h-11` (44px) without outer margin.
   - Refine search bar with `Ctrl+K` shortcut indicator.
4. `frontend/src/components/layout/Sidebar.tsx`:
   - Standardize expanded width to `w-60` (240px) and collapsed to `w-14` (56px).
   - Condense inference widget into sleek 2-line status bar.

#### Acceptance Criteria:
- Root layout renders cleanly edge-to-edge on 1024px, 1366px, 1440px, and 1920px viewports.
- Standard Tailwind padding (`p-4`, `p-6`, `gap-4`) behaves predictably without silent descendant overriding.
- Automated tests `tests/admin-guide.test.mjs` pass cleanly.

---

### PHASE B — High-Priority Layout Repairs (Agent Intelligence Studio)

- **Goal:** Resolve the critical Rule Detail layout defect and fix action column clipping in the Rule Directory Table.
- **Dependencies:** Phase A completed.
- **Effort Estimate:** 3 Engineering Days.

#### Files Requiring Modification:
1. `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:
   - Decouple action toolbar from the rule title header to eliminate horizontal flex compression.
   - Remove `truncate` from rule title; enable `line-clamp-2` with natural wrapping.
   - Implement the **12-column balanced grid**:
     - 8 columns on left for Rule Objective, 6-Stage Checklist, and Diagnostics.
     - 4 columns on right for Readiness Summary, 4 Metric Tiles, Version History, and Evidence Contract.
   - Remove `max-w-3xl` restriction on rule descriptions.
2. `frontend/src/components/compact/CompactDesignSystem.tsx`:
   - Update `CompactPageHeader` to support multi-line title wrapping.
   - Refactor `MetricSummaryCard` to fixed compact height `h-20` (80px).
3. `frontend/src/app/agent-intelligence-studio/page.tsx`:
   - Add fixed column widths to the Rules Directory Table (`w-64` for Rule Name, `w-24` for Severity, etc.).
   - Make the `Action` column **sticky right** (`sticky right-0 bg-slate-950/95 shadow-l`).
   - Retain full functionality of the `VERDICTUM_COMPACT_UI_ENABLED` rollout toggle.

#### Acceptance Criteria:
- Long rule titles (up to 80 characters) display fully without truncation or clipping.
- No dead space on the right side of the screen on 1440px and 1920px displays.
- Action buttons in the Rules Directory Table remain visible and accessible on 1280px and 1366px screens.
- Automated tests `tests/phase3-compact-ui.test.mjs` and `tests/production-readiness.test.mjs` pass 100%.

---

### PHASE C — Operational Density Optimization (Telemetry Hub & Workbench)

- **Goal:** Compress Telemetry Hub from a 5-level vertical stack into a dual-column control center; replace unbounded rule chips in AI Triage Workbench with a compact scope bar.
- **Dependencies:** Phase A and Phase B completed.
- **Effort Estimate:** 3 Engineering Days.

#### Files Requiring Modification:
1. `frontend/src/app/telemetry-hub/page.tsx`:
   - Replace 5-level vertical card stack with top 4-card compact KPI row.
   - Build dual-column control center: Continuous Poller on left (7 cols); Tabbed On-Demand Ingestion (Single ID + Archive Upload) on right (5 cols).
   - Consolidate Ingestion Jobs and Core Timeline into a unified tabbed data table.
   - Standardize button variants to VCDS 1.0 specifications.
2. `frontend/src/app/ai-triage-workbench/page.tsx`:
   - Replace unbounded chip mapping (Lines 468–500) with `CompactRuleScopeBar`.
   - Implement searchable canonical rule popover for queries matching >3 rules.
   - Add fixed heights (`h-9` / 36px) to incident table rows and make Action column sticky right.
3. `frontend/src/app/ai-triage-workbench/[id]/page.tsx`:
   - Optimize padding on `IncidentVerdictMatrix`.
   - Tighten sub-tab header spacing and ensure breadcrumbs stay anchored.

#### Acceptance Criteria:
- Telemetry Hub fits within ~900px vertical height; scrolling reduced by >60%.
- AI Triage incident table is immediately visible above the fold even when multi-rule searches match 30+ rules.
- Canonical rule disambiguation preserved: filtering strictly isolates incidents by `rule_uuid` and `logical_rule_id`.

---

### PHASE D — Global Visual Refinement & Design Token Alignment

- **Goal:** Unify tables, buttons, cards, typography, and badges across all remaining pages.
- **Dependencies:** Phases A–C completed.
- **Effort Estimate:** 3 Engineering Days.

#### Files Requiring Modification:
1. `frontend/src/app/page.tsx` (Agent Mission Control):
   - Add compact collapsible mode to `ServerInfrastructureMonitor`.
   - Standardize metric card heights (`h-24` / 96px).
2. `frontend/src/app/human-review-queue/page.tsx`:
   - Standardize table row heights; optimize slide-over investigation drawer.
3. `frontend/src/app/soc-chatbot/page.tsx`:
   - Compress message padding and format quick prompts as horizontal chip row.
4. `frontend/src/app/detection-intelligence/page.tsx` & `[id]/page.tsx`:
   - Align table columns and two-column detail layout.
5. `frontend/src/app/agent-simulation-lab/page.tsx`:
   - Compact benchmark summary cards and aligned replay controls.
6. `frontend/src/app/verdict-intelligence/page.tsx`:
   - Tighter chart wrappers and clean tab bar.
7. `frontend/src/app/agent-configuration/page.tsx`:
   - Tabbed configuration sections (FortiSIEM / Local LLM / Governance).
8. `frontend/src/app/governance-access/page.tsx`:
   - Split user list and slide-over user creation drawer.

#### Acceptance Criteria:
- All 17 canonical routes share the exact same button heights (30px), input heights (32px), and card border radii (8px).
- Zero horizontal overflow or unexpected double scrollbars across any page.

---

### PHASE E — Automated Verification, Accessibility & Regression Testing

- **Goal:** Validate 100% test passing, verify WCAG 2.1 AA accessibility, conduct responsive cross-browser testing, and verify zero functional regressions.
- **Dependencies:** Phases A–D completed.
- **Effort Estimate:** 2 Engineering Days.

#### Verification Activities:
1. Execute full automated test suite:
   ```powershell
   npm test --prefix frontend
   Push-Location frontend; node --experimental-strip-types --test tests/quality-export.test.mjs; Pop-Location
   ```
2. Run production build verification:
   ```powershell
   npm run build --prefix frontend
   ```
3. Test viewports: 1024×768, 1280×800, 1366×768, 1440×900, 1920×1080.
4. Verify keyboard focus rings and `prefers-reduced-motion` compliance.
5. Verify RBAC permissions: Administrator vs SOC Analyst vs Read-Only Viewer.

#### Acceptance Criteria:
- 100% of automated tests pass without modification of assertion logic.
- Production build succeeds with 0 errors and 0 warnings.
- All 17 pages pass WCAG 2.1 AA contrast requirements.

---

## 3. Rollback Strategy & Git Safety

Because all changes are strictly confined to the presentation layer in `frontend/src/`:
1. **Zero Database Risk:** No migrations, schemas, or database records are touched.
2. **Zero Backend API Risk:** Backend routes and schemas remain completely unmodified.
3. **Rollout Toggle Safeguard:** The `VERDICTUM_COMPACT_UI_ENABLED` toggle in `localStorage` allows instant client-side fallback to the legacy 7-tab view at any time.
4. **Git Branch Isolation:** Changes are implemented on a feature branch (`feature/compact-ui-redesign-v1`). If any regression is detected, the branch can be rolled back cleanly via standard Git operations.
