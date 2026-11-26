# 13 — Qwen2.5 Real GPU Baseline Results

> [!IMPORTANT]
> **Execution Status: NOT_RUN (Pending Server 1 Admin Bearer Token & Server 2 Model Switch Coordination)**
> 
> This live GPU benchmark section has **NOT executed yet**. No synthetic or extrapolated LLM outputs are reported here. Code changes were committed (`7fb6e53f405ba41b8d93ad2f0877fbdcc1512509`) and deployed to Server 1 (`172.26.41.240`, `local_llm.model_name = Qwen/Qwen3-14B-AWQ`, `current_s2_health = ONLINE`), and operator authorization for up to 82 GPU requests was granted. Execution requires an active Server 1 administrator JWT token (to call `/api/ground-truth/ais27/*`) and operator coordination on `verdict-llm` to toggle between `Qwen/Qwen3-14B-AWQ` and `Qwen/Qwen2.5-7B-Instruct-AWQ`.

- Reconciled historical AIS 2.7 Qwen2.5-7B-Instruct-AWQ results remain: Mode A 1/20 (5.0%), Mode B 2/20 (10.0%), Mode C 9/20 (45.0%). Fresh controlled Qwen2.5 runs under AIS 2.8 parity inputs await Server 1 admin token and Server 2 model switch.
