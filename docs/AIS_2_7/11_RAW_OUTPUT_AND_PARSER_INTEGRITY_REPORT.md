# AIS 2.7 — Workstream 11: Raw Output & Parser Integrity Report

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [RAW_RESPONSE_INTEGRITY_RESULTS.json](RAW_RESPONSE_INTEGRITY_RESULTS.json), [PARSER_ERROR_REGISTER.json](PARSER_ERROR_REGISTER.json), [VALIDATOR_TRANSFORMATION_LEDGER.json](VALIDATOR_TRANSFORMATION_LEDGER.json)

## 1. Raw Model Formatting & Parser Fidelity

| Metric | Observed Result |
|---|---|
| Benchmark GPU calls evaluated | `40 / 40` (`20` Mode A + `20` Mode B) |
| HTTP 200 OK & `vllm_response_id` present | `40 / 40 (100.0%)` |
| `finish_reason == "stop"` (no token truncation) | `40 / 40 (100.0%)` |
| Pure JSON without markdown fences | `20 / 40 (100.0%)` |
| `parse_success == True` and `schema_valid == True` | `40 / 40 (100.0%)` |
| Parser errors logged | `0` |

## 2. Mode C Validator Transformations Summary

Across the `20` Mode B outputs fed into Mode C (`0` GPU calls):

- **Mode B verdicts changed by Validator:** `10 / 20` (`9` `FALSE_POSITIVE`/`TRUE_POSITIVE` verdicts downgraded to `REQUIRES_ATTENTION` + `1` `TRUE_POSITIVE` on `132527297` downgraded = `10` total changed!).
- **Validation Status Counts:** `{"ABSTENTION_WITH_CONTRADICTION": 7, "INSUFFICIENT_EVIDENCE": 3, "REJECTED": 7, "VALIDATED": 3}`
- **Trust Score Below Decision Threshold (`< 7`):** `20 / 20 (100.0%)` -> Every single incident receives `effective_trust_verdict = REQUIRES_ANALYST_ATTENTION`.

**Critical Diagnostic Takeaway:** `Qwen/Qwen2.5-7B-Instruct-AWQ` demonstrates `100%` structural JSON compliance (`40/40`) and `0` parser failures. Thus, all downstream accuracy failures documented in Workstreams 12–18 reflect genuine **reasoning, instruction-following, and factual-grounding failure**, NOT syntax or transport breakage.
