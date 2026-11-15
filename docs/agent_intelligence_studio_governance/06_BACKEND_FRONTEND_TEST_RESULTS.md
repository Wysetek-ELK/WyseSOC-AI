# Report 06 — Backend & Frontend Test Results

## 1. Automated Test Summary

| Test Suite | Tests Executed | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- |
| `test_policy_version_governance.py` | 5 | 5 | 0 | **100% PASSED** |
| `test_actual_prompt_inspector.py` | 13 | 13 | 0 | **100% PASSED** |
| `test_prompt_studio.py` | 1 | 1 | 0 | **100% PASSED** |
| **Total Backend Tests** | **19** | **19** | **0** | **100% PASSED** |

---

## 2. Test Suite Details

### 2.1 `test_policy_version_governance.py`
1. `test_revocation_lifecycle_and_audit`:
   - Validates that revoking an approved version requires a substantive reason.
   - Confirms `status="REVOKED"`, `revoked_by_user_id`, `revoked_at`, `revocation_reason`, and `previous_status="APPROVED"` are accurately stored.
   - Verifies that parent `RulePrompt.ai_execution_suspended` is atomically set to `True`.
2. `test_rollback_rejection_on_revoked_and_draft`:
   - Validates that `rollback_version` hard-rejects rollback to a `REVOKED` version.
   - Validates that `rollback_version` hard-rejects rollback to a `DRAFT` version.
3. `test_semantic_mismatch_detection`:
   - Confirms `detect_semantic_mismatch` flags endpoint malware keywords on a `NETWORK_SCAN` rule.
   - Confirms network sweep instructions pass without false alerts.
4. `test_policy_eligibility_service_evaluation`:
   - Tests `evaluate_eligibility` across `POLICY_REVOKED`, `RULE_SUSPENDED`, and `DRAFT_NOT_APPROVED`.
   - Confirms draft candidate is permitted in simulation mode but blocked in production mode.
5. `test_verdict_pipeline_intercepts_suspended_rule`:
   - Confirms `run_shared_verdict_pipeline` catches suspended rules, bypasses LLM dispatch, records safe abstention, and assigns `REQUIRES_ATTENTION`.

### 2.2 `test_actual_prompt_inspector.py` & `test_prompt_studio.py`
- Confirms SHA-256 payload integrity, canonical JSON serialization, and prompt capture work in complete parity with the new governance lifecycle.
- Confirms rollback to an approved archived baseline works regression-free.

---

## 3. Frontend TypeScript & Production Build

- **Command:** `npm --prefix frontend run build`
- **TypeScript Typecheck:** 0 errors
- **Static & Dynamic Routes:** 32 of 32 pages compiled successfully
- **Artifact Output:**
  ```
  ✓ Compiled successfully in 1902ms
  Finished TypeScript in 4.7s ...
  Generating static pages using 11 workers (32/32) in 1887ms
  Finalizing page optimization ...
  ```

---
*Report Completed on 2026-11-15.*
