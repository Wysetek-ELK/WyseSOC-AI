# 04 — Exact Mode-Independent Wire Token Implementation

- Added `ModelTokenizerService.render_wire_user_message(...)` and upgraded `count_wire_prompt_tokens_remote(...)` to call vLLM `/tokenize` with `messages` + `chat_template_kwargs={enable_thinking: false}` (`tokenize_mode="messages_chat_template"`).
- Updated `TokenBudgetService.budget_prompt(...)` (`wire_system_prompt`, FULL `wire_rule_spec`, `safety_margin_tokens`) and wired it in both `AIS27BenchmarkRunner` and `verdict_pipeline` / `OpenAICompatibleProvider`.
- Added up-to-2-iteration automatic live `/tokenize` re-budgeting in `AIS27BenchmarkRunner` (proven live on `132461358`, which had `drift=591` and auto-compacted in `rebudget_iterations=2` to `7015` tokens).
- Verified 6/6 scenarios via `/api/ground-truth/ais27/tokenize-verify`.
