# 03 — Mode B Token Overflow Root Cause (`132474210`)

- Previous `TokenBudgetService.budget_prompt` budgeted against Mode A's shorter system prompt and a compact 5-key `rule_spec` stub (~90 tokens), plus pure-Python BPE undercounted by +274 to +591 tokens vs vLLM's Qwen3 tokenizer.
- Consequently, `132474210` retained 71 canonical evidence entries in Mode B vs 46 in Mode A, pushing Mode B wire input to 8,088 tokens and truncating completion at 104 tokens (`finish_reason=length`).
