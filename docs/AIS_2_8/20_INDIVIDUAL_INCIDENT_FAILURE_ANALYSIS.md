# 20 — Individual Incident Failure Analysis

> [!IMPORTANT]
> **Execution Status: NOT_RUN (Pending Server 1 Admin Bearer Token & Server 2 Model Switch Coordination)**
> 
> This live GPU benchmark section has **NOT executed yet**. No synthetic or extrapolated LLM outputs are reported here. Code changes were committed (`7fb6e53f405ba41b8d93ad2f0877fbdcc1512509`) and deployed to Server 1 (`172.26.41.240`, `local_llm.model_name = Qwen/Qwen3-14B-AWQ`, `current_s2_health = ONLINE`), and operator authorization for up to 82 GPU requests was granted. Execution requires an active Server 1 administrator JWT token (to call `/api/ground-truth/ais27/*`) and operator coordination on `verdict-llm` to toggle between `Qwen/Qwen3-14B-AWQ` and `Qwen/Qwen2.5-7B-Instruct-AWQ`.

- Baseline AIS 2.7 incident attribution across the 20 `AIS_2_6E_FROZEN_20` incidents is carried in `INTELLIGENCE_FAILURE_TAXONOMY.json` (`ERROR_ATTRIBUTION_MATRIX.json` source). Post-AIS 2.8 Qwen3 per-incident dispositions await live GPU run.
