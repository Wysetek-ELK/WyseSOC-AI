# AIS 3.1 Executive Summary

**Product:** Verdictum AI — Agentic SOC Intelligence (WYSETEK)  
**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100` (`100` incidents across `30` FortiSIEM rule families)  
**Benchmark Grade:** `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` (`100` locked GT-2 single-review by `admin`, `0` GT-3)  
**Primary Acceptance Status:** **`FAIL_INTELLIGENCE`**  
**Ready for AIS 4.0:** **`NO`** (`production_autonomy_approved = false`)

---

## 1. Key Findings & Acceptance Decision

1. **100% Execution, Integrity, UI & Security Pass (`G01–G18 PASS`):**
   - All `100` locked human reviews in `AIS_3_0_INDEPENDENT_HOLDOUT_100` were reconciled and preserved intact (`80 FP, 18 TP, 2 INCONCLUSIVE`, `0` conflicts, `100/100 BLIND_ENFORCED`).
   - Root-caused `Exposure Risk: 100` (`inc.ground_truth is not None` even on 85 empty-resolution rows) into `25 VERIFIED_NO_DETECTED_EXPOSURE`, `75 HISTORICAL_LABEL_EXISTS_BUT_MASKED`, `0 CONFIRMED_EXPOSURE` (`0/100` in `LearningRecord`, `ActualLLMPromptCapture`, or `AIS_2_6E_FROZEN_20`).
   - Pilot wire inspection exposed and fixed an evidence-plumbing bug where `54/100` aggregated FortiSIEM incidents sent `"events": []` instead of falling back to sanitized `Incident.raw_payload`, and hardened the leakage sanitizer to strip `incidentReso` and historical ML `confidence`.
   - Executed `100/100` real live GPU inferences on **Server 2 `Qwen/Qwen3-14B-AWQ`** (`vLLM 0.33.0`, `8192` context / `768` completion, `0` overflows, `0` technical failures, `60.30s` avg latency, Server 2 untouched/unrestarted) and deployed validated UI & API changes to Server 1 (`8c760c3b9f7957ad4283678ff1f8d1a31dd5dd96`).
2. **Empirical Multi-Rule Intelligence Deficit (`FAIL_INTELLIGENCE`):**
   - **Raw LLM (`Qwen/Qwen3-14B-AWQ`, frozen `NEUTRAL_SOC_BASELINE_V2`):** `25.0%` decision coverage (`25/100`), `48.0%` conclusive accuracy (`12/25`, 95% CI `[30.03%, 66.50%]`), `12.0%` end-to-end correct rate (`12/100`), **`0.0%` TRUE_POSITIVE recall** (`0/6` conclusive; `6` False Negatives + `12` Raw abstentions across `18` GT TPs), **`31.58%` balanced accuracy**, underperforming the majority-class (`ALWAYS_FALSE_POSITIVE`: `81.63%`) baseline.
   - **Validated Application (`IndependentVerdictValidator`):** Overrode `24/25` conclusive Raw LLM verdicts to `REQUIRES_ATTENTION`, yielding `1.0%` decision coverage (`1/100`, FID `6016`), `100.0%` conclusive accuracy (`1/1`), `1.0%` end-to-end correctness (`1/100`).
3. **Why AIS 4.0 Must Wait:**
   - The zero-shot neutral prompt under-specified FortiSIEM operational vs. attack semantics (`75%` Raw abstention + `4/6` operational/config FNs), scan alerts lacked organizational scanner allowlists (`6/7` FP overcalls), and `IndependentVerdictValidator`'s CrowdStrike/Prisma criteria rejected `96%` (`24/25`) of decisive LLM outputs.
   - Because AIS 3.0's 100 incidents have now been evaluated once and error causes analyzed, **future prompt/validator remediation must develop on a separate dataset and validate on a fresh untouched holdout cohort alongside dual-reviewer GT-3 certification**.
