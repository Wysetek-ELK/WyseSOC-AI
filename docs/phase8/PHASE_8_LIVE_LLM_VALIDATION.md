# Phase 8 Local LLM / Server 2 Validation Report

**Stage Covered:** Stage 3 (Live Local LLM Integration & HTTP Contract)

## 1. Live Server 2 Availability Status: **BLOCKED / UNAVAILABLE**

- **Configured Endpoint (`settings.LOCAL_LLM_BASE_URL`):** `http://<REDACTED_HOST>:8000/v1` (model: `Qwen/Qwen2.5-7B-Instruct-AWQ`)
- **Live Reachability Result:** `UNREACHABLE (TimeoutError)` when probing TCP port `8000` from the local environment.
- **Implication:** Real GPU latency, vLLM throughput under concurrent load, real Qwen 2.5 AWQ token generation quality, and hardware VRAM/thermal telemetry cannot be measured or claimed in this offline environment (`LLM-01-C2`, `MON-02-C2`, `QGS-02-C3` remain `NOT_TESTED`).

## 2. Verified HTTP Wire-Protocol, Parsing & Fault-Tolerance Validation

To prove [`OpenAICompatibleProvider`](../../backend/app/services/model_provider/openai_compatible.py), [`InferenceHealthMonitor`](../../backend/app/services/system_monitor_service.py), and [`gpu_workload_manager`](../../backend/app/services/gpu_manager.py) without mocking away HTTP serialization, [`test_phase8_llm_http_contract_fault_injection`](../../backend/tests/test_phase8_integration.py) launched a local multi-threaded TCP HTTP server simulating vLLM endpoints:

1. **Health & Model Discovery (`GET /health`, `GET /v1/models`)**: Confirmed healthy probe status and exact model ID extraction (`Qwen/Qwen2.5-7B-Instruct-AWQ`).
2. **Valid Structured JSON & Token Usage (`POST /v1/chat/completions`)**: Confirmed strict parsing of `verdict`, `confidence`, `supporting_claims`, and `total_tokens=165` tracking.
3. **Markdown-Fenced / Truncated JSON Repair**: Confirmed truncated fenced `FALSE_POSITIVE` payload repairs cleanly via `_repair_truncated_json` instead of dropping recoverable structure.
4. **Malformed Non-JSON Garbage**: Confirmed total unparseable text safely coerces to `verdict="REQUIRES_ATTENTION"`, `validation_status="INVALID_SCHEMA"`, `confidence=0.0`.
5. **HTTP 500 CUDA OOM & Timeouts + Circuit Breaker**: Confirmed consecutive `500` failures and request timeouts trip `gpu_workload_manager.circuit_breaker` cleanly into `CircuitState.OPEN` without leaking uncaught crashes or fabricating simulated verdicts.
6. **Prometheus Metrics Parsing (`GET /metrics`)**: Confirmed vLLM cache usage, active requests, and token throughput text exposition parsing in `InferenceHealthMonitor`, plus honest `OFFLINE` / `null` reporting when `/metrics` is unreachable.
7. **Strict Offline Fail-Closed Behavior**: Confirmed in [`test_phase8_stage4_complete_13_scenario_matrix_and_trace_export`](../../backend/tests/test_phase8_integration.py) (`S10`) and Chromium UI E2E Step 6 & 8 that setting `allow_simulated_fallback=False` raises `LocalLLMUnavailableError` / HTTP error and leaves `incident.ai_verdict = None` with zero simulated verdict leakage.

