# Phase 8.1 Verdict E2E Pipeline & Disposition Validation (Stage 5)

- **Status:** **`PASSED`** *(Controlled provider scenarios & unit contracts verified after `P8.1-DEF-002` / `P8.1-DEF-003` remediations; live Server 2 weights remain `BLOCKED`)*
- **Primary Evidence:** [`stage5_verdict_disposition_traces.json`](./evidence/verdicts/stage5_verdict_disposition_traces.json) | [`test_phase8_1_validation.py`](../../backend/tests/test_phase8_1_validation.py)

## 1. Remediations Implemented (`P8.1-DEF-002` & `P8.1-DEF-003`)

1. **`P8.1-DEF-002` — Explicit Disposition vs Proposal Validation Outcomes:**
   - Added `proposal_validation_outcome`, `final_disposition`, and `abstention_reason` to [`VerdictValidationResult`](../../backend/app/schemas/verdict_validation.py), `verdict_data` in [`VerdictTriageAgent`](../../backend/app/services/ai_verdict_service.py), and [`IncidentAiVerdictResponse`](../../frontend/src/lib/api.ts).
   - Fixed [`IndependentVerdictValidator.validate_verdict`](../../backend/app/services/independent_verdict_validator.py) (`MODEL_OUTPUT_INVALID`) and [`VerdictTriageAgent`](../../backend/app/services/ai_verdict_service.py) (`INVALID_SCHEMA` / `UNEXPECTED_VERDICT` / `PARSE_ERROR`) so malformed outputs set `validation_status="INVALID_MODEL_OUTPUT"` instead of `"VALIDATED"`.
2. **`P8.1-DEF-003` — Contradiction & Malformed Output Trust Caps:**
   - Updated [`VerdictTrustworthinessEngine`](../../backend/app/services/verdict_trustworthiness_engine.py), [`VerdictGuardrailsEngine.apply_guardrails`](../../backend/app/services/verdict_guardrails_engine.py) (`G0_INVALID_MODEL_OUTPUT`), and [`VerdictTriageAgent`](../../backend/app/services/ai_verdict_service.py) so:
     - Contradictory telemetry (`claim_verification` or `model_output["contradictory_evidence"]` or `val_res.detected_contradictions`) and zero-grounded decisive assertions cap `trust_score <= 3` (previously `S04` leaked `trust_score = 6`).
     - Malformed/unparseable outputs (`INVALID_SCHEMA`, `UNEXPECTED_VERDICT`, invalid label) cap `trust_score <= 2` (previously `S09` leaked `trust_score = 4`) and append an explicit `INVALID_MODEL_OUTPUT` limitation note.

## 2. Verified Disposition Matrix (`test_p8_1_def_002_003_invalid_model_output_and_contradiction_trust_bounds`)

| Case | Raw Model Input | Final Verdict | `validation_status` | `proposal_validation_outcome` | `final_disposition` | `trust_score` |
|---|---|---|---|---|---|---:|
| **A (`INC-P81-GARBAGE`)** | HTTP 200 non-JSON garbage (`INVALID_SCHEMA`) | `REQUIRES_ATTENTION` | `INVALID_MODEL_OUTPUT` | `INVALID_MODEL_OUTPUT` | `SAFE_ABSTENTION_AFTER_INVALID_OUTPUT` | `<= 2` |
| **B (`INC-P81-BADLABEL`)** | Unknown label `"MALICIOUS_MAYBE"` | `REQUIRES_ATTENTION` | `INVALID_MODEL_OUTPUT` | `INVALID_MODEL_OUTPUT` | `SAFE_ABSTENTION_AFTER_INVALID_OUTPUT` | `<= 2` |
| **C (`INC-P81-CONTRA`)** | `TRUE_POSITIVE` + `contradictory_evidence` (`Process Blocked=true`) | `REQUIRES_ATTENTION` | `REJECTED` | `REJECTED_BY_VALIDATOR` | `OVERRULED_TO_ANALYST_ATTENTION` | `<= 3` |
| **D (`INC-P81-ABSTAIN`)** | Valid cautious `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `VALIDATED` | `MODEL_ABSTENTION` | `SAFE_ANALYST_ESCALATION` | Uncalibrated |
| **E (`INC-P81-TP`)** | Grounded `TRUE_POSITIVE` with CORE telemetry | `TRUE_POSITIVE` | `VALIDATED` | `VALID_DECISIVE_PROPOSAL` | `ACCEPTED_DECISIVE_VERDICT` | Uncalibrated (`<= 6`) |

