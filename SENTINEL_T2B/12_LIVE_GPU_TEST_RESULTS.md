# 12 — Live GPU Test Results (Post-Deployment)

## Runtime Metrics (Separated from Intelligence Accuracy)

| Metric | Measured Result |
|---|---|
| Auto-budget completion rate (`RT01`, `RT03`, `RT04`×3, `RT06`) | **100%** (6/6 `COMPLETED`, `finish_reason=stop`) |
| Unintended truncation rate | **0%** (0/6) |
| Timeout rate | **0%** (0/6) |
| Stream interruption rate | **0%** (0/6) |
| Controlled overflow detection (`RT08`) | **100%** (1/1 fail-closed HTTP 422 / `CONTEXT_BUDGET_EXCEEDED` in 137ms) |
| Controlled truncation + continuation (`RT09`+`RT14`) | **100%** (`max_tokens=160` -> `TRUNCATED` -> `continue` -> `COMPLETED` 1817 tokens) |
| Persistence & UI/Backend parity | **100%** (`RT17` 4 messages persisted; UI T2 1975 tok `COMPLETED`) |

## Intelligence Observations (Recorded for T3/T4 — Unmodified LLM Output)

- In **T2 (`#16100`)**, the model completed all Sections A–I and noted missing `sample_events` (`event_count=0` in normalized DB events table, even though `raw_payload.incidentDetail` carried `incidentCount: 103`), returning `REQUIRES_ATTENTION`. It also exhibited the known T1 bias ("The source IP is internal, which could indicate a false positive"), confirming why T3/T4 policy/context work remains separate from runtime reliability.
- In **T3.1 (3 runs)**, with inline telemetry supplied, all 3 runs extracted entities, verified `40 + 35 + 28 = 103 >= 100`, checked timestamp consistency (`7. Eventtime and date/time consistency`), and ended with `[T3_1_COMPLETE]`.
