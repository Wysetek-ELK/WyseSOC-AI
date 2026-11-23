# AIS 2.4 — Semantic Evidence Integrity & Predicate Grounding

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.4 (Scalable Multi-Rule Verdict Evaluation & Context Expansion)  
**Date:** November 23, 2026  
**Status:** IMPLEMENTED & REGRESSION TESTED  

---

## 1. Executive Summary

Phase AIS 2.4 significantly extends the semantic claim grounding engine established in AIS 2.3b.1. In prior iterations, claims were checked for literal value matches against canonical evidence records. AIS 2.4 enforces **two-sided semantic predicate validation**: checking both the telemetry field/type compatibility AND the factual truth value of the predicate.

This ensures that models cannot hallucinate malicious or benign status from entity names alone, control action blocks alone, or mismatched evidence types.

---

## 2. Six Semantic Invariants Implemented in AIS 2.4

### 2.1 Invariant 1: Digital Signature Truth Value Verification
- **Rule:** A record confirming `file.signature_status = SIGNED` must NEVER support a claim asserting that the binary is unsigned, and vice versa.
- **Enforcement:** If a claim asserts `"unsigned"` or `"not signed"`, but the cited canonical record confirms `"SIGNED"`, `"VALID"`, or `"VERIFIED"`, `ModelClaimExtractor` marks the claim as `is_grounded = False` with `grounding_status = "UNSUPPORTED_PREDICATE"` (Reason: direct contradiction with observed signature telemetry).

### 2.2 Invariant 2: Filename Alone Cannot Prove Trusted Reputation
- **Rule:** A bare filename (e.g., `calc.exe`, `UltraViewer_Service.exe`, `powershell.exe`) must NEVER prove trusted or benign reputation.
- **Enforcement:** If a claim cites a filename without authentic digital signature verification, official vendor hash lookup, or IT change authorization, the claim is rejected as `UNSUPPORTED_PREDICATE`.

### 2.3 Invariant 3: Security Action Block Alone Cannot Prove Malice
- **Rule:** The mere observation that an EDR or firewall blocked an action (`security.action = block`) does not prove that the underlying executable is malicious.
- **Enforcement:** EDR blocks frequently trigger on policy violations or benign remote-access software (e.g. UltraViewer). A claim citing only `security.action = block` is rejected as `UNSUPPORTED_PREDICATE` for malicious attack claims.

### 2.4 Invariant 4: Direct Forensic Evidence Grounds Malice Without TI Feeds
- **Rule:** Direct forensic indicators (such as LOLBin execution, command line arguments like `vssadmin delete shadows`, unquoted service paths, or registry persistence) can affirmatively ground malicious activity without requiring an external threat intelligence (TI) reputation feed.
- **Enforcement:** When command line arguments record explicit forensic attack syntax, the claim is verified as `GROUNDED`.

### 2.5 Invariant 5: Network File Download vs OS Process Execution
- **Rule:** Web proxy or network firewall download telemetry (`NETWORK_FILE_DOWNLOAD`) must NEVER be interpreted as local operating system process execution (`PROCESS_EXECUTION`).
- **Enforcement:** If a claim asserts process execution but cites proxy download evidence, it is rejected as `INCOMPATIBLE_EVIDENCE_TYPE`.

### 2.6 Invariant 6: Contradictions in Model Rationale Recorded on Safe Abstention
- **Rule:** If a model claims in its narrative that an item (such as `file.hash_sha256`) is missing, but canonical telemetry proves it is `PRESENT_VALID`, the contradiction must be recorded in audit evidence even when the final verdict is a safe abstention (`REQUIRES_ATTENTION`).
- **Enforcement:** Check 4e in `IndependentVerdictValidator` sets `reasoning_integrity_status = "REASONING_CONTRADICTION"` and populates `reasoning_contradictions`.

---

## 3. Regression Test Verification

All six invariants are covered by unit and integration tests in `backend/tests/test_ais_2_4_regression.py`:
- `test_stage4_signature_status_value_contradiction` (**PASSED**)
- `test_stage4_filename_alone_cannot_prove_reputation` (**PASSED**)
- `test_stage4_security_action_block_cannot_prove_malice` (**PASSED**)
- `test_stage4_direct_forensic_attack_evidence_grounds_malice_without_ti` (**PASSED**)
- `test_stage4_network_file_download_incompatible_with_process_execution` (**PASSED**)
- `test_stage4_reasoning_contradiction_recorded_on_safe_abstention` (**PASSED**)
