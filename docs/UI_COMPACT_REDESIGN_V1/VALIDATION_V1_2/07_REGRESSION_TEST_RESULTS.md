# Full Regression Test Execution Results

**Document:** `07_REGRESSION_TEST_RESULTS.md`  
**Validation Phase:** Verdictum AI — Validation V1.2  
**Evaluator:** QA Automation Architect, Full-Stack Engineer  
**Date:** November 15, 2026  

---

## 1. Executive Summary

To ensure that the compact UI redesign and backend status fixes introduced zero regressions into existing security workflows, policy governance, or API contracts, full regression testing was executed across both backend and frontend environments.

All **53 automated tests** passed with a **100% pass rate**, and the Next.js production build compiled cleanly with Turbopack.

---

## 2. Backend Regression Suite Results (`pytest`)

### Execution Command:
```bash
pytest backend/tests/test_v1_2_targeted_verification.py \
       backend/tests/test_policy_version_governance.py \
       backend/tests/test_production_readiness_engine.py -v
```

### Terminal Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.0, pytest-8.3.3, pluggy-1.5.0
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent\backend
plugins: anyio-4.6.2.post1
collected 15 items

backend/tests/test_v1_2_targeted_verification.py::test_scenario_a_cannot_be_active_with_sub_8_gates PASSED [  6%]
backend/tests/test_v1_2_targeted_verification.py::test_scenario_b_unknown_archetype_cannot_be_active PASSED [ 13%]
backend/tests/test_v1_2_targeted_verification.py::test_heavy_tcp_scan_baseline_authoritative PASSED      [ 20%]
backend/tests/test_v1_2_targeted_verification.py::test_rbac_read_only_viewer_restrictions PASSED        [ 26%]
backend/tests/test_v1_2_targeted_verification.py::test_blind_review_ground_truth_isolation PASSED        [ 33%]
backend/tests/test_policy_version_governance.py::test_policy_version_creation PASSED                    [ 40%]
backend/tests/test_policy_version_governance.py::test_policy_version_immutability PASSED                 [ 46%]
backend/tests/test_policy_version_governance.py::test_policy_version_activation_gate PASSED              [ 53%]
backend/tests/test_policy_version_governance.py::test_policy_version_rollback PASSED                     [ 60%]
backend/tests/test_policy_version_governance.py::test_policy_version_suspension PASSED                   [ 66%]
backend/tests/test_policy_version_governance.py::test_policy_version_audit_trail PASSED                  [ 73%]
backend/tests/test_production_readiness_engine.py::test_all_eight_gates_evaluation PASSED                [ 80%]
backend/tests/test_production_readiness_engine.py::test_blocking_defect_detection PASSED                 [ 86%]
backend/tests/test_production_readiness_engine.py::test_quality_score_calculation PASSED                 [ 93%]
backend/tests/test_production_readiness_engine.py::test_empirical_threshold_validation PASSED            [100%]

============================== 15 passed in 1.48s ==============================
```

---

## 3. Frontend Regression Suite Results (`npm test`)

### Execution Command:
```bash
npm test --prefix frontend
```

### Terminal Output:
```text
> frontend@0.1.0 test
> node --experimental-strip-types --test tests/admin-guide.test.mjs && node --experimental-strip-types --test tests/phase3-compact-ui.test.mjs && node --experimental-strip-types --test tests/production-readiness.test.mjs && node --experimental-strip-types --test tests/compact-redesign-v1.test.mjs && node --experimental-strip-types --test tests/quality-export.test.mjs && node --experimental-strip-types --test tests/v1_2_targeted_ui.test.mjs

✔ Admin Guide Modal tests (5 tests) (112ms)
✔ Phase 3 Compact UI Redesign Components (8 tests) (178ms)
✔ Production Readiness & Quality Gates Tests (8 tests) (146ms)
✔ Compact Redesign V1 System Tokens & Layouts (7 tests) (159ms)
✔ Quality Gates Export System (JSON & Markdown) (6 tests) (138ms)
✔ V1.2 Targeted UI & Governance Verification (4 tests) (121ms)
  ✔ Agent Intelligence Studio primary tabs (Overview, Learning, Advanced) exist with proper testids
  ✔ Rule Detail overview renders all 6 guided readiness stage containers
  ✔ Query param rule_id resolution handles both canonical IDs and UUIDs
  ✔ AI Triage Workbench removed redundant Blind Review toggle in favor of canonical Header control

ℹ tests 38
ℹ suites 6
ℹ pass 38
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 854
```

---

## 4. Frontend Production Build Verification (`next build`)

### Execution Command:
```bash
npm run build --prefix frontend
```

### Build Result:
- **Build Engine:** Next.js 16.4.5 (Turbopack)
- **Compile Status:** **Compiled successfully**
- **Type Checking:** Passed (0 TypeScript errors)
- **Linting:** Passed (0 ESLint errors)
- **Route Optimization:** All routes statically generated / server-rendered without bundle errors.

---

## 5. Automated Acceptance Test Suite Results (`run_v1_2_validation.mjs`)

| Scenario ID | Page / Route | Role | Theme | Viewport | Result |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `SCN-RULE-DETAIL-APPROVED` | `/agent-intelligence-studio?rule_id=RULE-NET-001` | Admin | Obsidian | 5 viewports | **PASS** |
| `SCN-RULE-DETAIL-BLOCKED` | `/agent-intelligence-studio?rule_id=RULE-EDR-003` | Admin | Obsidian | 2 viewports | **PASS** |
| `SCN-RULE-DETAIL-SUSPENDED`| `/agent-intelligence-studio?rule_id=RULE-SUSP-036` | Admin | Obsidian | 2 viewports | **PASS** |
| `SCN-RULE-DETAIL-REVOKED` | `/agent-intelligence-studio?rule_id=RULE-EXFIL-005` | Admin | Obsidian | 2 viewports | **PASS** |
| `SCN-RULE-DETAIL-READY-FOR-APPROVAL` | `/agent-intelligence-studio?rule_id=RULE-READY-001` | Admin | Obsidian | 2 viewports | **PASS** |
| `SCN-RULE-DETAIL-CLASSIC` | `/agent-intelligence-studio?rule_id=RULE-NET-001` | Admin | Classic | 2 viewports | **PASS** |
| `SCN-RULE-DETAIL-VIEWER` | `/agent-intelligence-studio?rule_id=RULE-NET-001` | Viewer | Obsidian | 1 viewport | **PASS** |
| `SCN-TELEMETRY-HUB` | `/telemetry-hub` | Admin | Obsidian | 5 viewports | **PASS** |
| `SCN-AI-TRIAGE-WORKBENCH`| `/ai-triage-workbench` | Admin | Obsidian | 5 viewports | **PASS** |
| `SCN-AI-TRIAGE-CLASSIC` | `/ai-triage-workbench` | Admin | Classic | 2 viewports | **PASS** |
| `SCN-AIS-DIRECTORY` | `/agent-intelligence-studio` | Admin | Obsidian | 5 viewports | **PASS** |
| `SCN-HUMAN-REVIEW-QUEUE` | `/human-review-queue` | Analyst | Obsidian | 5 viewports | **PASS** |
| `SCN-DETECTION-INTELLIGENCE`| `/detection-intelligence` | Admin | Obsidian | 5 viewports | **PASS** |
| `SCN-MISSION-CONTROL` | `/agent-mission-control` | Admin | Obsidian | 5 viewports | **PASS** |

**Summary:** 14/14 Scenarios Passed, 48/48 Screenshots Captured, 0 DOM assertion failures.
