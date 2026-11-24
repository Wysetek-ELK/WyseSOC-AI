# AIS 2.6c — Workstream 11: Offline Regression and Security Validation Report

**Phase:** AIS 2.6c  
**Report ID:** `AIS-2.6c-REP-11`  
**Execution Timestamp:** 2026-11-24T15:12:00Z  
**Active Execution Git SHA:** `d854a5ef7471b74dab408473963a4511eab4dc66`  
**Git Branch:** `feature/phase3-compact-ui`  
**Target Environment:** Shadow Mode / Analyst Advisory Only  

---

## 1. Executive Summary

Workstream 11 conducts rigorous offline regression testing, security perimeter audit, counterfactual verification, cryptographic artifact hashing, and execution fingerprinting for Phase AIS 2.6c.

All production safety guardrails, prompt budgeting ceilings, untrusted input containment mechanisms, and three-mode evaluation pipelines were validated under automated test harnesses.

### Key Validation Outcomes:
1. **Three-Mode Pipeline Unit Tests:** 6 of 6 tests passed in `test_ais_2_6c_three_mode_and_bias_isolation.py`.
2. **Empirical Benchmark Suite:** 30 of 30 tests passed across benchmark and counterfactual test modules.
3. **Frontend Turbopack Production Build:** Next.js 16.4.5 completed in 1.1s across 32 static pages with 0 TypeScript/ESLint errors.
4. **Security Perimeter:** Delimiter escaping `<UNTRUSTED_INCIDENT_DATA>`, zero ground-truth leakage, and preflight abstention gates verified at 100% compliance.
5. **GPU Server 2 Connectivity:** Confirmed **OFFLINE** (timeout). Preflight Go/No-Go decision formally registered as `NO_GO_FOR_LIVE_GPU` with status `ENGINEERING_COMPLETE_GPU_EXPERIMENT_PENDING`.

---

## 2. Test Execution Ledger

| Test Suite / Target | Tests Executed | Passed | Failed | Status |
|---|---:|---:|---:|---|
| `test_ais_2_6c_three_mode_and_bias_isolation.py` | 6 | 6 | 0 | **PASS** |
| `test_empirical_benchmark_harness.py` | 22 | 22 | 0 | **PASS** |
| `test_ais_2_6b_counterfactual_validation.py` | 8 | 8 | 0 | **PASS** |
| `test_ais_2_6a_empirical_validation.py` | 6 | 6 | 0 | **PASS** |
| `test_ais_2_6_boundary_and_provenance.py` | 7 | 7 | 0 | **PASS** |
| `test_ais_2_4b_validator_integrity.py` | 9 | 9 | 0 | **PASS** |
| `test_ais_2_4a_tp_grounding.py` | 8 | 8 | 0 | **PASS** |
| `test_ais_2_4_regression.py` | 10 | 10 | 0 | **PASS** |
| `test_ais_2_3b_1_regression.py` | 7 | 7 | 0 | **PASS** |
| `test_ais_2_3a_integrity.py` | 4 | 4 | 0 | **PASS** |
| `test_evidence_normalization.py` | 12 | 12 | 0 | **PASS** |
| `test_evidence_preflight.py` | 9 | 9 | 0 | **PASS** |
| `test_policy_compiler.py` | 10 | 10 | 0 | **PASS** |
| `test_token_budgeting.py` | 8 | 8 | 0 | **PASS** |
| `test_independent_verdict_validator.py` | 8 | 8 | 0 | **PASS** |
| **Frontend Unit Suites (16 Suites)** | 80 | 80 | 0 | **PASS** |
| **Frontend Production Build (Next.js 16.4.5)** | 32 pages | 32 | 0 | **PASS** |

---

## 3. Security Perimeter and Guardrail Verification

### 3.1 Untrusted Delimiter Isolation
All incident metadata, raw events, and rule specifications transmitted to the LLM are encapsulated within explicit `<UNTRUSTED_INCIDENT_DATA>` delimiters. To prevent prompt injection through raw event payloads, closing tags are escaped:
```python
compact_json_clean = (
    compact_json_raw
    .replace("</UNTRUSTED_INCIDENT_DATA>", "&lt;/UNTRUSTED_INCIDENT_DATA&gt;")
    .replace("</untrusted_incident_data>", "&lt;/untrusted_incident_data&gt;")
)
```

### 3.2 Shadow Mode Closure Lock
In compliance with non-negotiable execution rules, `auto_incident_closure_allowed` is locked to `False`. Verdictum AI functions strictly as an analyst advisory intelligence system.

### 3.3 Guardrails G1 through G7
- **G1 (Missing Mandatory Evidence):** Evaluates contract requirements; demotes to `REQUIRES_ATTENTION` if critical telemetry is missing.
- **G2 (Contradictory Telemetry):** Flags conflicting network/endpoint telemetry.
- **G3 (Empty Decisive Claims):** Flags model verdicts lacking grounded claims.
- **G4 (Incomplete Detection Semantics):** Catches partial threat indicators.
- **G5 (Low Trust Score):** Enforces minimum trust score threshold (>= 7) and empirical calibration.
- **G6 (Negative FP Prohibition):** Prohibits False Positive classifications based on absence of evidence.
- **G7 (Alert Firing Alone):** Prevents equating rule trigger with confirmed maliciousness.

---

## 4. Counterfactual Validation Summary

Controlled counterfactual testing confirmed that prompt framing and policy directives alone dictate verdict proposals on identical evidence:
1. **Incident 132474210 (UltraViewer):**
   - Mode A (Neutral Baseline): Proposed `REQUIRES_ATTENTION`.
   - Mode B (CrowdStrike Policy v3): Proposed `TRUE_POSITIVE`.
   - Finding: The policy's directive ("unauthorized without change ticket -> TP") forces a TP verdict despite lack of authorization evidence.
2. **Incident 132596403 (Prisma update.exe):**
   - Mode A (Neutral Baseline): Proposed `REQUIRES_ATTENTION`.
   - Mode B (Prisma Policy v1): Proposed `TRUE_POSITIVE`.
   - Finding: The alert-trigger framing ("Suspicious file download") primes the model toward TP.

---

## 5. Artifact Manifest

The machine-readable evidence for this workstream is stored in:
- [REGRESSION_TEST_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/REGRESSION_TEST_RESULTS.json)
- [SECURITY_TEST_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/SECURITY_TEST_RESULTS.json)
- [GPU_GO_NO_GO.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/GPU_GO_NO_GO.json)
- [COUNTERFACTUAL_VALIDATION_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/COUNTERFACTUAL_VALIDATION_RESULTS.json)
- [HASH_VERIFICATION_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/HASH_VERIFICATION_RESULTS.json)
- [EXECUTION_BUILD_FINGERPRINT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EXECUTION_BUILD_FINGERPRINT.json)
- [REQUEST_RESPONSE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/REQUEST_RESPONSE_MANIFEST.json)
