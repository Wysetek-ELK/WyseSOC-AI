# AIS 3.1 — Workstream 9: Token Budget & Evidence Completeness (Pre-Deploy Audit Scope)

> [!NOTE]
> Local static BPE budget verification ran cleanly via `pytest` (`test_token_budgeting.py` + `test_ais_3_1_holdout_benchmark.py`). Live vLLM `/tokenize` verification (`verify_remote_tokenize=true`) across all 100 holdout incidents executes on Server 1 immediately after UPLA Gate 2 deployment (`TOKEN_BUDGET_RESULTS.json` will be populated with exact per-incident wire token counts).

---

## 1. Token Budget Configuration & Enforcement

Implemented in `TokenBudgetService.budget_prompt`, `ModelTokenizerService.count_wire_prompt_tokens_remote`, and `AIS31BenchmarkService._prepare_incident_wire_payload`:

- **Context Ceiling:** `max_model_len = 8192` (verified on `Qwen/Qwen3-14B-AWQ`).
- **Reserved Completion Budget:** `768` tokens (`temperature=0.0`, `enable_thinking=false`).
- **Max Prompt Input Ceiling:** `7424` tokens (`8192 - 768`).
- **Evidence Preservation Rules:**
  - `FROZEN_NEUTRAL_SYSTEM_PROMPT`, `RuleDefinitionBuilder` rule specification, and required JSON output schema are NEVER truncated.
  - Progressive re-budgeting iterates up to `3` times if remote vLLM `/tokenize` (`messages_chat_template`) exceeds `7424`, subtracting `drift_tokens` headroom and compacting surplus raw event noise while preserving canonical evidence records and material detection evidence.
  - Any incident still exceeding `7424` tokens after 3 re-budget passes is explicitly aborted with `CONTEXT_WINDOW_EXCEEDED` and `REQUIRES_ATTENTION` rather than silently truncated.

---

## 2. Live vLLM `/tokenize` Audit Status

Pending UPLA Gate 1 (GitHub) + Gate 2 (Server 1 deploy) so `/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/token-audit?verify_remote_tokenize=true` executes directly against `13.204.214.64:8000/tokenize`. Results will overwrite this status note with empirical min/median/p95/max token counts.
