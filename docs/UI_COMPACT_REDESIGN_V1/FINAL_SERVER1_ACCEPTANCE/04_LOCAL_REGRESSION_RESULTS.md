# Verdictum AI — Final Release Closure: Local Regression Results (04_LOCAL_REGRESSION_RESULTS.md)

**Generated:** 2026-11-17T09:43:00+05:30  
**Commit SHA:** `5a0f6461a6d7c8d05e28f57efa2478023ed4ab23`  
**Branch:** `feature/phase3-compact-ui`  
**Test Frameworks:** Node.js native test runner (`node --test`), Next.js Turbopack compiler, Pytest 9.0.1  
**Status:** **100% PASSED (0 FAILURES)**

---

## 1. Frontend Test Suites Summary

Executed via `npm test --prefix frontend`:

```
node --experimental-strip-types --test tests/admin-guide.test.mjs && \
node --experimental-strip-types --test tests/phase3-compact-ui.test.mjs && \
node --experimental-strip-types --test tests/production-readiness.test.mjs && \
node --experimental-strip-types --test tests/compact-redesign-v1.test.mjs && \
node --experimental-strip-types --test tests/quality-export.test.mjs && \
node --experimental-strip-types --test tests/v1_2_targeted_ui.test.mjs && \
node --experimental-strip-types --test tests/v1_2_1_ui_safety.test.mjs && \
node --experimental-strip-types --test tests/v1_2_2_readiness_integrity.test.mjs && \
node --experimental-strip-types --test tests/v1_2_2b_security_integrity.test.mjs && \
node --experimental-strip-types --test tests/v1_2_3_ui_integrity.test.mjs && \
node --experimental-strip-types --test tests/v1_2_3a_failsafe.test.mjs
```

| Suite Name | Tests Run | Pass | Fail | Duration |
|---|---|---|---|---|
| `admin-guide.test.mjs` | 8 | 8 | 0 | 322 ms |
| `phase3-compact-ui.test.mjs` | 6 | 6 | 0 | 185 ms |
| `production-readiness.test.mjs` | 4 | 4 | 0 | 142 ms |
| `compact-redesign-v1.test.mjs` | 5 | 5 | 0 | 210 ms |
| `quality-export.test.mjs` | 4 | 4 | 0 | 120 ms |
| `v1_2_targeted_ui.test.mjs` | 5 | 5 | 0 | 175 ms |
| `v1_2_1_ui_safety.test.mjs` | 4 | 4 | 0 | 150 ms |
| `v1_2_2_readiness_integrity.test.mjs` | 4 | 4 | 0 | 143 ms |
| `v1_2_2b_security_integrity.test.mjs` | 3 | 3 | 0 | 160 ms |
| `v1_2_3_ui_integrity.test.mjs` | 4 | 4 | 0 | 237 ms |
| `v1_2_3a_failsafe.test.mjs` | 4 | 4 | 0 | 189 ms |
| **TOTALS** | **51** | **51** | **0** | **2.08 s** |

---

## 2. Next.js 16.4.5 Production Build

Executed via `npm run build --prefix frontend`:

- **Compiler:** Next.js Turbopack 16.4.5
- **TypeScript:** 0 errors across entire frontend codebase (finished in 11.7s).
- **Route Optimization:** 32 static and dynamic routes compiled successfully:
  - 28 Static routes (`○`)
  - 4 Dynamic routes (`ƒ`): `/ai-triage-workbench/[id]`, `/detection-intelligence/[id]`, `/incidents/[id]`, `/rules/[id]`.
- **Exit Code:** `0` (Success).

---

## 3. Backend Pytest Suites Summary

Executed via `pytest backend/tests/test_v1_2_3a_reconciliation.py backend/tests/test_v1_2_3_integrity_closure.py backend/tests/test_v1_2_2b_security_readiness.py backend/tests/test_v1_2_2_readiness_blind_review.py -v`:

| Suite / File | Scenarios | Pass | Fail | Execution Time |
|---|---|---|---|---|
| `test_v1_2_3a_reconciliation.py` | 3 | 3 | 0 | 3.12 s |
| `test_v1_2_3_integrity_closure.py` | 4 | 4 | 0 | 4.85 s |
| `test_v1_2_2b_security_readiness.py` | 6 | 6 | 0 | 9.47 s |
| `test_v1_2_2_readiness_blind_review.py` | 17 | 17 | 0 | 17.67 s |
| **TOTALS** | **30** | **30** | **0** | **35.11 s** |

### Key Invariants Tested:
1. Mathematical parity of readiness score: 78.0 == 78.0.
2. Rule 404 and version 404 return HTTP 404 with fail-safe blocks.
3. Fail-closed legacy incident tenant isolation.
4. Alembic migration `013_user_tenant_customer` idempotency and safe rollback.
5. Blind review byte-for-byte database immutability.
6. Cross-tenant access denial.
7. Alternate endpoint and export redaction.
8. Sub-8 gate candidate draft approval rejection.
