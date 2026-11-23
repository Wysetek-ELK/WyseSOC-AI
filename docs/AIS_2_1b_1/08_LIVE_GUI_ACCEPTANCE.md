# AIS 2.1b.1 — Live GUI Acceptance Report

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Acceptance Test Suite**: Headless Chrome CDP Live Browser Suite (`scripts/run_ais_2_1b_1_gui_acceptance.mjs`)  
**Target Environment**: Server 1 (`http://172.26.41.240:3000`)  
**Target Rule**: Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Execution Timestamp**: November 23, 2026, 03:32:08 UTC  
**Result**: 100% PASSED  

---

## 1. Acceptance Screenshot Manifest

All 9 acceptance screenshots were captured via direct Chrome DevTools Protocol (CDP) session against the live deployed application on Server 1 and saved to `docs/AIS_2_1b_1/screenshots/`:

1. `01_login_page.png` (779.8 KB): Initial unauthenticated state and clean login interface.
2. `02_compact_toolbar_and_action_1440x900.png` (560.9 KB): Top compact header showing `v7 APPROVED` and `v8 DRAFT` status badges, rule title, and compact action button at 1440×900.
3. `03_test_ai_dominant_table_1440x900.png` (602.9 KB): Tab 2 (Test AI) showing dominant incident evaluation table, 35 total incidents, model context strip (`Qwen/Qwen2.5-7B-Instruct-AWQ`), and GPU online badge.
4. `04_accuracy_learning_tab_1440x900.png` (655.1 KB): Tab 3 (Accuracy & Learning) showing dynamic `Current Incident Inventory (35)` and `Cumulative Historical Cohort (65)` without hardcoded 13/45 text, displaying `NOT MEASURABLE` selective accuracy.
5. `05_review_incidents_tab_1440x900.png` (560.9 KB): Tab 1 (Review Incidents) showing double-blind incident list and analyst verdict review actions.
6. `06_advanced_settings_drawer_1440x900.png` (719.7 KB): Operational slide-out drawer providing full access to advanced policy parameters, prompt templates, and learning thresholds.
7. `07_viewport_1280x800.png` (512.5 KB): Layout and fold verification at 1280×800 resolution with zero horizontal overflow.
8. `08_viewport_1727x972.png` (758.1 KB): Full-width verification at 1727×972 resolution with zero horizontal overflow.
9. `09_viewport_1920x1080.png` (917.0 KB): High-definition verification at 1920×1080 resolution with zero horizontal overflow.

---

## 2. Live Assertion Audit

| Component / Assertion | Metric / Selector | Expected Value | Live Measured Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dual Branding** | Top header logos | Verdictum AI & Wysetek | Present & visible | **PASS** |
| **Target Rule Title** | Page header | Heavy TCP Host Scan... | Present | **PASS** |
| **Approved Policy Badge** | `[data-testid="header-active-policy-status"]` | `v7 APPROVED` | `"v7 APPROVED"` | **PASS** |
| **Draft Policy Badge** | `[data-testid="header-draft-policy-status"]` | `v8 DRAFT` | `"v8 DRAFT"` | **PASS** |
| **Tab Navigation** | Operational tabs | 3 tabs | Review, Test AI, Accuracy | **PASS** |
| **Incident Table Top** | DOM client bounding rect | $< 900\text{px}$ (visible without scroll) | `550px` | **PASS** |
| **Table Visibility** | `tableVisibleWithoutScroll` | `true` | `true` | **PASS** |
| **Incident Inventory** | Total count card | Consistent across tabs | `35` | **PASS** |
| **Partition Invariant** | Outcome partition | $0+33+0+0+2 = 35$ | $0+33+0+0+2 = 35$ | **PASS** |
| **Historical Cohort** | Cumulative reviews card | Dynamic count | `65` reviews (0 TP / 65 FP) | **PASS** |
| **Stale Fallback Check** | `hasContradictory13Reviews45FP` | `false` | `false` | **PASS** |
| **Accuracy Measure** | Selective accuracy card | `NOT MEASURABLE` | `NOT MEASURABLE` (null) | **PASS** |
| **Advanced Settings** | Drawer trigger button | Accessible on all tabs | Functional drawer | **PASS** |
| **Zero Overflow (1280)** | `scrollWidth === clientWidth` | `true` | `true` | **PASS** |
| **Zero Overflow (1440)** | `scrollWidth === clientWidth` | `true` | `true` | **PASS** |
| **Zero Overflow (1727)** | `scrollWidth === clientWidth` | `true` | `true` | **PASS** |
| **Zero Overflow (1920)** | `scrollWidth === clientWidth` | `true` | `true` | **PASS** |

---

## 3. Cross-Tab Consistency Conclusion

All five issues identified in AIS 2.1b have been completely eliminated:
- **Issue A**: Replaced static fallbacks with dynamic bindings; verified on live Server 1.
- **Issue B**: Live ingestion confirmed; partition invariant mathematically verified ($35 = 33 + 2$).
- **Issue C**: `REPEATABLE READ READ ONLY` transaction isolation and SHA-256 fingerprinting active.
- **Issue D**: `v7 APPROVED` and `v8 DRAFT` badges rendered and discoverable in the compact header.
- **Issue E**: Actual table top geometry measured at 550px; visible above the fold on all standard displays.
