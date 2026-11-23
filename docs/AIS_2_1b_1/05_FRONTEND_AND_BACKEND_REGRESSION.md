# AIS 2.1b.1 — Frontend & Backend Regression Test Report

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Test Suite**: Full Automated Regression Suite  
**Date**: November 23, 2026  

---

## 1. Executive Summary

All automated regression tests for AIS 2.1b.1 passed with 100% success rate:
- **Backend Pytest Suite**: **25 passed** in 42.02s
- **Frontend Jest/RTL Suite**: **88 passed** (10 test suites) in 4.31s
- **Next.js Production Build**: **32 / 32 routes compiled and optimized** with zero TypeScript or ESLint errors

---

## 2. Backend Regression Results

Command executed:
```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests/test_ais_unified_population_contract.py backend/tests/test_ais_evaluation_tracking.py -v
```

### Key Test Outcomes:
1. `backend/tests/test_ais_unified_population_contract.py`:
   - `test_unified_population_contract_structure`: **PASSED** (Verifies mandatory population schema)
   - `test_deterministic_snapshot_consistency_across_queries`: **PASSED** (Verifies snapshot consistency and deterministic fingerprinting across consecutive reads and mutations)
   - `test_partition_invariant_enforcement`: **PASSED** (Verifies $\text{Total} = \text{Decisive} + \text{Abstained} + \text{Rejected} + \text{Failed} + \text{Not Evaluated}$)
   - `test_not_measurable_accuracy_when_decisive_zero`: **PASSED** (Verifies selective accuracy is null and status is NOT_MEASURABLE when decisive denominator is 0)
   - `test_tenant_and_policy_isolation`: **PASSED** (Verifies multi-tenant isolation and policy boundary segregation)
2. `backend/tests/test_ais_evaluation_tracking.py`:
   - 20 / 20 tests **PASSED** (Verifies evaluation status transitions, batch evaluation tracking, queuing logic, rollback-safe transactions, and analyst review submissions)

Total: **25 passed, 0 failed, 0 errors**

---

## 3. Frontend Unit & Integration Regression Results

Command executed:
```powershell
npm.cmd test -- --watchAll=false
```

### Test Suites:
- `CompactPageHeader.test.tsx`: **PASSED** (Verifies compact toolbar rendering, policy status badges, and action triggers)
- `AccuracyLearningSummary.test.tsx`: **PASSED** (Verifies dynamic count bindings, absence of static 13/45 fallbacks, and NOT_MEASURABLE card)
- `DominantIncidentTable.test.tsx`: **PASSED** (Verifies compact table geometry, sorting, filtering, and status badge colors)
- `EvaluationMetricsGrid.test.tsx`: **PASSED** (Verifies KPI card values, secondary outcome counts, and partition invariant display)
- `ReviewIncidentsWorkbench.test.tsx`: **PASSED** (Verifies double-blind review protection and evidence timeline)
- `PolicyVersionSelector.test.tsx`: **PASSED** (Verifies switching between approved v7 and draft v8)
- Additional utility and state management suites: **PASSED**

Total: **10 test suites passed, 88 tests passed**

---

## 4. Next.js Production Build Verification

Command executed:
```powershell
npm.cmd run build
```

### Build Output Summary:
- Compiled 32 static and server routes cleanly.
- Page `/agent-intelligence-studio`: **Static (prerendered as static content)**
- Route size: `12.8 kB`, First Load JS: `214 kB`
- Zero TypeScript diagnostics. Zero Webpack bundling warnings. Zero circular dependency warnings.
