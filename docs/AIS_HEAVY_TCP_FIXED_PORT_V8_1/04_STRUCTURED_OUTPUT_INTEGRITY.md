# 04 — Structured LLM Output Integrity Report

**Implemented In:** [openai_compatible.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/openai_compatible.py), [policy_compiler_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_compiler_service.py), [verdict_pipeline.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_pipeline.py)

---

## 1. Compact Structured Output Contract (Section 11)

V8.1 streamlined the Section 11 wire schema to eliminate redundant token bloat (removing duplicate `evidence_ids` alongside `cited_evidence_ids`, capping concise `supporting_claims` at 3 and `analyst_questions` at 2) while strictly preserving every mandatory field required by downstream validators, APIs, and UI consumers:
- `incident_id` (strictly cross-checked against evaluated incident; mismatch → `INVALID_INCIDENT_REF`)
- `rule_id` (strictly cross-checked against allowed canonical UUID/event_type/name; mismatch → `INVALID_RULE_REF`)
- `verdict` (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `INSUFFICIENT_EVIDENCE`, or `REQUIRES_ATTENTION`)
- `confidence` (strictly validated `0.0–100.0`, NaN rejected → `INVALID_CONFIDENCE`)
- `reason`, `supporting_claims`, `supporting_evidence`, `contradictory_evidence`, `missing_evidence`, `recommended_action`, `analyst_questions`

---

## 2. Anti-Silent-Truncation & Output Status Safeguards

Prior to V8.1, `_repair_truncated_json` silently closed truncated JSON strings (e.g., V8's `5/6` runs that hit `512/512` tokens) and returned `validation_status = "VALID"`. V8.1 eliminated silent truncation acceptance across **all rules**:

| Validation Status | Trigger Condition | Enforced Safety Outcome | Trust Score Impact |
| :--- | :--- | :--- | :--- |
| **`TRUNCATED_OUTPUT`** | vLLM `choice.finish_reason == "length"` OR `_repair_truncated_json` applied (`_truncated_output = True`) | **NEVER accepted as decisive TP/FP**; forced `REQUIRES_ATTENTION`, `confidence = 0.0`, `OUTPUT_TRUNCATED` reason code, `SAFE_ABSTENTION_AFTER_TRUNCATED_OUTPUT` | Capped at **`<= 4/10`** with explicit limitation note |
| **`INVALID_MODEL_OUTPUT` / `SCHEMA_INVALID`** | Unparseable output, missing required schema keys, `INVALID_INCIDENT_REF`, `INVALID_RULE_REF`, `INVALID_CONFIDENCE`, or malformed regex recovery | Forced `REQUIRES_ATTENTION`, `confidence = 0.0`, `MODEL_OUTPUT_INVALID` reason code | Capped at **`<= 2/10`** |
| **`REJECTED` (`EVIDENCE_VALUE_MISMATCH` / `EVIDENCE_UNVERIFIED`)** | `ModelClaimExtractor` + `IndependentVerdictValidator` detect fabricated/mismatched `asserted_value` or unverified `EV-*` reference | Decisive TP/FP **overruled** to `REQUIRES_ATTENTION` — **PROVEN LIVE on V8.1 `#164575`!** | Downgraded (`3/10` on `#164575`) |
| **`ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`)** | Candidate policy is in `DRAFT` status (`contract.status != "APPROVED"`) | Decisive proposal safely blocked from autonomous execution (`REQUIRES_ATTENTION`) | Capped at `<= 6/10` while uncalibrated |
| **`VALIDATED` / `SAFE_ABSTENTION`** | Untruncated, schema-valid, 100% grounded against approved contract | Accepted for advisory triage (or safe escalation when abstaining) | Full 5-dimension rubric (capped `<= 6/10` until `>= 30` verified labels) |

---

## 3. Live Empirical Verification of Output Integrity in V8.1 (`a95cd268`)

- **Output Truncation Rate:** **`0 / 6` (`0.0%`)** — all 6 real GPU responses completed cleanly between `262` and `561` tokens (`< 768` cap), down from `5 / 6` (`83.3%`) in V8.
- **Schema Parse Failures:** **`0 / 6` (`0.0%`)** — all 6 responses parsed as valid JSON on the first pass without truncation repair.
- **Incident/Rule ID Reference Accuracy:** **`6 / 6` (`100%`)** exact matches on `incident_id` and `rule_id` (`40498741-ee6b-4a71-9101-0d6d3f77154c`).
- **Live Hallucination Rejection Proof (`#164575`):** When `Qwen/Qwen2.5-7B-Instruct-AWQ` fabricated `"asserted_value": "bidirectional_sessions=0, unanswered_probes=100, denied_flows=0"` (contradicting real telemetry `bidirectional_sessions=100, unanswered_probes=0`), `IndependentVerdictValidator` immediately flagged `EVIDENCE_VALUE_MISMATCH`, set `validation_status = REJECTED`, downgraded trust to `3/10`, and overruled `TRUE_POSITIVE` → `REQUIRES_ATTENTION`.
- **Unit Test Proof (`test_11`):** Explicitly verifies `robust_parse_model_verdict_json` tags `_truncated_output = True` and `_schema_recovery_applied = True` on mid-claim truncated JSON so truncated outputs can never masquerade as `VALID`.
- **Observed Minor Calibration Note:** On `#176011`, `#175129`, `#173449`, `#164575`, `Qwen/Qwen2.5-7B-Instruct-AWQ` returned `confidence` on a `0–1` probability scale (`0.9` / `0.95`) rather than `0–100` (`90.0` / `95.0`). Documented transparently for future prompt/schema normalization; raw model confidence is never used as proof of empirical accuracy.
