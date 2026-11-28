# 05 — Verified Root Cause Analysis

| Suspected Cause | Classification | Supporting Evidence |
|---|---|---|
| Fixed output token limit (`max_tokens: 1024` / `768`) | **CONFIRMED** | `soc-chatbot/page.tsx:291` hardcoded `max_tokens: 1024`; `schemas/chat.py:15` defaulted to `768`. Reproduced exact 1,024-token mid-sentence cutoff across stream, non-stream, and UI. |
| Missing `finish_reason` & silent stream completion | **CONFIRMED** | `chat.py` & `api.ts` ignored `finish_reason="length"` and stream EOF without `[DONE]`, emitting/accepting `done` as success. |
| Incorrect token accounting (`len//4` fallback) | **CONFIRMED** | `chat.py` omitted `stream_options.include_usage=True`, causing `prompt_tokens=307` (`len(sys_prompt)//4`) across all 7 historical runs. |
| Lack of context-aware output budgeting | **CONFIRMED** | `chat.py` never computed `effective_context_window - input_tokens - safety_margin` nor trapped pre-dispatch overflow. |
| Absence of conversation persistence | **CONFIRMED** | Sentinel stored messages only in React `useState([])`. |
| Qwen3 thinking token consumption | **RULED_OUT** (current runtime) | Live `/api/chat/message` & `/api/chat/stream` probes showed `completion_tokens` equaled visible text tokens (zero hidden reasoning tokens). |
| HTTP / Reverse proxy / Idle timeout | **RULED_OUT** (for 1024-tok failures) | Unpatched runs completed in 44s–75s under 180s/300s timeouts; however, `api.ts` & `next.config.ts` were raised from `300s` to `600s` to protect larger 4,000+ token generations. |
| Frontend rendering / SSE Unicode defect | **RULED_OUT** | All streamed deltas rendered faithfully up to the 1,024-token cutoff. |
