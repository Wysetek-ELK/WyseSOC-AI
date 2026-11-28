# 04 — Failure Reproduction (Before Fix)

Exact original T2 and T3.1 user prompts were not persisted in the unpatched Server 1 database (Sentinel previously kept messages only in browser React state and logged only token counts in `token_usage_records`). Historical `CHATBOT` ledger entries from 2026-11-28T13:00Z–13:31Z showed 7 runs with `prompt_tokens=307` (unpatched `len(sys_prompt)//4` fallback) and `completion_tokens` between `761` and `1146`.

Using clearly labeled **reconstructed** T2 and T3.1 prompts against incident `#16100` on the unpatched Server 1 deployment (`before_reproduction.json` & `ui_before_sentinel.png`):

1. **Path 2 — Backend `/api/chat/stream` (`max_tokens=1024`)**: Stopped mid-sentence after **1,024 deltas** (`"...it may be:\n"`), yet emitted `type: "done"` with no truncation warning.
2. **Path 2 — Backend `/api/chat/message` (`max_tokens=1024`)**: Stopped mid-sentence at **`completion_tokens=1024`** (`"...lack of data or a misconfigured"`).
3. **Path 3 — Sentinel UI (`http://172.26.41.240/soc-chatbot`)**: Stopped mid-sentence inside Section D (`"...May be a follow-up to the scanning phase"`), displaying no warning and no continuation control.
