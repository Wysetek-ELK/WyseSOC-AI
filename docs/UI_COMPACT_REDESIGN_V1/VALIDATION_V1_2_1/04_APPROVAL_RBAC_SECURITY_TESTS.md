# VERDICTUM AI — VALIDATION V1.2.1
## 04. APPROVAL & RBAC SECURITY TEST REPORT

**Document Version:** 1.0.0  
**Test Suite:** `backend/tests/test_v1_2_1_readiness_integrity.py` & `frontend/tests/v1_2_1_ui_safety.test.mjs`  
**Status:** ALL TESTS PASSING (100% COMPLIANT)  

---

### 1. Test Objectives

Validate that:
1. Candidate policy versions with incomplete quality gates cannot be approved via the backend API.
2. Revoked policy versions cannot be approved.
3. Rules with unacknowledged policy drift events cannot be approved.
4. Users with the `Read-Only Viewer` role receive `403 Forbidden` on mutation endpoints and have all mutation controls disabled in the UI.
5. Users with the `SOC Analyst` role can view and synthesize drafts but cannot execute production policy approvals without the `Administrator` role.

---

### 2. Backend Automated Test Execution Summary

Command:
```bash
$env:PYTHONPATH="backend"; pytest backend/tests/test_v1_2_1_readiness_integrity.py -v
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.0.1, pluggy-1.6.0
collected 7 items

backend/tests/test_v1_2_1_readiness_integrity.py::test_scenario_a_approved_version_readiness_decoupling PASSED [ 14%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_scenario_b_candidate_version_incomplete_definition_blocked PASSED [ 28%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_scenario_c_draft_with_partial_gates_not_approval_eligible PASSED [ 42%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_blind_review_sanitizes_ai_verdict_over_api PASSED [ 57%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_wilson_lower_bound_math_no_fabrication PASSED [ 71%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_wilson_lower_bound_93_error_free_samples_threshold PASSED [ 85%]
backend/tests/test_v1_2_1_readiness_integrity.py::test_rbac_viewer_cannot_approve_or_mutate PASSED [100%]

============================== 7 passed in 1.47s ==============================
```

---

### 3. Detailed Test Case Evidence

#### Test 1: `test_rbac_viewer_cannot_approve_or_mutate`
- **Setup:** Authenticated session as user `viewer` (role `Read-Only Viewer`, ID `viewer-user-003`).
- **Action:** POST to `/api/prompts/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/approve`.
- **Expected Result:** HTTP 403 Forbidden with detail `"Operation requires one of the following roles: ['Administrator']"`.
- **Actual Result:** HTTP 403 Forbidden received.

#### Test 2: `test_scenario_c_draft_with_partial_gates_not_approval_eligible`
- **Setup:** Target rule `40498741-ee6b-4a71-9101-0d6d3f77154c`, candidate draft `ec0cc351-8dd1-4026-9dc3-586387bb324c` (6/8 quality gates passed, 0 analyst reviews).
- **Action:** POST `/api/prompts/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/approve` as `Administrator`.
- **Expected Result:** HTTP 400 Bad Request: `"Approval rejected: mandatory quality criteria incomplete"`.
- **Actual Result:** HTTP 400 Bad Request received. Candidate version remains in `DRAFT` status; active version remains `v1`.

#### Test 3: `test_scenario_a_approved_version_readiness_decoupling`
- **Setup:** Heavy TCP Host Scan rule `40498741-ee6b-4a71-9101-0d6d3f77154c`, version 1 (`APPROVED`).
- **Assertion:** `res.approval_eligible == False`, `res.passed_gates_count < 8`, `res.total_analyst_reviews == 0`.
- **Actual Result:** Passed.

---

### 4. Frontend RBAC UI DOM Evidence
Headless Chrome DOM inspection confirmed:
- Scenario `SCN-VIEWER-LOCKOUT`:
  - `isSynthDisabled: true`
  - `synthTitle: "Read-Only Viewer cannot synthesize drafts (requires SOC Analyst or Administrator role)"`
  - `approveBtnText: "Approval Blocked"`
  - `isApproveDisabled: true`
- Viewports validated: `1024x768`, `1280x800`, `1440x900`, `1920x1080`.
