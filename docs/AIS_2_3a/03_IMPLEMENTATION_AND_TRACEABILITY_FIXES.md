# AIS 2.3a — Implementation & Traceability Fixes Report

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3a (Runtime Evidence, Guardrail & Accuracy Integrity Correction)  
**Date:** November 23, 2026  
**Status:** IMPLEMENTED & UNIT-TESTED  

---

## 1. Executive Summary

Phase AIS 2.3a delivered targeted code corrections to eliminate runtime evidence delivery drops, token underestimation drift, citation resolution failures, validator runtime errors, and traceability omissions across the Verdictum AI decision pipeline.

All modifications strictly preserve:
- Existing three-tab Agent Intelligence Studio UI architecture.
- Approved Detection Policy v7 and Draft Candidate Policy v8.
- Double-blind analyst workflow protections.
- Zero-fabrication empirical truth constraints.

---

## 2. Inventory of Code Modifications

### 2.1 Evidence Normalization: Canonical Field Aliasing
- **File:** `backend/app/services/evidence_normalization_service.py`
- **Root Cause:** FortiSIEM events store process executable names under `File Name` or `fileName`. `FIELD_MAPPINGS` mapped this solely to `process.file_name`. The evidence contracts for `MALWARE_EXECUTION` and `NETWORK_THREAT` archetypes expected `process.name` or `file.name`.
- **Fix:** In `_extract_from_dict`, when `File Name` / `fileName` is processed, canonical field aliases are generated:
  - If mapped to `process.file_name`, secondary records for `process.name` and `file.name` are also emitted into `EvidenceNormalizationResult`.
  - When `Parent File Name` is processed, secondary records for `process.parent_name` are emitted.
- **Result:** Downstream consumers (policy compilers, evidence contracts, and LLM prompts) find required process attributes regardless of whether they look for `process.name`, `process.file_name`, or `file.name`.

### 2.2 Evidence Compaction: Lineage Preservation & Priority Scoring
- **File:** `backend/app/services/evidence_compaction_service.py`
- **Root Cause:** `DO_NOT_COLLAPSE_FIELDS` omitted `process.name`, `process.file_name`, and `file.name`. Furthermore, `score_relevance` and `is_core_candidate` used strict equality against contract fields, failing to recognize alias relationships (`process.name` $\leftrightarrow$ `process.file_name`).
- **Fix:**
  1. Added `"process.name"`, `"process.file_name"`, `"process.parent_name"`, and `"file.name"` to `DO_NOT_COLLAPSE_FIELDS`.
  2. Updated `score_relevance` to give 1,000 priority points whenever any alias matches a contract field.
  3. Added process lineage fields to Priority 3 Core SOC Identifiers (+300 points).
  4. Updated `is_core_candidate` to guarantee that process lineage and binary names are retained in the core candidate pool and never evicted as low-priority auxiliary fields.
- **Result:** Process binary names and execution parameters are guaranteed to reach the model-facing payload.

### 2.3 Token Budgeting: Calibrated BPE Counting
- **File:** `backend/app/services/token_budget_service.py`
- **Root Cause:** `estimate_tokens` used naive `len(text) // 4`. Structured SOC telemetry (hex hashes, Windows file paths, JSON quotes, ChatML delimiters) has a higher token density (~3.0–3.2 chars/token in BPE), causing a 25–33% underestimation of prompt token length and encroaching on the completion budget.
- **Fix:** Replaced naive heuristic with `ModelTokenizerService.count_tokens(text)`, which uses `tiktoken` calibrated to `cl100k_base` with JSON overhead correction.
- **Result:** Accurate token counting guarantees prompt payloads remain $\le 3,328$ tokens, reserving $\ge 768$ completion tokens within the 4,096 context window.

### 2.4 Model Claim Extraction: Resilient Citation Resolution
- **File:** `backend/app/services/model_claim_extractor.py`
- **Root Cause:** In Prisma SASE incidents, Qwen proposed `FALSE_POSITIVE` citing `EV-...-TOP-file_name` or field `file_name`. The extractor rejected citations if the ID had slight casing or prefix differences, or if the field was recorded as `process.file_name` instead of `file_name`.
- **Fix:**
  1. Implemented resilient citation alias resolution in `ground_claims`: if an exact evidence ID is not found, the extractor checks for canonical records with matching values and compatible field names.
  2. Implemented field alias compatibility: `process.name` $\leftrightarrow$ `process.file_name` $\leftrightarrow$ `file.name` $\leftrightarrow$ `process` are treated as compatible for value verification.
  3. Extracted `ground_claims` as a dedicated modular method on `ModelClaimExtractor`.
- **Result:** Grounded citations reference valid canonical records, eliminating synthetic rejection flags while maintaining strict hallucination detection.

### 2.5 Independent Verdict Validator: UnboundLocalError Hotfix
- **File:** `backend/app/services/independent_verdict_validator.py`
- **Root Cause:** If model output formatting was invalid but raw confidence was valid, `action_directive` was accessed before assignment on line 106, raising an `UnboundLocalError`.
- **Fix:** Initialized `action_directive` with a safe default string at function entry:
  `action_directive = "Invalid model verdict output format." if invalid_output_flag else "Verdict verified against canonical evidence contract."`.
- **Result:** Eliminates unhandled runtime exceptions in the validation pipeline.

### 2.6 Pipeline Traceability: Metadata Population
- **File:** `backend/app/services/verdict_pipeline.py`
- **Root Cause:** Several early exit paths (preflight abstention, token budget overflow, policy governance gates) returned dictionary responses lacking `rule_id`, `rule_name`, `policy_version_id`, `policy_version_number`, and `policy_status`.
- **Fix:** Populated `rule_id`, `rule_name`, `policy_version_id`, `policy_version_number`, and `policy_status` across all return branches in `run_shared_verdict_pipeline`.
- **Result:** All verdict responses provide complete end-to-end traceability for downstream dashboards, audit logs, and reports.

---

## 3. Test Suite Verification

### 3.1 New Dedicated Integrity Test Suite
- **File:** `backend/tests/test_ais_2_3a_integrity.py`
- **Tests Implemented (4/4 Passed):**
  1. `test_canonical_field_aliasing_for_process_binary`: Verifies both `process.name` and `process.file_name` records are produced from raw FortiSIEM events.
  2. `test_compaction_preservation_of_process_lineage`: Verifies process binary names receive $\ge 1,300$ relevance points and are preserved during severe budget compaction.
  3. `test_claim_grounding_resilient_citation_resolution`: Verifies model claims citing `file_name` ground successfully against canonical `process.file_name` records.
  4. `test_token_budget_bpe_calibrated_bounds`: Verifies that a real historical CrowdStrike incident prompt is accurately budgeted $\le 3,328$ tokens.

### 3.2 Regression Suite Summary
- **Backend Tests:** **64 passed** out of 64 collected (0 failures).
- **Frontend Tests:** **85 passed** out of 85 collected (0 failures).
- **Combined Test Health:** **149 passed** out of 149 (100% pass rate).
