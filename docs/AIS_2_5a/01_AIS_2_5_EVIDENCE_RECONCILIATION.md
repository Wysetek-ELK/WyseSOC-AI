# 01 — AIS 2.5 Evidence Reconciliation & Forensic Audit

## 1. Executive Summary

During the AIS 2.5a audit phase, an exhaustive forensic examination was conducted on all execution records, markdown reports, deployment logs, and machine-readable evidence under `docs/AIS_2_5/`. The objective was to investigate, reconcile, and resolve every reported discrepancy between published narratives and recalculable underlying artifacts without fabricating data.

All discrepancies have been resolved through programmatic verification against authoritative runtime traces.

---

## 2. Itemized Discrepancy Reconciliation Matrix

| Finding / Metric | AIS 2.5 Reported Narrative | Recalculated / Authoritative Value | Root Cause & Resolution |
|---|---|---|---|
| **Raw Model TP Proposals** | 6 | **5** (or 4 in authentic live 4k run) | Table in `04_AUTHENTICATED_LIVE_BENCHMARK.md` had 5 rows marked `TRUE_POSITIVE`. The narrative claimed 6 due to miscounting incident 132474210 which proposed `REQUIRES_ATTENTION`. |
| **Raw Model FP Proposals** | 11 | **12** (in reported 8k table) / **0** (in authentic live 4k run) | Summing rows in `04_AUTHENTICATED_LIVE_BENCHMARK.md` table yields 12 FP rows, not 11. In live 4k vLLM execution, Prisma incidents are intercepted by TokenBudgetService, yielding 0 proposals. |
| **Raw Abstentions** | 3 | **3** (in reported 8k table) / **16** (6 model + 10 preflight in live 4k run) | Reconciled. Narrative counted 3 explicit abstentions for CrowdStrike. |
| **Total Benchmark Tokens** | 78,826 | **79,568** (table sum) / **74,853** (authentic live run) | Summing prompt (71,122) and completion (8,446) from `docs/AIS_2_5` table rows equals 79,568. The reported 78,826 omitted 742 tokens from an earlier draft run. |
| **Pilot Metrics Discrepancy** | Reported consistent | Discrepancies between JSON and Markdown | `scratch/five_incident_pilot_results.json` showed incidents 132499009, 132499023, and 132499745 halted with `TOKEN_BUDGET_GUARD` (latency ~450ms, 0 completion tokens). `docs/AIS_2_5/FINAL_EVIDENCE.json` substituted completions from an offline run. |
| **Wilson Interval for 0/2 Coverage** | 0% – 16.84% | **0.00% – 65.76%** (exact 95% Wilson CI for N=2, k=0) | The reported 0–16.84% is the Wilson score interval for $k=0, N=20$. For the 2-incident certified cohort ($N=2, k=0$), the true mathematical Wilson interval is [0.00%, 65.76%]. |
| **Benchmark Application SHA** | c9a2a17 | Final deployment **6434940** (AIS 2.5), now **ff0a4c2** (AIS 2.5a) | `c9a2a17` was an intermediate commit. Deployment logs on Server 1 confirmed checkout at `64349401c6165c23d49a549924fabb128699b9d8`. |
| **Certified Ground Truth** | 2 FP | **PROVISIONAL_UNVERIFIED** (prov: 0 certified) | Historical SIEM field `clearedUser` is empty (`""`) for all 20 incidents. Labels were operational resolution tags, not independent double-blind human certifications. |
| **Provider Execution Evidence** | 20 Live Executions | **10 Live GPU Executions + 10 Token Guard Intercepts** | Server 2 vLLM is running with `--max-model-len 4096`. 10 CrowdStrike incidents executed live on GPU; 10 Prisma incidents were safely intercepted by `TokenBudgetService` (wire tokens > 3328 budget). |

---

## 3. Forensic Investigation of Incidents 132499009, 132499023, 132499745

These three Prisma SASE incidents were the primary source of divergence across AIS 2.5 artifacts:
1. **Pilot Artifact (`scratch/five_incident_pilot_results.json`)**:
   - `execution_provenance`: `TOKEN_BUDGET_GUARD`
   - `latency_ms`: 445ms – 454ms
   - `prompt_tokens`: 3709, 3747, 3701
   - `completion_tokens`: 0
   - `proposed_verdict`: None (`CONTEXT_WINDOW_EXCEEDED`)
2. **Benchmark Report (`04_AUTHENTICATED_LIVE_BENCHMARK.md`)**:
   - Reported as `FALSE_POSITIVE` proposals with ~400 completion tokens and ~15s latency.
3. **Resolution**:
   The discrepancies were caused by mixing an offline 8k token test run into the live benchmark report. In the live production environment, Server 2 vLLM has an active context window of 4,096 tokens. The compiled Prisma SASE policy requires 3,709 wire tokens, exceeding the 3,328 available input budget. Server 1's `TokenBudgetService` strictly and correctly halted these incidents to preserve evidence integrity.

All original AIS 2.5 artifacts have been preserved unaltered in `docs/AIS_2_5/`. Corrected figures are now compiled exclusively from `docs/AIS_2_5a/LIVE_EXECUTION_LEDGER.jsonl`.
