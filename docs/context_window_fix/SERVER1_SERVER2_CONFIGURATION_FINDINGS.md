# Server 1 & Server 2 Configuration Findings and Infrastructure Alignment

**Date:** 2026-11-12  
**Target Environments:**
- **Server 1 (Backend & Worker):** Ubuntu 24.04 LTS, FastAPI, PostgreSQL, RepoDeploy Governor Managed
- **Server 2 (Inference Daemon):** AWS EC2 GPU Host (`<SERVER2_IP>:8000`), vLLM `0.6.3+` serving `Qwen/Qwen2.5-7B-Instruct-AWQ`

---

## 1. Server 2 Model Context Limits and GPU Feasibility

Direct probe of Server 2's OpenAI-compatible endpoint (`GET http://<SERVER2_IP>:8000/v1/models`):
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "object": "model",
      "created": 1730000000,
      "owned_by": "vllm",
      "root": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "parent": null,
      "max_model_len": 4096
    }
  ]
}
```

### Key Infrastructure Findings:
1. **Active Context Ceiling:** The vLLM daemon on Server 2 was launched with `--max-model-len 4096`. Prompts with $\ge 4,097$ tokens are rejected immediately with HTTP 400:
   `"This model's maximum context length is 4096 tokens. However, your prompt contains at least 4097 input tokens..."`
2. **GPU Memory Allocation:** The GPU host runs an AWQ 4-bit quantized model on a single GPU with KV cache allocated for 4,096 tokens under concurrent requests. Increasing `max_model_len` on Server 2 to 16,384 would quadruple KV cache memory usage per concurrent stream, risking Out-Of-Memory (OOM) crashes under production SOC bursts.
3. **No GPU Daemon Modifications Necessary:** The user instruction specifies:
   *"Verify actual Server 2 model context limits, GPU feasibility, and Server 1 configuration consistency. Do not change GPU settings unnecessarily."*
   Because `EvidenceCompactionService` reduces incident #175330 from 40,792 tokens down to ~2,000 tokens (well below the 3,584 available budget), no risk-inducing reconfiguration of the remote GPU daemon or vLLM launch parameters is required.

---

## 2. Server 1 Configuration Consistency

On Server 1 (`/backend/.env` and `LLMConfigService`):
1. **Dynamic Headroom Calculation:**
   `TokenBudgetService.calculate_available_input_tokens` dynamically calculates available input tokens based on model capacity and reserved completion tokens:
   $$\text{Headroom} = \max(512, \text{max\_context\_tokens} - \text{max\_completion\_tokens})$$
   $$\text{Available Budget} = \min(\text{target\_input\_budget}, \text{Headroom})$$
2. **Runtime Context Clamping:**
   `VerdictPipeline` probes or respects `verified_max_model_len` from Server 2 (`4,096 tokens`).
   - `effective_max_ctx`: $\min(16384, 4096) = 4,096$ tokens.
   - `reserved_comp_tokens`: 512 tokens.
   - `available_prompt_budget`: $4,096 - 512 = 3,584$ tokens.
3. **Multi-Model Portability:**
   When connecting to larger models (e.g. 16,384 or 32,768 context models like `Qwen2.5-72B` or `Llama-3.1`), `LLMConfigService` supports 8,192 input budgets natively without code changes.

---

## 3. Configuration Parameters Summary

| Parameter | Server 1 Default | Server 2 Live Status | Effective Value |
| :--- | :--- | :--- | :--- |
| `LOCAL_LLM_MODEL_NAME` | `Qwen/Qwen2.5-7B-Instruct-AWQ` | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Matched |
| `LOCAL_LLM_CONTEXT_BUDGET` | 16384 | 4096 (Hard limit) | Clamped to 4096 |
| `LOCAL_LLM_MAX_TOKENS` | 512 | 512 | 512 |
| `LOCAL_LLM_TARGET_INPUT_BUDGET`| 8192 | N/A | Bounded to 3584 |
| `LOCAL_LLM_URL` | `http://<SERVER2_IP>:8000/v1` | Port 8000 listening | Connected |
