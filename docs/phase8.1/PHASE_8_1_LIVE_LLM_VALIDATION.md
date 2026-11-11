# Phase 8.1 Local LLM / Server 2 Validation Report (Stage 4)

- **Status:** **`BLOCKED`** *(Physical Server 2 GPU unreachable `TimeoutError`; wire protocol, HTTP 200 malformed JSON handling, and fail-closed safety verified locally)*
- **Primary Evidence:** [`stage4_llm_contract_probe.json`](./evidence/llm/stage4_llm_contract_probe.json)

## 1. Live Server 2 Connectivity & Hardware Metrics

- **Configured Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **TCP Socket Probe:** `UNREACHABLE (TimeoutError)` from the local workspace.
- **Blocked Criteria (`NOT_TESTED`):** Live Server 2 `POST /v1/chat/completions` inference latency/throughput (`LLM-01-C2`), live `GET /metrics` GPU cache/VRAM scrape (`MON-02-C2`), and live `OPENAI_COMPATIBLE` historical replay (`QGS-02-C3`).

## 2. Phase 8.1 Wire-Protocol & Malformed Response Remediation

- **Critical Fix Inside `VerdictTriageAgent` (`P8.1-DEF-002` Root Cause):** Previously, [`VerdictTriageAgent._evaluate_incident_locked`](../../backend/app/services/ai_verdict_service.py#L528-L535) set `is_connection_error = True` whenever `confidence == 0.0 and validation_status != "VALID"`. That misclassified HTTP 200 responses carrying `INVALID_SCHEMA` or `UNEXPECTED_VERDICT` from [`OpenAICompatibleProvider`](../../backend/app/services/model_provider/openai_compatible.py) as network outages—causing either false `LocalLLMUnavailableError` crashes (`allow_simulated_fallback=False`) or silent swap-in of `SIMULATED` mock verdicts (`allow_simulated_fallback=True`).
- **Remediated Behavior:** `is_connection_error` now triggers strictly on `("CONNECTION_ERROR", "HTTP_ERROR")`. Real TCP HTTP 200 garbage output (`"NOT_JSON {{{ broken output here"`) is preserved as an explicit model output failure, routed through [`IndependentVerdictValidator`](../../backend/app/services/independent_verdict_validator.py) & [`VerdictTrustworthinessEngine`](../../backend/app/services/verdict_trustworthiness_engine.py), and persisted with `validation_status="INVALID_MODEL_OUTPUT"`, `proposal_validation_outcome="INVALID_MODEL_OUTPUT"`, `final_disposition="SAFE_ABSTENTION_AFTER_INVALID_OUTPUT"`, `is_simulated=False`, `confidence=0.0`, and `trust_score <= 2`.
- **Verification:** Verified end-to-end against a real local `ThreadingHTTPServer` in [`test_p8_1_def_002_003_invalid_model_output_and_contradiction_trust_bounds`](../../backend/tests/test_phase8_1_validation.py) and `test_phase8_llm_http_contract_fault_injection` in [`test_phase8_integration.py`](../../backend/tests/test_phase8_integration.py).

