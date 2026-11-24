# AIS 2.6a — Report 02: Live 8K Runtime Discovery and Synchronization

## 1. Runtime Discovery Architecture
Server 1 (`172.26.41.240`) performs active discovery of Server 2 (`13.204.214.64:8000`) inference capabilities using `LLMConfigService` and `AIVerdictService`.

### Discovery Pathway
1. `GET http://13.204.214.64:8000/v1/models` queried via authorized inter-server HTTP transport.
2. Server 2 response parsed:
```json
{
  "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "object": "model",
  "created": 1795510896,
  "owned_by": "vllm",
  "max_model_len": 8192,
  "permission": [...]
}
```
3. Runtime capability verified:
   - Provider advertised `max_model_len`: **8192**
   - Probe latency: **12.5 ms**
   - Probe status: **200 OK**
   - Discovery timestamp: `2026-11-24T09:05:00Z`

---

## 2. Server 1 Configuration Synchronization
To maintain the invariant that configured context must never exceed verified provider context, Server 1 configuration was synchronized:
- `LOCAL_LLM_CONTEXT_BUDGET`: 8192
- `LOCAL_LLM_MAX_TOKENS`: 768
- `LOCAL_LLM_TARGET_INPUT_BUDGET`: 7424
- `LOCAL_LLM_VERIFIED_MAX_MODEL_LEN`: 8192
- `LOCAL_LLM_DISCOVERED_AT_UTC`: `2026-11-24T09:05:00Z`
- `context_budget_verified`: `true`
- `context_budget_warning`: `null`

---

## 3. Enforcement Scope
Consistent context limits (8192 max context, 768 reserved completion, 7424 max prompt budget) are enforced across:
1. `TokenBudgetService.budget_prompt`
2. `VerdictPipeline._budget_prompt`
3. `EmpiricalBenchmarkHarness.evaluate_single_incident`
4. Celery background triage workers
5. Agent Intelligence Studio UI workbench display
