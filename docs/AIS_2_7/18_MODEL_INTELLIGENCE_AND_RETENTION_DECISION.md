# AIS 2.7 — Workstream 18: Model Intelligence Assessment & Retention Decision

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [MODEL_CAPABILITY_SCORECARD.json](MODEL_CAPABILITY_SCORECARD.json), [MODEL_RETENTION_DECISION.json](MODEL_RETENTION_DECISION.json)

## Final Model Verdict: **`NOT_SUITABLE_FOR_PRODUCTION_OR_CONTINUED_TUNING_REPLACE_OR_UPGRADE_MODEL`**

| Evaluation Criterion | Measured Result | Verdict |
|---|---|---|
| JSON Schema & Stop Compliance | `40/40 (100.0%)`, `0` overflows | **PASS** |
| Mode A Raw Baseline Reasoning | `1/20 (5.0%)` 3-class, `0/9 (0.0%)` TP recall, `9/9 (100.0%)` missed TP | **FAIL** |
| Mode B Policy-Assisted Raw Reasoning | `2/20 (10.0%)` 3-class, `2/9` TP recall, `0/1` FP recall, `0/10` Prisma abstentions | **FAIL** |
| Factual & Contextual Faithfulness | `0/20` Mode B incidents cleanly hallucination-free | **FAIL** |
| Mode C Validator Firewall | `9/20 (45.0%)` 3-class, `0/9` missed-TP-as-FP, `8/10` Prisma rescued | **SAFETY WORKS; MODEL FAILS** |

**Why Prompt Tuning Alone Cannot Save `Qwen/Qwen2.5-7B-Instruct-AWQ`:** A 4-bit AWQ 7B model that treats every neutral alert as FP (`20/20`), claims an explicitly supplied JSON field is missing on `7/9` TPs under policy prompts, calls `3.109.76.166` an internal IP, calls `172.25.14.67` non-internal, and calls `Program Files (x86)` a writable temporary path lacks the foundational instruction adherence and security reasoning required for Verdictum AI. Retain Verdictum AI's Validator + Evidence Contract + Ingestion pipeline, fix the Prisma policy template and enrichment pipeline, and upgrade the LLM.
