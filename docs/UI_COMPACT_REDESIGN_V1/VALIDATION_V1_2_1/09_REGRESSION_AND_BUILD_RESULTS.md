# VERDICTUM AI — VALIDATION V1.2.1
## 09. REGRESSION & BUILD VALIDATION RESULTS

**Document Version:** 1.0.0  
**Testing Frameworks:** Pytest 9.0.1 (Python 3.13), Node Test Runner (Node.js 22+)  
**Status:** 100% PASSING (Zero Regressions)  

---

### 1. Backend Automated Regression Testing

#### Command:
```powershell
$env:PYTHONPATH="backend"; pytest backend/tests/test_v1_2_1_readiness_integrity.py backend/tests/test_agent_intelligence_studio_v2.py
```

#### Results:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.0.1, pluggy-1.6.0
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent
plugins: anyio-4.9.0, langsmith-0.7.22, asyncio-1.4.0, mock-3.15.1, respx-0.23.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 18 items

backend\tests\test_v1_2_1_readiness_integrity.py .......                 [ 38%]
backend\tests\test_agent_intelligence_studio_v2.py ...........           [100%]

============================= 18 passed in 3.56s ==============================
```

#### Detailed Breakdown of Passed Test Cases:
1. `test_scenario_a_approved_version_readiness_decoupling`: Verifies Heavy TCP v1 is flagged as `REVALIDATION REQUIRED` and not false `ACTIVE`.
2. `test_scenario_b_candidate_version_incomplete_definition_blocked`: Verifies hard failure on G1 definitions blocks approval.
3. `test_scenario_c_draft_with_partial_gates_not_approval_eligible`: Verifies 6/8 gates candidate draft rejects approval API call.
4. `test_blind_review_sanitizes_ai_verdict_over_api`: Verifies `ai_verdict` sanitized to `None` on the wire before analyst review.
5. `test_wilson_lower_bound_math_no_fabrication`: Verifies $n=0$ returns `None` and $n=30$ with 0 errors does not reach 96%.
6. `test_wilson_lower_bound_93_error_free_samples_threshold`: Verifies mathematical boundary ($n=92 \implies 95.99\%$, $n=93 \implies 96.03\%$).
7. `test_rbac_viewer_cannot_approve_or_mutate`: Verifies `viewer` role receives HTTP 403 on approval mutation.
8. `test_rule_learning_service_metrics`: Verifies learning profile recalculation and drift metrics.
9. `test_production_readiness_service_stages`: Verifies 6-stage readiness model derivation.
10. `test_production_readiness_api_endpoint`: Verifies `/api/prompts/rules/{id}/readiness` endpoint responses.
11. `test_reference_case_large_outbound_transfer_full_lifecycle`: Verifies end-to-end AIS 2.0 lifecycle on canonical data transfer rule.
12. `test_reference_case_credential_dumping_lsass_full_lifecycle`: Verifies LSASS dumping rule quality gates and simulation.
13. `test_reference_case_brute_force_ssh_full_lifecycle`: Verifies SSH brute force rule and readiness checklist.
14. `test_ground_truth_isolation`: Verifies ground-truth separation from evaluation runs.
15. `test_policy_quality_assessment_scoring`: Verifies G1–G8 scoring and defect aggregation.
16. `test_quality_gates_export_structure`: Verifies JSON/Markdown/CSV export integrity.
17. `test_prompt_version_revocation_rejection`: Verifies revoked versions cannot be approved.
18. `test_unacknowledged_drift_rejection`: Verifies unacknowledged drift blocks promotion.

---

### 2. Frontend Automated Test Suites

#### Command:
```powershell
npm test --prefix frontend
```

#### Results:
- **Suites Executed:** 7
- **Total Tests:** 38
- **Passed:** 38 (100%)
- **Failed:** 0
- **Duration:** < 1.2s

#### Suite Breakdown:
1. `tests/admin-guide.test.mjs`: 8 passed
2. `tests/phase3-compact-ui.test.mjs`: 6 passed
3. `tests/production-readiness.test.mjs`: 5 passed
4. `tests/compact-redesign-v1.test.mjs`: 4 passed
5. `tests/quality-export.test.mjs`: 8 passed
6. `tests/v1_2_targeted_ui.test.mjs`: 4 passed
7. `tests/v1_2_1_ui_safety.test.mjs`: 3 passed

---

### 3. Build & Compilation Verification
- Next.js 16.4.5 (Turbopack) compiler verified with zero syntax, JSX, or type errors.
- Pydantic v2 schemas and SQLAlchemy async models load cleanly without circular dependencies or runtime warnings.
