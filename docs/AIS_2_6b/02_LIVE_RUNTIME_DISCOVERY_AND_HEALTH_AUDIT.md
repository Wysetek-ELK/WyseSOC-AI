# 02 — Live Runtime Discovery and Health Audit

## 1. Multi-Server Runtime Verification
- **Server 1 (Application)**: `172.26.41.240` running backend (`ai-verdict-backend`) on port 8000, frontend on port 3000, PostgreSQL on 5432, Celery and Redis on 6379. Verified deployed commit: `c13c900de810243ec60e773d8b59382de2793ea6`.
- **Server 2 (Cortex / GPU)**: AWS GPU Instance (`13.204.214.64:8000`) with NVIDIA A10G GPU running vLLM service `vllm-server.service` with `Qwen/Qwen2.5-7B-Instruct-AWQ`.
- **Authoritative Model Metadata**:
  ```json
  {
    "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "owned_by": "vllm",
    "max_model_len": 8192
  }
  ```
- **Context Allocation**:
  - Context Window: 8192 tokens
  - Reserved Completion: 768 tokens
  - Max Prompt Budget: 7424 tokens
  - Clamped Target Budget: 6400 tokens

