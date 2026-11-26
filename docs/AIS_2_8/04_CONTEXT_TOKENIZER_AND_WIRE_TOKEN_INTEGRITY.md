# 04 — Context, Tokenizer & Wire Token Integrity

- Registered `Qwen/Qwen3-14B-AWQ` alongside `Qwen/Qwen2.5-7B-Instruct-AWQ` in `LLMConfigService.DEFAULT_MODEL_PROFILES` (`8192 / 768 / 7424`).
- Updated `config.py`, `schemas/llm_config.py`, `schemas/token_budget.py`, `schemas/chat.py`, `runtime_config_service.py`, `integration_diagnostic_service.py`, and `verdict_pipeline.py` so runtime context caps honor configured & verified limits cleanly without stale `16384` / `1024` fallbacks.
- Updated `ModelTokenizerService` with Qwen3 chat-template overhead accounting (`QWEN3_CHAT_TEMPLATE_OVERHEAD_TOKENS = 72`) and added `count_wire_prompt_tokens_remote()` supporting Server 2 `/tokenize` verification with calibrated local fallback.
- Replaced hardcoded `16,384` / `1,024` / `8,192` helper copy in `frontend/src/app/agent-configuration/page.tsx` with dynamic bound labels and corrected private VPC IP vs public NAT egress IP labeling.
- Verified across `test_context_window_8k_16k.py`, `test_llm_config.py`, `test_token_budgeting.py`, and `test_ais_2_8_intelligence.py` (`0` failures).
