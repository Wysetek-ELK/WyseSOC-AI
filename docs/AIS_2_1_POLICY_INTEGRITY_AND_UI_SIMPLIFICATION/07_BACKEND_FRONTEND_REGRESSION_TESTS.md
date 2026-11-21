# 07. BACKEND AND FRONTEND REGRESSION TEST MATRIX

## Verdictum AI — Agent Intelligence Studio 2.1
**Powered by WYSETEK Systems**

---

## 1. Regression Test Execution Summary

The regression testing suite validates all changes introduced in AIS 2.1 across backend services, API endpoints, database models, frontend components, and user workflows.

### 1.1 Test Suite Results Overview

| Test Suite | Focus Area | Total Tests | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `test_ais_evaluation_tracking.py` | AI Evaluation Tracking Service, Status Resolver, Batch Inference, Isolation | 20 | 20 | 0 | 10.00s |
| `test_ais_heavy_tcp_e2e.py` | Target Rule `Heavy TCP Host Scan` End-to-End Governance & G1-G8 | 14 | 14 | 0 | 12.54s |
| `Next.js Production Build` | TypeScript compilation, Page routing, Component bundling, Zero regressions | Full App | PASS | 0 | ~18s |

---

## 2. Detailed Backend Test Suite: `test_ais_evaluation_tracking.py`

This suite validates the comprehensive state machine and API behavior for AI Evaluation Tracking:

| Test ID | Test Name | Invariants Verified | Result |
| :--- | :--- | :--- | :---: |
| **TEST-01** | `test_01_not_evaluated_status_when_no_execution_exists` | Incidents without inference records report `NOT_EVALUATED` rather than vanishing from the table. | **PASS** |
| **TEST-02** | `test_02_evaluated_decisive_status_for_valid_tp_or_fp_inference` | Valid True Positive or False Positive LLM predictions map to `EVALUATED_DECISIVE`. | **PASS** |
| **TEST-03** | `test_03_abstained_status_for_requires_attention` | Verdicts returning `REQUIRES_HUMAN_ATTENTION` map to `ABSTAINED`. Not confused with missing inference. | **PASS** |
| **TEST-04** | `test_04_validation_rejected_status_when_validator_rejects_output` | Independent validator rejection maps to `VALIDATION_REJECTED`. Never accepted as decisive. | **PASS** |
| **TEST-05** | `test_05_evaluation_failed_status_on_timeout_or_error` | Inference timeouts or pipeline errors map to `EVALUATION_FAILED`. | **PASS** |
| **TEST-06** | `test_06_mock_or_simulation_output_marked_is_mock_only_and_excluded` | Mock or simulation outputs marked `is_mock_only` are strictly excluded from production empirical accuracy. | **PASS** |
| **TEST-07** | `test_07_policy_version_isolation_v7_does_not_satisfy_v8` | Policy version isolation: an evaluation under v7 does not satisfy v8 evaluation status. | **PASS** |
| **TEST-08** | `test_08_status_list_filtering_by_status_policy_version_and_search` | Filter pills (`ALL`, `NOT_EVALUATED`, `EVALUATED_DECISIVE`, `ABSTAINED`, etc.) filter correctly. | **PASS** |
| **TEST-09** | `test_09_summary_api_count_accuracy_no_double_counting` | Summary counts equal the sum of distinct incident statuses; zero double counting. | **PASS** |
| **TEST-10** | `test_10_evaluation_history_preserves_all_attempts_in_chronological_order` | Chronological evaluation history is fully preserved across re-runs. | **PASS** |
| **TEST-11** | `test_11_controlled_batch_inference_evaluates_only_eligible_missing_incidents` | Batch evaluation only executes against eligible, missing or failed incidents. | **PASS** |
| **TEST-12** | `test_12_controlled_batch_inference_graceful_cancellation` | Cancellation signals halt batch processing cleanly without corrupting database state. | **PASS** |
| **TEST-13** | `test_13_double_blind_protection_unreviewed_incident_masks_verdicts` | Unreviewed incidents mask AI predictions for non-administrative analysts. | **PASS** |
| **TEST-14** | `test_14_authorized_admin_can_inspect_full_evaluation_details` | Authorized administrators can inspect full unmasked inference details. | **PASS** |
| **TEST-15** | `test_15_non_admin_cannot_trigger_batch_inference` | RBAC: Non-admin users are rejected from triggering batch evaluations (HTTP 403). | **PASS** |
| **TEST-16** | `test_16_tenant_isolation_enforced` | Multi-tenant customer scoping prevents cross-customer data leakage. | **PASS** |
| **TEST-17** | `test_17_invalid_rule_uuid_returns_404` | Non-existent rule UUID returns 404 with fail-safe error details. | **PASS** |
| **TEST-18** | `test_18_missing_incident_id_returns_404` | Non-existent incident ID returns 404 cleanly. | **PASS** |
| **TEST-19** | `test_19_re_evaluating_incident_creates_new_history_and_updates_latest_status` | Re-evaluating an incident updates its latest status while retaining previous attempts. | **PASS** |
| **TEST-20** | `test_20_empirical_accuracy_summary_not_measurable_when_zero_decisive_comparisons` | When zero decisive comparisons exist, empirical accuracy correctly displays as not measurable. | **PASS** |

---

## 3. End-to-End Target Rule Suite: `test_ais_heavy_tcp_e2e.py`

Validates that rule `Heavy TCP Host Scan On Fixed Port` (`40498741-ee6b-4a71-9101-0d6d3f77154c`) adheres to all governance policies:

| Test ID | Test Scenario | Expected Outcome | Result |
| :--- | :--- | :--- | :---: |
| **E2E-01** | Rule Metadata & Prompt Association | Rule binds to `rule_prompts` container without orphan errors. | **PASS** |
| **E2E-02** | Approved Policy Version v7 Historical Integrity | v7 is marked `APPROVED`, `was_ever_approved=True`, content immutable. | **PASS** |
| **E2E-03** | Candidate Draft Version v8 Isolation | v8 is marked `DRAFT`, not conflated with active baseline. | **PASS** |
| **E2E-04** | Active Policy Binding Recovery Endpoint | Admin activation endpoint validates G1–G8, archives previous approved, un-suspends AI. | **PASS** |
| **E2E-05** | Production Readiness Gate G8 Hard Gate Enforcement | Requires ≥100 evaluations, ≥95% accuracy, ≥99% precision, ≥95% recall before unassisted auto-close. | **PASS** |
| **E2E-06** | Evidence Contract Mapping | Normalized evidence schema verified against raw FortiSIEM event payloads. | **PASS** |
| **E2E-07** | Double-Blind Review Queue Isolation | Analysts cannot view model inference prior to ground-truth labeling. | **PASS** |
| **E2E-08** | Multi-Tenant Incident Visibility | Global administrators view incidents across `GDC_NOC` and `Demo-SOC`. | **PASS** |
| **E2E-09** | Diagnostic Issue Normalization | Decoupled SIEM status, prompt lifecycle status, and runtime suspension reasons. | **PASS** |
| **E2E-10** | Safe Rollback Protection | Reverting active policy requires admin approval and records audit event. | **PASS** |
| **E2E-11** | Prompt Injection Defense | Untrusted incident fields cannot escape schema boundary or alter prompt instructions. | **PASS** |
| **E2E-12** | Local AWQ Inference Execution | Real Local AWQ model executes deterministically against test payloads. | **PASS** |
| **E2E-13** | Quality Gates G1–G7 Evaluation | Semantic completeness, indicators, evidence contract, and archetype alignment verified. | **PASS** |
| **E2E-14** | Audit Log Trail | All policy promotions, activations, and reviews produce immutable audit events. | **PASS** |

---

## 4. Frontend Compilation & Type Safety Verification

- Command: `npm run build`
- Framework: Next.js 16.4.5 with Turbopack & React 19
- TypeScript Validation: Zero syntax errors, zero type errors, strict mode compliant.
- Component Integration:
  - `page.tsx`: Consolidated 3 operational tabs (`incidents`, `ai_evaluation`, `accuracy`) + 1 administrative `settings` control.
  - `ReviewIncidentsWorkbench.tsx`: Direct review queue without internal mode switches. Canonical evidence mapping with incident metadata fallback.
  - `AiTestWorkbench.tsx`: 6 summary cards, tracking table with filter pills, integrated test workbench.
  - `AccuracyLearningSummary.tsx`: Real-time empirical accuracy tracking with ground-truth drilldowns.
  - `AgentIntelligenceStudioOverview.tsx`: Integrated seamlessly into Settings Module 0.
