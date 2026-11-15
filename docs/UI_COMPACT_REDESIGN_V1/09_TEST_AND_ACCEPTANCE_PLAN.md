# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 09. Testing, Validation & Acceptance Plan

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Quality Assurance & Test Verification  
**Test Harness:** Node.js Native Test Runner (`node --test`), Next.js Production Build  
**Acceptance Threshold:** 100% Automated Tests Passing + 0 Production Build Errors  

---

## 1. Testing Framework & Philosophy

The UI Redesign must satisfy the fundamental principle of **Zero Operational Regression**:  
Visual and layout enhancements must not alter, bypass, or weaken any backend security rules, quality gate formulas, audit loggers, or ground-truth masking safeguards.

### Test Hierarchy:
```
[ Level 1: Automated Unit & Contract Tests (Node.js Test Runner) ]
                          │
                          ▼
[ Level 2: Production Build & Type Checking (Next.js Turbopack) ]
                          │
                          ▼
[ Level 3: Cross-Viewport Responsive Layout Inspection ]
                          │
                          ▼
[ Level 4: SOC Operational Workflow & Safety Acceptance ]
```

---

## 2. Existing Automated Test Suites & Regression Guards

The repository includes four specialized test suites in `frontend/tests/`. Every test in these suites must pass cleanly without modification to test assertions.

### 2.1 Test Suite Inventory

| Test File | Total Tests | Target Functionality Covered | Command to Execute |
|---|---|---|---|
| `tests/phase3-compact-ui.test.mjs` | 7 Tests | Operational status derivation, consolidated diagnostic issue extraction, HTTP error formatting, 3 primary tabs structure, rollout toggle persistence, double-blind review masking, replay engine heuristics | `npm run test:phase3 --prefix frontend` |
| `tests/production-readiness.test.mjs` | 5 Tests | 6-stage guided checklist, evidence completeness indicators, rule listing readiness columns, table filter states, empirical accuracy calculation | `npm run test:readiness --prefix frontend` |
| `tests/admin-guide.test.mjs` | 8 Tests | 17-stage architecture diagram, 9 decision engine steps, 8 lifecycle stages, 11 admin domains, workflow animation settings | `npm run test:admin-guide --prefix frontend` |
| `tests/quality-export.test.mjs` | 8 Tests | G1–G8 normalization, CSV formula injection defense (CWE-1236), Markdown/JSON export formatting, provenance digests | `Push-Location frontend; node --experimental-strip-types --test tests/quality-export.test.mjs; Pop-Location` |

### 2.2 Baseline Verification Execution
All 28 tests across the four suites were executed in the repository and confirmed passing:
- **`tests/admin-guide.test.mjs`:** 8/8 passed (224ms).
- **`tests/phase3-compact-ui.test.mjs`:** 7/7 passed (210ms).
- **`tests/production-readiness.test.mjs`:** 5/5 passed (122ms).
- **`tests/quality-export.test.mjs`:** 8/8 passed (242ms).

---

## 3. Functional Safety & Operational Test Matrix

| Functional Area | Test Scenario | Expected Outcome | Verification Method |
|---|---|---|---|
| **Quality Gates (G1–G8)** | Rule has hard blocker (e.g. missing correlation threshold) | Gate G1 marked `FAILED`; Rule state is `ACTION_REQUIRED`; Approval button strictly disabled | Source assertion in `AgentIntelligenceStudioOverview.tsx` |
| **Double-Blind Review** | Operator toggles Blind Review ON | Historical resolution verdicts, closure notes, and AI proposed verdicts are masked in Human Review Queue and Incident Detail | Verify `blindReviewMode` masking in `IncidentVerdictMatrix.tsx` |
| **Canonical Rule Filter** | Operator filters AI Triage Workbench by rule | Only incidents matching canonical `rule_uuid` / `logical_rule_id` render; zero cross-rule contamination | Test `api.getIncidents({ exact_rule_id })` query filter |
| **Inference Provenance** | Server 2 is offline or running HTTP Mock | Sidebar footer, Mission Control, and Telemetry Hub accurately reflect `OFFLINE` or `HTTP_MOCK (TEST)` | Check `formatServer2HealthSummary` output |
| **Rollout Toggle** | Operator toggles Legacy View in AIS | UI transitions from 3-tab compact view to legacy 7-tab view; preference persisted in `localStorage` | Assert `VERDICTUM_COMPACT_UI_ENABLED` toggle |
| **CSV Formula Injection** | Analyst exports quality gates CSV containing `=SUM(...)` or `@cmd` | Cell is sanitized with single quote prefix, neutralizing spreadsheet formula injection (CWE-1236) | Run `tests/quality-export.test.mjs` |

---

## 4. Responsive Viewport Acceptance Matrix

Every refactored page must be inspected against four canonical viewports:

| Test Viewport | Key Inspection Checks | Failure Condition |
|---|---|---|
| **1920 × 1080** | - 12-column grid balanced (8-col main + 4-col sidebar)<br>- No dead black space on right side of AIS overview<br>- Telemetry Hub dual-column fits without excessive scrolling | Empty gutters > 300px on the right; single-column stretching |
| **1440 × 900** | - AIS Rule Directory table displays all 9 columns cleanly<br>- Sticky Action column stays fixed on right edge<br>- Rule titles display up to 2 lines without harsh clipping | Rule title clipped to < 20 characters; Open Studio action pushed offscreen |
| **1366 × 768** | - AI Triage Workbench incident table visible without scrolling past rule chips<br>- Fixed table row heights (36px) prevent ragged wrapping<br>- Search & Filter bar wraps into single clean secondary line | Multi-rule warning blocks the incident table; horizontal scrollbar traps |
| **1024 × 768** | - Navigation sidebar automatically collapses to 56px icon strip<br>- 12-column grids gracefully stack to 1-column cascade<br>- Tap targets remain ≥ 28px × 28px | Layout breaks; text overflows outside cards; buttons overlap |

---

## 5. Visual Regression Testing Protocol

To ensure pixel-perfect fidelity across updates:
1. **Baseline Screenshot Capture:** Capture full-page reference screenshots across the 4 priority pages in both **Obsidian Glass** and **Classic Slate** themes.
2. **Comparison Verification:** Verify that:
   - Header height is uniformly 44px across all pages.
   - Card border radiuses are uniformly 8px (`rounded-lg`).
   - Table headers share identical background (`--vcds-bg-surface-0`) and typography.
   - Status badge colors match VCDS 1.0 specifications exactly.

---

## 6. Release Sign-Off Criteria

The implementation is approved for production release only when:
- [ ] 100% of the 28 automated tests pass without modification to test logic.
- [ ] `npm run build` executes with exit code 0 and zero compilation warnings.
- [ ] All 10 cataloged layout defects in `02_UI_LAYOUT_DEFECTS.md` are verified resolved.
- [ ] All 4 priority pages meet the responsive acceptance criteria on 1024px, 1366px, 1440px, and 1920px viewports.
- [ ] WCAG 2.1 AA contrast requirements are satisfied across all text tokens.
- [ ] Zero database schemas, backend APIs, or security policies are modified.
