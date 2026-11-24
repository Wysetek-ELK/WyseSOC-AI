# AIS 2.6a — Report 05: Empirical 5-Incident GPU Benchmark Pilot

## 1. Pilot Cohort Design and Execution
Prior to full cohort execution, a 5-incident live GPU pilot was executed against Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ` at `8192` context window).

### Pilot Results Summary

| Incident ID | Rule Name | Prompt Tokens | Comp Tokens | Finish Reason | Layer A Verdict | Layer B Validator | Final Verdict | Decisive | Latency |
|---|---|---:|---:|---|---|---|---|:---:|---:|
| **132438483** | Crowdstrike: Suspicious Activity | 5,717 | 506 | `stop` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** | 44.2s |
| **132474210** | Crowdstrike: Suspicious Activity | 6,918 | 470 | `stop` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** | 43.5s |
| **132499009** | Prisma SASE: Suspicious File Threat | 3,560 | 463 | `stop` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** | 40.1s |
| **132599145** | Prisma SASE: Suspicious File Threat | 3,857 | 455 | `stop` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** | 20.0s |
| **132501348** | Crowdstrike: Suspicious Activity | 4,412 | 545 | `stop` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** | 56.2s |

---

## 2. Key Findings and Verification
1. **8K Capacity Verified:** 100% of pilot prompts (3,560 to 6,918 tokens) exceeded the previous 3,328-token budget. All 5 executed successfully without truncation (`finish_reason=stop`).
2. **Decisive Coverage:** 4 out of 5 incidents (80.0%) achieved valid decisive verdicts.
3. **Layer Separation:** Incident `132501348` demonstrated layer separation: the model proposed TP, but the validator intercepted with `TP_CRITERIA_UNSATISFIED` due to sparse telemetry (2 events), safely defaulting to `REQUIRES_ATTENTION`.
4. **Safety & Double-Blind:** No historical analyst resolutions were exposed to the model.
