# 08 — Final Experiment Protocol & Request Budget Governance

| ID | Description | Mode / Policy / Enrichment / Prompt | Calls Attempted | Calls Succeeded |
|---|---|---|---:|---:|
| `H` | Historical AIS 2.7 Baseline (`Qwen/Qwen2.5-7B-Instruct-AWQ`) | Archived `mode_a`, `mode_b`, `mode_c` | 42 (AIS 2.7) | 41 (AIS 2.7) |
| `SMOKE` | Live Qwen3 Pre/Post-Fix Synthetic Connectivity | `POST /ais27/smoke-test` | 5 pre-fix + 1 post-fix | 1 (`chatcmpl-b6de0ebd1e1f8817`) |
| `A` | `QWEN3_NEUTRAL_V2` | `mode=A`, `V2`, `rule_def=true`, `ev_intel=false`, `cand_pol=false`, `temp=0.0` | 20 | 20 |
| `B` | `QWEN3_ENRICHED` | `mode=A`, `V2`, `rule_def=true`, `ev_intel=true`, `cand_pol=false`, `temp=0.0` | 21 (1 WinError 10054 reset) | 20 |
| `C` | `QWEN3_RULE_AWARE` | `mode=B`, `V2`, `rule_def=true`, `ev_intel=true`, `cand_pol=true`, `temp=0.0` | 20 | 20 |
| `D` | `QWEN3_VALIDATOR` | Deterministic CPU validation on A, B, C outputs | 0 GPU calls | N/A |
| `R` | `QWEN3_HISTORICAL_PROMPT_REPLAY` (Budget-Capped Stratified Subset) | `mode=A`, `V1`, `rule_def=false`, `ev_intel=false`, `temp=0.1` | 15 | 15 |
| **Total AIS 2.8** | **Authorized Ceiling = 82** | **Single-model `Qwen/Qwen3-14B-AWQ` exclusive** | **82 / 82** | **76** |
