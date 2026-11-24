# AIS 2.6c — Workstream 1: Offline Evidence & Source Code Reconciliation Report
**Document ID:** `01_AIS_2_6B_EVIDENCE_RECONCILIATION.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Baseline:** AIS 2.6b (`docs/AIS_2_6b/`)  
**Execution Context:** Offline Analysis (GPU Not Required)  
**Authoritative Source Ledger:** `docs/AIS_2_6b/LIVE_EXECUTION_LEDGER.jsonl`  
**Recomputed Output:** `docs/AIS_2_6c/AIS_2_6B_RECOMPUTED_METRICS.json`  
**Discrepancy Register:** `docs/AIS_2_6c/REPORTING_DISCREPANCY_REGISTER.json`  

---

## 1. Executive Summary & Objective

The primary objective of Workstream 1 is to independently recompute, verify, and reconcile all empirical metrics reported during Phase AIS 2.6b directly from the frozen live execution ledger (`LIVE_EXECUTION_LEDGER.jsonl`). An independent audit revealed multiple discrepancies between the narrative executive reports, aggregate summary JSON files, and the underlying row-by-row live inference records.

This investigation establishes a **single authoritative automated metric aggregation engine** that derives all summary counts, rates, and distributions directly from verified execution ledgers, eliminating manual arithmetic, stale carried-over metrics, and invalid zero-denominator calculations.

---

## 2. Authoritative Comparison: Reported vs. Recomputed Metrics

The table below contrasts the metrics published in the AIS 2.6b executive documentation and `BENCHMARK_METRICS.json` against the exact row-by-row recomputation of all 20 records in `LIVE_EXECUTION_LEDGER.jsonl`:

| Metric | AIS 2.6b Executive / JSON Report | Authoritative Recomputation (Ledger) | Variance / Reconciliation Finding |
|---|---:|---:|---|
| **Total Cohort Size** | 20 | 20 | Exact match (10 CrowdStrike, 10 Prisma SASE) |
| **Live GPU Executions** | 20 | 20 | Exact match (all 20 executed via live OpenAI provider) |
| **Original Model Proposed TP** | *Not emphasized* | **20 (100.0%)** | **Critical omission:** Model proposed TP for every incident |
| **Original Model Proposed FP** | 0 | 0 (0.0%) | Zero FP proposals from local LLM |
| **Original Model Proposed RA** | 0 | 0 (0.0%) | Zero RA / abstention proposals from local LLM |
| **Final Authoritative TP** | **8** | **9** | **+1 TP in ledger:** CS incident 132474210 was accepted |
| **Final Authoritative FP** | 0 | 0 | Zero FP final verdicts |
| **Final Authoritative RA** | **12** | **11** | **-1 RA in ledger:** Derived from 20 - 9 = 11 |
| **Decisive Verdicts Count** | **8** | **9** | Matches final TP count (all decisive were TP) |
| **Overall Decisive Coverage** | **40.0%** | **45.0%** | Recomputed: 9 / 20 = 45.0% (vs. 8 / 20 = 40.0%) |
| **CrowdStrike Decisive Count** | **8** | **9** | 9 accepted TPs, 1 rejected to RA (132501348) |
| **CrowdStrike Coverage Rate** | **80.0%** | **90.0%** | Recomputed: 9 / 10 = 90.0% (vs. 8 / 10 = 80.0%) |
| **Prisma SASE Decisive Count** | 0 | 0 | All 10 proposed TPs rejected to RA by validator |
| **Prisma SASE Coverage Rate** | 0.0% | 0.0% | 100.0% abstention rate post-validation |
| **Average Latency** | 32.69 s (32,685.7 ms) | **31.35 s (31,346.05 ms)** | -1.34 s discrepancy from manual unweighted mean |
| **CrowdStrike Avg Latency** | 38,166.4 ms | **37,431.20 ms** | -735.20 ms variance |
| **Prisma SASE Avg Latency** | 27,205.0 ms | **25,260.90 ms** | -1,944.10 ms variance |
| **Average Prompt Tokens** | 4,483.7 | **4,358.60** | -125.10 tokens variance |
| **CrowdStrike Avg Prompt Tok** | 5,462.1 | **5,311.90** | -150.20 tokens variance |
| **Prisma SASE Avg Prompt Tok** | 3,505.3 | **3,405.30** | -100.00 tokens variance |
| **Average Completion Tokens** | 567.6 | **566.35** | -1.25 tokens variance |
| **CrowdStrike Avg Comp Tok** | 569.2 | **566.90** | -2.30 tokens variance |
| **Prisma SASE Avg Comp Tok** | 566.0 | **565.80** | -0.20 tokens variance |
| **Trust Score (Ordinal 1-10)** | Reported as Calibrated / High | **3 / 10 (LOW) for all 20** | Score clamped by missing canonical evidence in payload |
| **Unsafe FP Count** | 0 | 0 | Zero unsafe FPs observed |
| **Unsafe FP Rate** | 0.0% | **null (`NOT_DEMONSTRATED`)** | Denominator is 0 FP predictions; 0/0 is undefined |
| **Certified Ground Truth** | 0 | 0 | Zero certified labels; accuracy status is `NOT_MEASURED` |
| **Execution Git SHA** | `2033c09...` | `2033c09...` (STALE) | Hardcoded fallback from ancient AIS 2.4 |

---

## 3. Discrepancy Root Cause Analysis

### 3.1 Discrepancy 1: Decisive Count (8 Reported vs. 9 Recomputed)
- **Root Cause:** In Phase AIS 2.6a, CrowdStrike decisive count was 8 (8 accepted TPs, 2 abstentions). When Phase AIS 2.6b completed, the reporting script utilized stale aggregate constants rather than dynamically aggregating `LIVE_EXECUTION_LEDGER.jsonl`.
- **Evidence:** Incident `132474210` in `LIVE_EXECUTION_LEDGER.jsonl` line 7:
  ```json
  {"incident_id": "132474210", "raw_proposed_verdict": "TRUE_POSITIVE", "final_authoritative_verdict": "TRUE_POSITIVE", "is_decisive_accepted": true, "validation_status": "VALIDATED"}
  ```
  Only incident `132501348` (line 8) was demoted to `REQUIRES_ATTENTION` (`TP_CRITERIA_UNSATISFIED` for `MEGAsync.exe`). Thus, exactly 9 of 10 CrowdStrike incidents were accepted as decisive TP.

### 3.2 Discrepancy 2: Token and Latency Arithmetic Discrepancies
- **Root Cause:** `BENCHMARK_METRICS.json` reported latency and token averages computed from a preliminary 5-incident pilot run or unweighted category arithmetic rather than the complete 20-row ledger sum.
- **Ledger Verification:**
  - CrowdStrike Prompt Tokens sum: `53,119 / 10 = 5,311.90` (Report: 5,462.1).
  - Prisma SASE Prompt Tokens sum: `34,053 / 10 = 3,405.30` (Report: 3,505.3).
  - Overall Prompt Tokens sum: `87,172 / 20 = 4,358.60` (Report: 4,483.7).
  - CrowdStrike Latency sum: `374,312 ms / 10 = 37,431.20 ms` (Report: 38,166.4 ms).
  - Prisma SASE Latency sum: `252,609 ms / 10 = 25,260.90 ms` (Report: 27,205.0 ms).
  - Overall Latency sum: `626,921 ms / 20 = 31,346.05 ms = 31.35 s` (Report: 32.69 s).

### 3.3 Discrepancy 3: Stale Git SHA (`2033c09...`)
- **Root Cause:** In `backend/app/services/empirical_benchmark_harness.py` lines 878–886:
  ```python
  @classmethod
  def get_active_git_sha(cls) -> str:
      try:
          import subprocess
          res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
          if res.returncode == 0 and res.stdout.strip():
              return res.stdout.strip()
      except Exception:
          pass
      return "2033c09156c68d51ce45ab829f6e691257e995dc"
  ```
  On Server 1 or during containerized evaluation, `git` was either not in `PATH` or the working directory was not a git worktree root. The exception handler silently fell back to the hardcoded SHA `2033c09156c68d51ce45ab829f6e691257e995dc`, which originated from AIS 2.4 (`feat(ais): AIS 2.4 multi-rule verdict evaluation and context expansion`).

### 3.4 Discrepancy 4: Zero Denominator in Unsafe FP Rate
- **Root Cause:** The benchmark harness computed:
  $$\text{Unsafe FP Rate} = \frac{\text{Unsafe FP Count}}{\text{Total FP Predictions}}$$
  When `Total FP Predictions` was 0, the harness returned `0.0%`.
- **Correction:** Under statistical rigor, $\frac{0}{0}$ is undefined. Reporting `0.0%` falsely implies demonstrated safety against false positives when the model in fact made zero false-positive predictions. The rate must be reported as `null` with status `NOT_DEMONSTRATED`.

### 3.5 Discrepancy 5: Trust Score Clamping to 3/10
- **Root Cause:** In `empirical_benchmark_harness.py:1347`, `trust_payload` was constructed as `copy.deepcopy(incident_rec.sanitized_payload)` without appending the normalized canonical evidence records (`norm_result.records`). `EvidenceSufficiencyEngine` searched for canonical dot-notation keys (`process.file_name`, `endpoint.hostname`) and flagged them as missing. This triggered the mandatory guardrail:
  ```python
  if sufficiency.mandatory_fields_missing ...:
      ordinal_score = min(3, ordinal_score)
  ```
  Consequently, all 20 records had their ordinal trust score clamped to 3/10 regardless of evidence quality.

---

## 4. Single Authoritative Aggregation Architecture

To prevent future reporting variances, Phase AIS 2.6c implements a single, authoritative aggregation function:
`EmpiricalBenchmarkHarness.compute_authoritative_metrics(ledger_records)`.

This function:
1. Derives every count directly from record fields (`raw_proposed_verdict`, `final_authoritative_verdict`, `is_decisive_accepted`, `latency_ms`, `prompt_tokens`, `completion_tokens`).
2. Disallows hardcoded fallback strings in summary generation.
3. Explicitly handles zero denominators by emitting `null` with standardized status strings (`NOT_MEASURED`, `NOT_DEMONSTRATED`).
4. Generates both machine-readable JSON and Markdown table outputs from the exact same internal data structure.

---

## 5. Deliverable References

- Recomputed metrics: [AIS_2_6B_RECOMPUTED_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/AIS_2_6B_RECOMPUTED_METRICS.json)
- Discrepancy register: [REPORTING_DISCREPANCY_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/REPORTING_DISCREPANCY_REGISTER.json)
- Source ledger: [LIVE_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6b/LIVE_EXECUTION_LEDGER.jsonl)
