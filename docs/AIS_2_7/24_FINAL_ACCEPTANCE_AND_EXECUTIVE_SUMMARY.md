# AIS 2.7 — Final Acceptance & Executive Summary

**Organization:** Wysetek Systems Technologists Pvt. Ltd. | **Application:** Verdictum AI  
**Phase:** AIS 2.7 (Live GPU Benchmark & Model Intelligence Evaluation) | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [FINAL_EVIDENCE.json](FINAL_EVIDENCE.json), [BENCHMARK_EXECUTION_SUMMARY.json](BENCHMARK_EXECUTION_SUMMARY.json), [NEXT_PHASE_DECISION.json](NEXT_PHASE_DECISION.json)

---

## 1. Separate Top-Level Verdicts

| Evaluation Dimension | Final Status | Basis |
|---|---|---|
| **Benchmark Execution Status** | **PASS (`COMPLETED_AND_VALIDATED`)** | `41/41` live GPU calls + `1` gateway 504 retry; `20/20` incidents completed; `40/40` schema-valid JSON; `0` context overflows; `0` DB mutations; `61` pytest passing. |
| **Model Capability Status** | **FAIL (`UNSUITABLE`)** | `Qwen/Qwen2.5-7B-Instruct-AWQ` achieved `1/20 (5.0%)` in Mode A and `2/20 (10.0%)` in Mode B vs GT-2, collapsed completely to `FALSE_POSITIVE` in Mode A, and hallucinated across `20/20` Mode B responses. |
| **Production Readiness Status** | **NOT READY (`BLOCKED`)** | Blocked by model failure (`BLK-01`), absent GT-3 certification (`BLK-02`), Prisma SASE policy template mismatch (`BLK-03`), and missing external hash enrichment (`BLK-04`). |

---

## 2. Direct Empirical Answers to All 40 Executive Questions

1. **Authoritative database & environment used:** Server 1 PostgreSQL (`http://172.26.41.240`, commit `1e099d5b5954f6921e154ce124d04e604f466d9e`) holding the `20` frozen cohort incidents and active approved rules.
2. **Authoritative GT-2 status:** `20/20` locked single-reviewer (`admin`) GT-2 reviews (`9 TRUE_POSITIVE`, `1 FALSE_POSITIVE`, `10 INCONCLUSIVE`); `0/20` GT-3 dual-certified; `20/20` historical exposure markers.
3. **Dataset independence:** Exploratory GT-2 only; correlated across `2` detection rules (`10` CrowdStrike, `10` Prisma SASE) and `2` customers; cannot claim uncontaminated production holdout.
4. **Deployed Server 2 model & runtime:** `vLLM 0.33.0` serving `Qwen/Qwen2.5-7B-Instruct-AWQ` with `max_model_len = 8192` on `http://13.204.214.64:8000/v1` (EC2 GPU hardware unverified from HTTP telemetry).
5. **Runtime limits & truncation:** `max_model_len = 8192`, benchmark `max_completion_tokens = 768`; `0/40` overflows and `0/40` `length` truncations (max `7,197` total tokens on `132461358` Mode B).
6. **Human-only evidence gaps:** Proven on `132501348` (`MEGAsync.exe`), where GT-2 analyst verified external executable hash reputation (`clean`) absent from incident logs/prompts.
7. **Evidence preservation & token compliance:** `100%` of required Evidence Contract fields preserved; `0` dropped incidents; max Mode A input `5,748`, Mode B input `6,724` live tokens.
8. **Zero label leakage verified:** `0` GT-2 labels, `0` historical FortiSIEM verdicts, and `0` operational AI verdicts in any wire prompt.
9. **Smoke test pass:** HTTP `200`, `chatcmpl-969d0b6172c8e3a4`, `43+14=57` tokens, `406.98ms`.
10. **Priority Pilot (`N=5`) passed execution:** `10/10` GPU calls succeeded; early `0/5` Mode A accuracy observed; authorized full cohort.
11. **Full cohort (`N=20`) completed cleanly:** `20/20` incidents completed across Modes A, B, and C with `41` live GPU calls + `1` HTTP 504 retry (`132499009` before single-mode split).
12. **Mode A 3-class accuracy (`N=20`):** **`1/20 (5.0%, 95% CI 0.89%-23.61%)`** (`0/9` TP, `1/1` FP, `0/10` `INCONCLUSIVE`).
13. **Mode A binary accuracy (`N=10` CrowdStrike):** **`1/10 (10.0%)`**, `100%` decision coverage (`0/9` TP recall, `1/1` FP recall by `100%` FP class collapse).
14. **Mode B raw 3-class accuracy (`N=20`):** **`2/20 (10.0%, 95% CI 2.79%-30.10%)`** (`2/9` TP, `0/1` FP, `0/10` `INCONCLUSIVE`).
15. **Mode B raw binary accuracy (`N=10`):** **`2/10 (20.0%)`** at `30% (3/10)` coverage (`2/3 = 66.67%` conditional decisive accuracy; `7/10` abstentions).
16. **Mode C validator-assisted 3-class accuracy (`N=20`):** **`9/20 (45.0%, 95% CI 25.82%-65.79%)`** via `validated_verdict` (`1/9` TP, `0/1` FP, `8/10` `INCONCLUSIVE`), and **`10/20 (50.0%)`** via `effective_trust_verdict` (`20/20` `REQUIRES_ANALYST_ATTENTION`).
17. **Mode C binary accuracy (`N=10`):** **`1/10 (10.0%)`** at `10% (1/10)` coverage (`1/1 = 100%` conditional decisive accuracy; `9/10` abstentions).
18. **Mode A vs Mode B impact:** Policy changed `11/20` verdicts (`+5%`, `p = 1.0`) by rescuing `2` UltraViewer TPs (both still flawed in reasoning), shifting `7` UltraViewer TPs into false `process.command_line is missing` abstentions, regressing `132501348` (`FP -> TP`), and pushing `132499745` (`INCONCLUSIVE -> TP`).
19. **Mode B vs Mode C validator impact:** Significant lift (`10% -> 45%`, exact McNemar `p = 0.0391`); blocked `8/10` ungrounded Prisma decisive verdicts, blocked `132501348` FP-as-TP error, and caught `7/7` contradictory missing-field claims.
20. **True Positive recall (critical SOC metric):** Mode A **`0/9 (0.0%)`**, Mode B **`2/9 (22.22%)`**, Mode C **`1/9 (11.11%)`**.
21. **Missed-TP-as-FP suppression rate:** Mode A **`9/9 (100.0%)`** (catastrophic silent-miss risk); Mode B **`0/9 (0.0%)`**; Mode C **`0/9 (0.0%)`**.
22. **False Positive precision & FP-as-TP errors:** Mode A FP precision `1/20 (5.0%)`, FP-as-TP `0/1`; Mode B FP precision `0/9 (0.0%)`, FP-as-TP **`1/1 (100.0%)`** (`132501348`); Mode C FP precision `0/2 (0.0%)`, FP-as-TP **`0/1 (0.0%)`**.
23. **Abstention accuracy on Prisma SASE (`10 INCONCLUSIVE`):** Mode A **`0/10 (0.0%)`**, Mode B **`0/10 (0.0%)`**, Mode C **`8/10 (80.0%)`**.
24. **Did any mode fabricate claims/rationales?** Yes — `20/20` Mode B runs had either mechanical validator flags (`10` hallucinations, `7` contradictions) or audited semantic/prose hallucinations (`0/20` completely hallucination-free).
25. **Exact hallucination examples observed:** Calling `Program Files (x86)` a `"writable temporary path"` (`132439932`), claiming `process.command_line` is missing (`7/9` CS), asserting `"Binary not signed"` citing `process.name` (`132527297`), calling public IPs `13.35.36.32` & `3.109.76.166` `"internal"`, calling RFC-1918 `172.25.14.67` `"not internal"`, and inventing `"No suspicious process execution detected"` citing blank `process.file_name`.
26. **Validator false rejections vs justified rejections:** `1` Mode B GT-matching verdict (`132527297` `TRUE_POSITIVE`) was downgraded -> **0 substantive validator bugs**, because Mode B actually hallucinated `"Binary not signed"` without signature telemetry.
27. **Validator blindspots found:** Missed narrative `"writable temporary path"` contradiction inside `132439932` `claim_text`, and leaked `2/10` Prisma FPs (`132599145`, `132499023`) whose claim fields superficially matched while prose assumed benignity/misread IPs.
28. **Confidence calibration:** Completely broken in raw LLM — Mode A returned exact `85%` on `20/20` calls (`19/19` errors overconfident); Mode B returned `>=80%` on `11/18` errors (up to `95%`).
29. **CrowdStrike vs Prisma SASE rule comparison:** Mode B CrowdStrike `2/10 (20%)`, Mode C CrowdStrike `1/10 (10%, 9 abstained)`; Mode B Prisma `0/10 (0%)`, Mode C Prisma `8/10 (80% rescued to REQUIRES_ATTENTION)`.
30. **Did Approved Policy `ed7ff3c7` v1 help or hurt Prisma SASE?** Actively hurt — it uses a mismatched EDR/web-loopback template barring `REQUIRES_ATTENTION` on network logs without process fields.
31. **Parser/schema health:** `40/40 (100%)` pure valid JSON (`0` parser errors, `0` truncated outputs).
32. **Did Server 1 operational UI match benchmark metrics?** Reconciled cleanly: Verdict Intelligence shows `200` historical incidents at `REQUIRES_ANALYST_ATTENTION` (`trust <= 6`, `avg=5.3`, `measured_accuracy=null`, `UNCALIBRATED`), agreeing with Mode C's `20/20` trust `< 7` escalation while remaining completely isolated from GT-2 benchmark writes.
33. **Operational DB & LearningRecord isolation verified:** `0` operational incident changes across `20` UUIDs, `0` GT queue diffs, `0` rule changes, `0` `LearningRecord` writes.
34. **Regression tests passed after final deploy:** `61 passed, 0 failed` (`22.95s`) across 9 backend pytest suites + Server 1 UPLA verification.
35. **GPU budget, tokens, and wall-clock generation time:** `41` successful calls + `1` gateway retry (`132499009`), `208,474` total tokens, `1,716.83s` cumulative inference latency; billing dollars unverified (`gpu_telemetry_verified=false`).
36. **GPU Server 2 post-benchmark state:** `active_concurrent_slots = 0`, `live_triage_queue_depth = 0`, Server 2 intentionally **LEFT RUNNING** per Checkpoint A rule — operator must shut it down manually.
37. **Core model suitability verdict:** **`Qwen/Qwen2.5-7B-Instruct-AWQ` is UNSUITABLE** for autonomous or policy-assisted Verdictum AI SOC triage (`5%` Mode A / `10%` Mode B).
38. **Should we tune prompts on `Qwen2.5-7B-Instruct-AWQ` or replace the model?** **Replace/upgrade the model** (alongside fixing Prisma policy `ed7ff3c7` and adding deterministic hash/IP enrichment). Further prompt engineering on a 7B-AWQ model exhibiting field-presence blindness and IP-range inversion has diminishing/negative returns.
39. **Should we keep Verdictum AI's deterministic Validator + Evidence Contract architecture?** **Yes** — Mode C proved essential as a deterministic safety firewall (`p = 0.0391`, `0/9` missed-TP-as-FP, `0/1` FP-as-TP, `8/10` inconclusive rescue) and only requires narrative/IP/path hardening.
40. **Was AIS 2.8 started automatically?** **No.** AIS 2.7 halted cleanly at conclusion pending operator review and GPU Server 2 shutdown.
