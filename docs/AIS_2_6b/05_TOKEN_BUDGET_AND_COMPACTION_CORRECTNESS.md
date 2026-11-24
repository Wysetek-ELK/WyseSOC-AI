# 05 — Token Budget and Compaction Correctness Report

## 1. Token Budget Compliance Under 8192 Runtime
- Runtime Context: 8,192 tokens
- Completion Headroom: 768 tokens
- Wire Prompt Ceiling: 7,424 tokens
- Clamped Target Budget: 6,400 tokens
- Peak Wire Prompt Tokens Observed: 7,012 tokens (`132441815`)
- Minimum Wire Prompt Tokens Observed: 3,042 tokens (`132596403`)
- Token Overflow Rejections (HTTP 400): **0**
- Compaction Triggered: Successfully compacted large incident `132461368` from 91 canonical records down to 4,834 tokens.

