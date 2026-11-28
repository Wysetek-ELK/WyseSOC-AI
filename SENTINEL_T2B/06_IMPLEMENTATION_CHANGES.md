# 06 — Implementation Changes

Modified and added files (deployed SHA `eb78e6ffc034b0cfc3560de0509642efda5b9e59`):

- **`backend/app/services/sentinel_token_budget.py`** *(new)*: `SentinelTokenBudgetService` computing `effective_context_window`, tokenizing full multi-turn messages via Server 2 `/tokenize` (with calibrated BPE fallback), reserving safety margins (`32`/`64`), progressively trimming oldest history turns with disclosure while keeping system prompt/incident evidence/latest user prompt immutable, and failing closed (`CONTEXT_BUDGET_EXCEEDED`) when input exceeds capacity.
- **`backend/app/models/chat.py`** & **`backend/alembic/versions/019_sentinel_chat_persistence.py`** *(new)*: `SentinelConversation` and `SentinelMessage` tables with strict user ownership, lifecycle status, finish reason, token telemetry, and continuation lineage.
- **`backend/app/models/__init__.py`** *(modified)*: Exported new chat models.
- **`backend/app/schemas/chat.py`** *(modified)*: Made `ChatRequest.max_tokens` optional (`None` = context-aware auto budget), added lifecycle fields, `ContinueChatRequest`, and conversation schemas.
- **`backend/app/api/chat.py`** *(modified)*: Integrated `SentinelTokenBudgetService`, `stream_options={"include_usage": True}`, `chat_template_kwargs`, `finish_reason` + `[DONE]` classification (`COMPLETED`/`TRUNCATED`/`INTERRUPTED`/`TIMEOUT`/`FAILED`/`CANCELLED`), `reasoning_delta` separation, partial JSON buffering, `gpu_workload_manager` slot/circuit-breaker protection, `/conversations` & `/requests/{id}` & `/continue` endpoints, and sanitized structured logging.
- **`frontend/next.config.ts`** *(modified)*: Raised `proxyTimeout` to `600_000` ms.
- **`frontend/src/lib/api.ts`** *(modified)*: Shared `consumeChatSseResponse` with 120s idle watchdog, 600s abort timeout, missing-`done` `INTERRUPTED` classification, and conversation/continuation client methods.
- **`frontend/src/app/soc-chatbot/page.tsx`** *(modified)*: Removed `max_tokens: 1024`, added saved conversation switcher & `New Chat`, exact incomplete/interrupted/budget warnings, `Continue Response` action, and collapsed-by-default `Technical Details`.
- **`backend/tests/test_sentinel_t2b_regression.py`**, **`frontend/tests/sentinel-t2b-ui.test.mjs`**, **`frontend/package.json`**: Added comprehensive regression test suites.
