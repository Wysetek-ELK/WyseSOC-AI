# 15. TEST SUITE & SCENARIO COVERAGE

**Document Identifier:** `AV-P3-DOC-15`  
**Requirement Mapping:** `P3-REQ-08` (Regression Testing & Decision Provenance)  
**Implementation Modules:** `backend/tests/`  

---

## 1. Test Suite Architecture

Phase 3 introduces 7 dedicated test suites in addition to the 15 existing suites from Phase 1 and Phase 2:

| Test Suite | Tests | Scenarios Covered |
| :--- | :--- | :--- |
| `test_policy_compiler.py` | 4 | 9 sections order, LIVE draft rejection, SIMULATION allowance, SHA-256 digest uniqueness. |
| `test_live_simulation_parity.py` | 1 | 100% prompt content and token budget parity between Live and Simulation pipelines. |
| `test_verified_semantic_rag.py` | 2 | 6 isolation gates (status, self-exclusion, tenant, rule, temporal, deduplication), safe fallback. |
| `test_token_budgeting.py` | 1 | 7-tier priority allocation, RAG trim, optional enrichment trim, context overflow abstention. |
| `test_structured_output_and_injection.py` | 1 | Prompt injection payload neutralized by deterministic validator; fake claims rejected. |
| `test_calibration_and_evaluation.py` | 4 | Deterministic 4-way partitioning, honest metrics calculation, calibration withholding < 30 samples, API endpoint. |
| `test_phase3_integration.py` | 1 | Full end-to-end investigation with 9 sections, semantic RAG, token budgeting, validation, and audit token. |
| **Phase 3 Subtotal** | **14** | **All Phase 3 requirements validated.** |
| **Phase 2 Subtotal** | **51** | **Evidence contracts, preflight, grounding, independent validator, integration.** |
| **Phase 1 Subtotal** | **84** | **Safety gates, secrets, blind review, system monitor, hardware, dev endpoints.** |
| **Total Test Suite** | **149** | **100% Passing (0 failures, 0 regressions).** |

---

## 2. Full Regression Execution

Command: `python -m pytest tests -q`  
Result: **149 passed, 3984 warnings in 125.19s (0:02:05)**  
Status: **100% PASSING**

