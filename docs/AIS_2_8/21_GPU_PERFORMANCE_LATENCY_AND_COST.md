# 21 — GPU Performance, Latency & Cost

> [!IMPORTANT]
> **Execution Status: NOT_RUN (Pending Server 1 Admin Bearer Token & Server 2 Model Switch Coordination)**
> 
> This live GPU benchmark section has **NOT executed yet**. No synthetic or extrapolated LLM outputs are reported here. Code changes were committed (`7fb6e53f405ba41b8d93ad2f0877fbdcc1512509`) and deployed to Server 1 (`172.26.41.240`, `local_llm.model_name = Qwen/Qwen3-14B-AWQ`, `current_s2_health = ONLINE`), and operator authorization for up to 82 GPU requests was granted. Execution requires an active Server 1 administrator JWT token (to call `/api/ground-truth/ais27/*`) and operator coordination on `verdict-llm` to toggle between `Qwen/Qwen3-14B-AWQ` and `Qwen/Qwen2.5-7B-Instruct-AWQ`.

- Historical AIS 2.7 baseline (41 Qwen2.5 calls, 208,474 tokens, 1,716.83s cumulative latency) is recorded in `GPU_TELEMETRY_VERIFICATION.json`. Real-time Server 2 Qwen3-14B latency and KV cache occupancy will be measured during live execution.
