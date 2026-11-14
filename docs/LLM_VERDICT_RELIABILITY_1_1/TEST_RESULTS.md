# Verdictum AI — LLM Verdict Reliability 1.1: Test Results

**Date:** 2026-11-14  
**Test Suite:** Reliability & Guardrail Regression Suite  
**Test Runner:** pytest 9.0.1 (Python 3.13.13, Windows)  

---

## 1. Summary of Execution Results

| Test Module | Tests | Passed | Failed | Skipped | Execution Time | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `backend/tests/test_verdict_reliability_1_1.py` | 10 | 10 | 0 | 0 | 2.25s | New Reliability 1.1 Invariants |
| `backend/tests/test_policy_compiler.py` | 4 | 4 | 0 | 0 | 0.81s | System prompt & JSON schema compilation |
| `backend/tests/test_structured_output_and_injection.py` | 1 | 1 | 0 | 0 | 0.28s | Untrusted boundary & injection defense |
| `backend/tests/test_independent_verdict_validator.py` | 9 | 9 | 0 | 0 | 1.60s | Scenarios 21–34 deterministic validation |
| `backend/tests/test_evidence_contracts.py` | 9 | 9 | 0 | 0 | 0.95s | Contract approval & schema validation |
| `backend/tests/test_evidence_normalization.py` | 11 | 11 | 0 | 0 | 0.89s | Canonical evidence normalization |
| `backend/tests/test_token_budgeting.py` | 1 | 1 | 0 | 0 | 0.64s | Priority P1–P7 budgeting & compaction |
| `backend/tests/test_ground_truth_isolation.py` | 1 | 1 | 0 | 0 | 0.32s | Zero ground-truth leakage assertion |
| `backend/tests/test_agentic_nomenclature.py` | 3 | 3 | 0 | 0 | 0.37s | Nomenclature & attribute sanitization |
| **Total Core Reliability Suite** | **49** | **49** | **0** | **0** | **7.11s** | **100% Pass Rate** |

---

## 2. Detailed Test Case Coverage for `test_verdict_reliability_1_1.py`

### Test 1: Bidirectional Evidence ID Synchronization & ClaimType Enum
- **Target:** `app.schemas.evidence_claim.ModelSupportingClaim`, `app.schemas.verdict_intelligence.ClaimType`
- **Result:** PASSED
- **Verification:** Verified that providing `cited_evidence_ids` automatically populates `evidence_ids` and vice-versa via Pydantic after-validators. Standardized claim types (`TELEMETRY_OBSERVATION`, `PROCESS_EXECUTION`, `NETWORK_CONNECTION`, etc.) resolve correctly.

### Test 2: Untrusted Incident Data Boundary Tags (`<UNTRUSTED_INCIDENT_DATA>`)
- **Target:** `app.services.model_provider.openai_compatible`
- **Result:** PASSED
- **Verification:** Verified that serialized incident JSON sent in the user prompt is strictly enclosed inside `<UNTRUSTED_INCIDENT_DATA>\n...\n</UNTRUSTED_INCIDENT_DATA>`, aligning user prompt construction with System Prompt Section 10 boundaries.

### Test 3: Large Event Counts and Long Commands Preserved in Allowlist
- **Target:** `app.services.model_payload_allowlist.build_model_facing_payload`
- **Result:** PASSED
- **Verification:** Generated a 12-event incident with a 1,500-character PowerShell command line. Confirmed all 12 events were retained (bypassing the former 2-event cap) and the command line was preserved without premature truncation at 180 characters.

### Test 4: Rejection of Decisive FP Based Solely on RFC-1918 / Service Account
- **Target:** `app.services.independent_verdict_validator.IndependentVerdictValidator`
- **Result:** PASSED
- **Verification:** Model proposed `FALSE_POSITIVE` claiming "Internal RFC-1918 traffic from service account svc_app_pool, appears normal and routine."
- **Outcome:** Decisive verdict was strictly rejected and forced to `REQUIRES_ATTENTION` with reason code `FP_CRITERIA_UNSATISFIED` and confidence display set to 0.0.

### Test 5: Acceptance of Decisive FP Backed by Affirmative Authorization
- **Target:** `app.services.independent_verdict_validator.IndependentVerdictValidator`
- **Result:** PASSED
- **Verification:** Model proposed `FALSE_POSITIVE` citing scheduled backup execution under change ticket `CHG-9842`.
- **Outcome:** Accepted as `FALSE_POSITIVE` (`is_decisive_accepted = True`, status `VALIDATED`, reason code `EVIDENCE_VALIDATED`, confidence display 92.0).

### Test 6: Safe Downgrade When Regex Schema Recovery Was Applied
- **Target:** `app.services.model_provider.openai_compatible._regex_fallback_extract`
- **Result:** PASSED
- **Verification:** Fed malformed JSON missing closing braces to the regex fallback extractor. Confirmed `_schema_recovery_applied = True` and `confidence = 0.0`. Confirmed decisive TP/FP proposal forced to `REQUIRES_ATTENTION` with `validation_status = "INVALID_SCHEMA"`.

### Test 7: Rejection of Decisive Verdict When Structured Claims Are Absent
- **Target:** `app.services.model_claim_extractor.ModelClaimExtractor`, `IndependentVerdictValidator`
- **Result:** PASSED
- **Verification:** Model proposed `TRUE_POSITIVE` with `"supporting_claims": []`. Confirmed that claim extraction did not scrape entities from `reason` to bypass the claim requirement. Total grounded claims remained 0, forcing downgrade to `REQUIRES_ATTENTION` (`TP_CRITERIA_UNSATISFIED`).

### Test 8: Rejection Under Contradictory Telemetry (External C2 on Loopback)
- **Target:** `app.services.independent_verdict_validator.IndependentVerdictValidator`
- **Result:** PASSED
- **Verification:** Incident telemetry had all traffic on `127.0.0.1`. Model asserted external C2 communication.
- **Outcome:** Contradiction detected; decisive TP rejected and forced to `REQUIRES_ATTENTION` (`EVIDENCE_CONTRADICTION`).

### Test 9: Zero Confidence Default When Model Omits Confidence
- **Target:** `app.services.model_provider.openai_compatible`
- **Result:** PASSED
- **Verification:** When model response omitted `confidence`, verified default is 0.0 rather than 90.0 or 75.0.

### Test 10: Fail-Closed Context Window Overflow Abstention
- **Target:** `app.services.token_budget_service.TokenBudgetService`
- **Result:** PASSED
- **Verification:** Configured tight token budget (512 tokens available) while compiled mandatory core exceeded 1,500 tokens. Verified `can_proceed_to_inference = False` and fail-closed abstention triggered without naive text slicing.

---

## 3. Provenance & Hardware Notice

> [!IMPORTANT]
> **OFFLINE VALIDATION NOTICE:**
> - All 49 tests were executed deterministically in an offline Python environment without requiring active GPU servers, live vLLM instances, or Docker containers.
> - No empirical model accuracy (precision/recall on real production threats) is claimed from these unit and integration tests.
> - Empirical accuracy benchmarking is scheduled for Phase 9 on Server 2 GPU hardware against the certified 1,000-incident analyst ground-truth dataset.

---
*End of Test Results report.*

