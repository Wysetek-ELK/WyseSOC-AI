# 08 — Qwen3 Reasoning Configuration Verification

- Live Server 2 probes (`/api/chat/message` and `/api/chat/stream`) verified that `Qwen/Qwen3-14B-AWQ` does **not** emit `<think>...</think>` blocks or hidden `reasoning_content` tokens under current Server 2 configuration.
- Server 1 aligns `chat.py` with `OpenAICompatibleProvider` by sending `chat_template_kwargs: {"enable_thinking": settings.LOCAL_LLM_ENABLE_THINKING}` (`false` by default) for Qwen3 models, and simultaneously supports `delta.reasoning_content` / `delta.reasoning` and `usage.completion_tokens_details.reasoning_tokens` if thinking mode is ever enabled on Server 2 in the future.
- `reasoning_tokens` is displayed in UI Technical Details **only** when actually reported by Server 2 (never fabricated).
