# WyseSOC AI — Automated Test Results Report

**Document:** `09_AUTOMATED_TEST_RESULTS.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Test Suite:** `backend/tests/test_evidence_integrity_audit.py`  
**Regression Suites:** 7 Test Suites (72 Tests Total)  
**Execution Environment:** Windows / Python 3.12 / pytest 8.3.4  
**Status:** 100% PASSED (72/72)  

---

## 1. Executive Summary

This report documents the execution and verification of the mandatory automated test suite (Tests T01 through T25) specifically developed to validate the end-to-end evidence integrity, field normalization, type-aware comparison, and false-positive gating subsystems.

All 25 mandatory tests passed cleanly. Additionally, the complete regression test suite comprising 72 tests across 7 test suites executed with a 100% pass rate.

---

## 2. Mandatory Test Suite Results Matrix (T01 – T25)

| Test ID | Scenario | Input Fixture | Expected Outcome | Actual Outcome | Status |
|---|---|---|---|---|---|
| **T01** | Required evidence in canonical fields | Canonical JSON with `network.source_ip`, `event.timestamp` | Recognized with `DIRECT` provenance | Normalized directly to canonical schema | **PASS** |
| **T02** | Evidence in verified alias fields | Incident #176061 aliases (`srcip`, `dstip`, `catdesc`, `url`) | Normalized to canonical schema paths | Correctly resolved to canonical fields | **PASS** |
| **T03** | Nested JSON evidence | Multi-level nested dictionary `{"network": {"source": {"ip": ...}}}` | Recursively extracted to dot-path | Extracted dot-paths properly | **PASS** |
| **T04** | Flattened JSON & raw syslog | Raw FortiGate syslog string `srcip=... catdesc=...` | Regex KV extracted and mapped | Parsed KV tokens into canonical evidence | **PASS** |
| **T05** | Missing source field | Payload omitting optional/conditional fields | Classified as `NOT_IN_SOURCE` | Tracked as `NOT_IN_SOURCE` | **PASS** |
| **T06** | Field exists but is not mapped | Raw payload with unrecognized custom attribute | Identified as unmapped, preserved in `unmapped_fields` | Preserved in `unmapped_fields`, status `NOT_MAPPED` | **PASS** |
| **T07** | Field dropped from AI context | Field pruned during token compaction | Tracked as `CONTEXT_OMITTED` | Accurately recorded as `CONTEXT_OMITTED` | **PASS** |
| **T08** | Valid evidence and model response | Grounded claims citing valid evidence IDs | Evidence validation passes, high grounding ratio | 100% Grounding ratio, validation accepted | **PASS** |
| **T09** | Hallucinated model evidence | Model cites unobserved IP `203.0.113.99` | Rejected with `CLAIM_UNGROUNDED` | Claim neutralized, grounding penalized | **PASS** |
| **T10** | Model value differs from source | Model asserts IP `192.0.2.2` when source is `192.0.2.1` | Flagged as `EVIDENCE_VALUE_MISMATCH` | Detected value mismatch, claim rejected | **PASS** |
| **T11** | HTTP status string vs integer | Model asserts string `"200"` for integer `200` | Matched via type-aware comparison | Type-aware comparator matched values | **PASS** |
| **T12** | Conflicting values across events | Multiple events with distinct source IPs | Conflict preserved without overwriting | Flagged `FIELD_CONFLICT`, preserved candidates | **PASS** |
| **T13** | Benign claim without evidence | Model claims benign routine traffic without proof | Rejected, downgraded to `REQUIRES_ATTENTION` | Gating prevented unsubstantiated FP | **PASS** |
| **T14** | Genuine insufficient evidence | Mandatory core fields missing from telemetry | Model abstains with `REQUIRES_ATTENTION` | Safe abstention approved | **PASS** |
| **T15** | Validated false-positive scenario | Verified scanner IP with matching scan telemetry | False-positive criteria approved | Decisive `FALSE_POSITIVE` accepted | **PASS** |
| **T16** | Re-evaluation with stale cache | Updated raw logs re-evaluated against cached record | Cache bypassed, fresh normalization applied | Reflected updated telemetry correctly | **PASS** |
| **T17** | Existing unrelated incident type | Incident with `BRUTE_FORCE` rule | No regression in existing rule archetypes | Brute force archetype evaluated cleanly | **PASS** |
| **T18** | Cross-tenant incident access | Evaluated cross-tenant incident access attempt | Access denied, tenant isolation preserved | Strict tenant barrier maintained | **PASS** |
| **T19** | Malformed LLM JSON response | Incomplete and markdown-wrapped JSON responses | Recovered or degraded safely to `REQUIRES_ATTENTION` | Handled gracefully without crash | **PASS** |
| **T20** | Repeated re-evaluation | Multiple rapid re-evaluations on same incident | Audit history preserved without corrupted duplicates | Appended clean versioned audit logs | **PASS** |
| **T21** | URL normalization edge cases | Scheme/host normalization vs path traversal | Scheme/host matched; path traversal rejected | Root slash matched; path traversal blocked | **PASS** |
| **T22** | Prompt injection in raw evidence | Ingested event containing `IGNORE PREVIOUS INSTRUCTIONS` | Escaped and quarantined as untrusted data | Neutralized injection attempt | **PASS** |
| **T23** | Parser mapping collision | Specific `src_ip` vs generic `ip` | Deterministic precedence enforced | Specific alias took precedence over generic | **PASS** |
| **T24** | Event aggregation across records | Aggregation of 10 firewall drop events | Preserved event IDs and time range provenance | Grouped records without cross-event leakage | **PASS** |
| **T25** | Missing or malformed source events | Corrupted payloads with missing brackets/tokens | Safe degradation without uncaught exception | Handled safely, returned partial evidence | **PASS** |

---

## 3. Regression Test Suite Summary

The remediation was verified against the entire repository regression test suite to ensure zero unintended side-effects across token budgeting, preflight validation, grounding, and compaction:

```text
============================== test session starts ==============================
platform win32 -- Python 3.12.7, pytest-8.3.4, pluggy-1.5.0
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent
configfile: pytest.ini
collected 72 items

backend\tests\test_evidence_integrity_audit.py ......................... [ 34%]
backend\tests\test_evidence_normalization.py ...........                  [ 50%]
backend\tests\test_evidence_preflight.py ......                          [ 58%]
backend\tests\test_independent_verdict_validator.py .........            [ 70%]
backend\tests\test_evidence_grounding.py ..........                      [ 84%]
backend\tests\test_evidence_compaction_and_chunking.py ......            [ 93%]
backend\tests\test_context_window_8k_16k.py .....                        [100%]

============================== 72 passed in 9.13s ==============================
```

### Verification Highlights
- **Audit Suite (`test_evidence_integrity_audit.py`):** 25 passed in 2.91s.
- **Evidence Normalization Suite (`test_evidence_normalization.py`):** 11 passed in 0.44s.
- **Evidence Preflight Suite (`test_evidence_preflight.py`):** 6 passed in 0.38s.
- **Independent Verdict Validator Suite (`test_independent_verdict_validator.py`):** 9 passed in 0.65s.
- **Evidence Grounding Suite (`test_evidence_grounding.py`):** 10 passed in 1.12s.
- **Compaction and Chunking Suite (`test_evidence_compaction_and_chunking.py`):** 6 passed in 1.48s.
- **Context Window 8K/16K Suite (`test_context_window_8k_16k.py`):** 5 passed in 1.25s.
- **Total Pass Rate:** 100% (72/72 tests passing). Zero regressions.
