# 10 — Final Recommendation & Executive Decision (AIS 2.0 V8 Validation)

**Date (UTC):** `2026-11-18T16:15:00Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Deployed Server 1 SHA:** `10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c` (`23 passed in 5.78s`, Next.js build `PASS`)
**Active Policy (UNCHANGED):** **Approved v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`)
**Candidate Policy Created:** **DRAFT v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, G1–G7 `85.0/85.0`, `0` blockers)
**Local LLM (UNTOUCHED):** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`max_model_len = 4096`)

---

## Executive Determination

> ### **1. Empirical Accuracy Status:** **`NOT MEASURABLE`** (`0 / 100` verified independent analyst ground-truth evaluations)
> ### **2. Policy Promotion Recommendation:** **DO NOT APPROVE V8 YET — KEEP APPROVED V7 ACTIVE AND RETAIN V8 IN `DRAFT`**
> ### **3. Production Automation Status:** **`BLOCKED` & DISABLED** (`lifecycle_stage: LEARNING`, `is_enabled: false`, `0` live FortiSIEM closures)

---

## What V8 Empirically Proved vs. What Remains Blocked

### Verified Real Improvements Delivered in V8 (`10021a3f` + Candidate DRAFT v8)
1. **Eliminated Evidence-Contract & Compaction Defects:**
   - Audited all `69` incidents (`3,197` FortiGate events) and proved `0/3,197` expose raw `network.tcp_flags`.
   - Reclassified `network.tcp_flags` as `OPTIONAL` and `detection.threshold` as `RULE_METADATA`; split `evidence_contract` into `required_fields` / `conditional_fields` / `optional_fields`; added `appctrl_pass_events` for the `806` `FortiGate-appctrl-ips-pass` logs; fixed compaction so `event.timestamp` and `network.protocol` survive on `100%` of rich-log incidents.
   - `0/6` V8 runs falsely blamed `network.tcp_flags` or `detection.threshold`.
2. **Major Grounding, Hallucination & Trust Gains on Real Server 2 GPU (`Qwen/Qwen2.5-7B-Instruct-AWQ`):**
   - **Grounded Canonical Claims:** Improved from **`0 / 0` (v7) → `16 / 16` (`100%`, `0` unsupported) on v8**.
   - **Hallucination Elimination:** Eliminated v7's `"raw event count is zero"` hallucination on `#176011` and `#167157` (`2 → 0`).
   - **Schema Reliability:** Eliminated v7's `INVALID_MODEL_OUTPUT` failure on `#164575` (`1 → 0`).
   - **Raw Trust Score:** Improved mean rich-incident raw trust from **`60.0` → `81.0 / 100` (+21.0 pts)**, reaching the `6/10` uncalibrated ceiling on all `6/6` incidents.
   - **Safe Abstention Preserved:** Correctly abstained on header-only `#176122` (`scan.raw_events_count == 0`) and mixed internal+external `#167157` (`internal=2, external=30`).
3. **Honest Reporting, Learning Reversal & UI Clarity:**
   - Live API and `RuleLearningDashboard.tsx` now explicitly report **`NOT MEASURABLE`** (never `0.0%` achieved accuracy), display `v7 (APPROVED) | v8 (DRAFT)`, and separate `Implemented`, `Tested (Mocks/Pytest)`, `Tested with Real LLM`, `Verified vs Ground Truth`, and `Production Eligible`.
   - Verified label-correction metric reversal (`test_10`) and preserved sibling rule `PH_RULE_HEAVY_TCP_HOST_SCAN` untouched (`APPROVED v2`).

### Concrete Empirical Blockers Preventing V8 Approval & Production Readiness Today
1. **Zero Independent Verified Analyst Ground Truth (`0 / 69` in FortiSIEM; `0 / 100` Required):**
   - Exhaustive audit confirmed all `69` incidents are open (`incidentStatus = 0`) with empty `clearedReason`/`resolution`/`comments`. Empirical accuracy, TP recall, FP precision, Wilson 95% LB, and Gate **G8** cannot be measured until SOC analysts submit verified reviews.
2. **Decision Coverage Remained `0 / 6` (`0.0%`) on Both V7 and V8 Under Server 2's `4,096`-Token Context Limit:**
   - Under `4,096` total tokens (`max_tokens = 512`), V8's slightly longer system prompt squeezed `scan.policy_and_service` out of `4/5` rich-log prompts and hit the `512`-token completion cap on `5/5` rich-log responses.
   - Even on `#175129` (where `scan.policy_and_service` was present), `Qwen/Qwen2.5-7B-Instruct-AWQ` conservatively abstained with `0` verified RAG precedents.

---

## Concrete Action Plan to Unblock Decisive Coverage, G8 & Controlled Production

1. **SOC Analyst Operations (Immediate — Required for Ground Truth & RAG):**
   - Review the **32 Tier-1 rich-log incidents** (`16 GDC_NOC` + `16 Demo-SOC`, prioritizing the 4 mixed-internal `Demo-SOC` incidents `#167157`, `#160595`, `#158997`, `#158332`) in the Double-Blind Review Workbench so verified TP/FP examples populate `learning_records` (and verified few-shot RAG precedents become available outside `LOCKED_TEST`).
   - Continue FortiSIEM ingestion until `>= 100` eligible independent verified TP/FP incidents (`>= 25` TP, `>= 50` FP) exist across training and `LOCKED_TEST` partitions.
2. **Server 2 vLLM Configuration (Authorized Maintenance Window — Do NOT Auto-Restart):**
   - Increase vLLM `--max-model-len` on Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ` natively supports `32,768`) from `4,096` to **`8,192`** (or `16,384`). This immediately removes both the `11`-field compaction squeeze (preserving `scan.policy_and_service`, `scan.window_seconds`, `scan.rate_per_second`, `network.destination_ip_list`, and verified RAG precedents) and the `512`-token completion truncation (`allowing 1,024` completion tokens).
3. **Candidate V8/V9 Empirical Gate G8 Evaluation & Promotion:**
   - Re-run `evaluate-simulation` (`provider_type=OPENAI_COMPATIBLE`) against the independent `LOCKED_TEST` partition once verified analyst labels exist.
   - Approve V8 (or V9) ONLY after G8 passes with zero critical missed TPs, `>= 95%` verified accuracy, `>= 99%` FP precision, `>= 96%` Wilson 95% LB, and `>= 95%` TP recall, followed by distinct Administrator promotion approval and separate explicit FP-automation opt-in.

---

## Deliverable Index (`docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/`)

1. [01_V7_ROOT_CAUSE_AUDIT.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/01_V7_ROOT_CAUSE_AUDIT.md)
2. [02_EVIDENCE_ALIGNMENT_REPORT.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/02_EVIDENCE_ALIGNMENT_REPORT.md)
3. [03_CANDIDATE_V8_POLICY.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/03_CANDIDATE_V8_POLICY.md)
4. [04_REAL_LLM_V7_V8_BENCHMARK.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/04_REAL_LLM_V7_V8_BENCHMARK.md)
5. [05_HISTORICAL_GROUND_TRUTH_AUDIT.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/05_HISTORICAL_GROUND_TRUTH_AUDIT.md)
6. [06_ANALYST_FEEDBACK_VALIDATION.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/06_ANALYST_FEEDBACK_VALIDATION.md)
7. [07_EMPIRICAL_ACCURACY_G8_REPORT.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/07_EMPIRICAL_ACCURACY_G8_REPORT.md)
8. [08_UI_AND_SAFETY_VALIDATION.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/08_UI_AND_SAFETY_VALIDATION.md)
9. [09_SERVER_DEPLOYMENT_RESULTS.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/09_SERVER_DEPLOYMENT_RESULTS.md)
10. [10_FINAL_RECOMMENDATION.md](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/10_FINAL_RECOMMENDATION.md)
11. [FINAL_EVIDENCE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_HEAVY_TCP_FIXED_PORT_V8_VALIDATION/FINAL_EVIDENCE.json)
