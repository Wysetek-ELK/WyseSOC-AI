# AIS 2.6e — Five-Incident Actual GPU Pilot Specification

**Document Identifier:** `13_FIVE_INCIDENT_ACTUAL_GPU_PILOT.md`  
**Phase:** AIS 2.6e  
**Status:** SPECIFICATION / READY FOR EXECUTION  
**Pilot Target:** 5 Priority Incidents (10476, 10477, 10478, 10479, 10480)  
**Related Manifests:** [GROUND_TRUTH_REVIEW_QUEUE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/GROUND_TRUTH_REVIEW_QUEUE.json), [BENCHMARK_EXECUTION_PLAN.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/BENCHMARK_EXECUTION_PLAN.json)

---

## 1. Executive Summary & Pilot Purpose

The Five-Incident Actual GPU Pilot is the initial live evaluation gate designed to validate the end-to-end execution pipeline on real GPU hardware before committing the full 20-incident cohort.

The pilot executes exactly **10 live GPU calls** (5 in Mode A Neutral, 5 in Mode B Approved Policy) across the 5 priority incidents.

---

## 2. Priority Incident Cohort

The pilot cohort consists of 5 real FortiSIEM incidents exhibiting distinct behavioral patterns:

| Incident ID | Rule Name | Verified SQLite Entity | Reason for Priority Inclusion |
| :--- | :--- | :--- | :--- |
| **10476** | `Crowdstrike-Falcon-Host-Block-Detected` | `UltraViewer_Service.exe` | Priority 1: Baseline administrative remote tool block. |
| **10477** | `Crowdstrike-Falcon-Host-Block-Detected` | `UltraViewer_Service.exe` | Priority 2: Verifies consistency across identical binary. |
| **10478** | `Crowdstrike-Falcon-Host-Block-Detected` | `MEGAsync.exe` | Priority 3: Cloud sync utility test case. |
| **10479** | `Prisma-SASE-Security-Alert` | `update.exe` | Priority 4: SASE binary execution download alert. |
| **10480** | `Prisma-SASE-Security-Alert` | `review.es.system.js` | Priority 5: Web script script-alert test case. |

---

## 3. Pilot Execution Protocol

1. **Pre-requisite:** Certified human review recorded in `analyst_verdict_reviews` for all 5 incidents.
2. **Pacing:** Strict 1,000 ms sleep between requests.
3. **Execution Order:**
   - Incident 10476: Mode A, then Mode B.
   - Incident 10477: Mode A, then Mode B.
   - Incident 10478: Mode A, then Mode B.
   - Incident 10479: Mode A, then Mode B.
   - Incident 10480: Mode A, then Mode B.
4. **Telemetry Logging:** Every call appends verbatim output to `PILOT_EXECUTION_LEDGER.jsonl`.

---

## 4. Pilot Pass/Fail Stop Conditions

Execution immediately HALTS if any of the following occur:
- **Crash/OOM:** Any HTTP 500/503 from vLLM.
- **Context Overflow:** Any prompt rejected for exceeding context limit.
- **Malformed Output:** Model output fails JSON schema parsing.
- **Zero Decisive Output:** If 5 of 5 Mode A prompts return `INCONCLUSIVE` without attempting analysis.

If all 10 calls succeed, telemetry is evaluated against the 5 certified human reviews. If pilot accuracy $\ge 60\%$ or provides actionable error attribution, the benchmark proceeds to the remaining 15 incidents.
