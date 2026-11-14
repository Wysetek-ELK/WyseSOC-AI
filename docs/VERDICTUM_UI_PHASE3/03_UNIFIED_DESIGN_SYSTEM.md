# VERDICTUM AI — PHASE 3
# 03. Unified Compact Design System & Component Library

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Component Location:** `frontend/src/components/compact/CompactDesignSystem.tsx`  

---

## 1. Design Direction & Principles

The Phase 3 Unified Design System adheres to the standard enterprise cybersecurity dashboard aesthetic:
- **Palette:** Deep slate/zinc dark theme (`#020617`, `#090d16`, `#0f172a`) with subtle surface contrast and crisp 1px borders (`border-slate-800`).
- **Semantic Accents:**
  - Cyan (`text-cyan-400`, `border-cyan-800`): Active primary navigation, system focus, intelligence features.
  - Emerald (`text-emerald-400`, `border-emerald-800`): Passed gates, verified verdicts, production active, high confidence.
  - Amber (`text-amber-400`, `border-amber-800`): Warnings, pilot mode, uncalibrated confidence, pending reviews, double-blind mode.
  - Rose (`text-rose-400`, `border-rose-800`): Critical gate blockers, True Positive threats, errors, disputed reviews.
- **Typography:** Inter/system sans-serif for operational prose; tabular monospaced font (`font-mono`) for metrics, IDs, IP addresses, and timestamps.
- **Compact Padding:** 8px to 12px standard card padding (`p-2.5` to `p-3.5`) ensuring maximum vertical data density without visual clutter.

---

## 2. Standardized Component Library

### 2.1 `CompactPageHeader`
Responsive header component supporting single-row desktop layout and two-row mobile layout:
- Renders page title, category badge, and active operational status pill.
- Supports dropdown rule selector, version badge, and right-aligned action buttons.

### 2.2 `MetricSummaryCard`
High-density KPI display component:
- Displays metric label, primary numerical value, secondary subtext, and status border styling (`normal`, `success`, `warning`, `danger`, `neutral`).
- Optional click handlers for deep-dive navigation.

### 2.3 `RuleStatusSummary`
Unified 4-card hero row displaying:
1. **Rule Quality:** G1–G8 validation score (0–100) with passed gate tally.
2. **AI Accuracy:** Verified empirical accuracy or explicit `N/A (Requires verified analyst reviews)`.
3. **Analyst Reviews:** Count of completed independent human evaluations toward the 30-sample threshold.
4. **Automation Status:** Current enforcement state (`DISABLED`, `PILOT`, `APPROVED`, `ACTIVE`).

### 2.4 `NextActionCard`
High-priority actionable call-to-action component:
- Communicates the single most important operational task currently facing the analyst.
- Features high-contrast border and integrated action trigger button with arrow indicator.

### 2.5 `IssueSummary` & `DiagnosticIssueCard`
Consolidated diagnostic container:
- Replaces scattered warning banners with a single prioritized container.
- Renders issue title, severity badge, root cause, missing elements, operational impact, and 1-click navigation to the resolving tab.
- Collapsible missing info inspector for technical details.

### 2.6 `CompactVersionSelector`
Dropdown version selector replacing the legacy 25% sidebar column:
- Displays current version, status badge (`DRAFT`, `APPROVED`, `ARCHIVED`), and digest hash.
- Integrates rollback action trigger directly in the selector toolbar.

### 2.7 `AdvancedDetailsPanel`
Accessible collapsible accordion container:
- Wraps technical telemetry, model payloads, validator reason codes, and token metrics.
- Closed by default to maintain clean screen density; expands smoothly on demand.

### 2.8 `IncidentVerdictMatrix`
4-dimension verdict clarity matrix:
1. **AI Proposed Verdict:** Raw output from local LLM prior to validation.
2. **Platform Validated Verdict:** Authoritative determination following deterministic validation guards.
3. **Analyst Verified Verdict:** Human-in-the-loop ground truth evaluation.
4. **Operational SIEM Status:** FortiSIEM incident closure and sync state.

---

## 3. Style Tokens & Tailwind Compatibility

All components utilize Tailwind CSS v4 design tokens and semantic CSS variables defined in `globals.css`:
- `theme-hero-score-card`: Subtle gradient hero container.
- `theme-primary-btn`: Cyan-accented interactive button.
- `theme-secondary-btn`: Slate-accented secondary action button.
- `tabular-nums`: Fixed-width numerals preventing layout shift during live metrics polling.
