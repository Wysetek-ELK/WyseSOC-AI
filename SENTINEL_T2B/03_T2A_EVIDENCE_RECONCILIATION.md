# 03 — Prior T2a/T2b Claims Reconciliation

Previous T2a/T2b audit documents generated inside Sentinel Chat were treated strictly as unverified LLM claims. Independent empirical verification established:

| Claimed Topic | Independent Runtime Evidence |
|---|---|
| Context window | Verified **8,192 tokens** via `/api/llm/config` and live vLLM `BadRequestError` on `max_tokens=8500` |
| Model identifier | Verified **`Qwen/Qwen3-14B-AWQ`** via `/api/chat/status` and live completion responses |
| Truncation mechanism | Confirmed **hardcoded `max_tokens: 1024` in `frontend/src/app/soc-chatbot/page.tsx:291`** and **`max_tokens=768` default in `backend/app/schemas/chat.py:15`**, compounded by missing `finish_reason` and `stream_options.include_usage` handling in `backend/app/api/chat.py` |
| Qwen3 thinking burn | Disproved as primary cause on current Server 2: live probes confirmed Server 2 defaults to `enable_thinking=False` behavior with zero `<think>` tags and zero hidden reasoning token consumption |
| Proxy / HTTP timeouts | Nginx (`300s` with `proxy_buffering off`), `chat.py` (`180s` read timeout + `10-12s` SSE keepalives) did **not** prematurely drop the 44s–75s historical runs |
