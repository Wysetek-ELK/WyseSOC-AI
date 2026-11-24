# AIS 2.6e — Executable Benchmark Harness & Execution Architecture

**Document Identifier:** `08_EXECUTABLE_BENCHMARK_HARNESS_VALIDATION.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / FROZEN  
**Target Module:** `backend/app/services/benchmark_harness.py`  
**Related Manifests:** [BENCHMARK_EXECUTION_PLAN.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/BENCHMARK_EXECUTION_PLAN.json), [GPU_WORKLOAD_AND_COST_ESTIMATE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/GPU_WORKLOAD_AND_COST_ESTIMATE.json), [BENCHMARK_RESUMPTION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/BENCHMARK_RESUMPTION_MANIFEST.json)

---

## 1. Executive Summary & Harness Architecture

The Benchmark Execution Harness (`backend/app/services/benchmark_harness.py`) is the core execution engine responsible for orchestrating live evaluation calls against the remote vLLM endpoint on Server 2 (`http://13.204.214.64:8000/v1`).

In previous phases, benchmark executions relied on offline simulated mock providers. In AIS 2.6e, the harness has been engineered and validated to enforce strict live execution safeguards, precise token accounting, deterministic wire formatting, and robust circuit breaking.

```
+-------------------------------------------------------------------------------+
|                       AIS 2.6e BENCHMARK HARNESS                              |
|                                                                               |
|  +--------------------+    +--------------------+    +---------------------+  |
|  | Request Pacing     |    | Circuit Breaker    |    | Execution Ledger    |  |
|  | Inter-call: 1000ms |    | 2x 5xx -> HALT     |    | Append-only JSONL   |  |
|  | Timeout: 30s       |    | 2x Timeout -> HALT |    | Full raw audit trail|  |
|  +--------------------+    +--------------------+    +---------------------+  |
|                               |                                               |
|                               v                                               |
|                    [ POST /v1/chat/completions ]                              |
|                               |                                               |
+-------------------------------|-----------------------------------------------+
                                | (Authenticated Wire Protocol)
                                v
               +----------------------------------+
               |   Server 2: vLLM GPU Endpoint    |
               |   Model: Qwen2.5-7B-Instruct-AWQ |
               |   Port: 8000                     |
               +----------------------------------+
```

---

## 2. Recalculated GPU Workload & Cost Budget

In historical documentation, speculative call counts ranged from 80 to over 200 calls. For AIS 2.6e, the exact required GPU inference workload has been mathematically audited and budgeted across the frozen 20-incident cohort:

| Stage / Component | Incidents Evaluated | Mode | Calls per Incident | Total Calls |
| :--- | :--- | :--- | :--- | :--- |
| **0. Smoke Test** | 1 synthetic test incident | Connectivity validation | 1 | **1** |
| **1. Pilot Stage** | 5 priority incidents | Mode A (Neutral) | 1 | **5** |
| | 5 priority incidents | Mode B (Approved Policy) | 1 | **5** |
| **2. Cohort Completion**| 15 remaining incidents | Mode A (Neutral) | 1 | **15** |
| | 15 remaining incidents | Mode B (Approved Policy) | 1 | **15** |
| **3. Mode C Validation**| All 20 incidents | Mode C (Deterministic) | 0 (Local CPU) | **0** |
| **Total Baseline Workload** | **20 Incidents** | **Modes A + B + C** | — | **41 Calls** |
| *Optional Counterfactuals*| 5 selected incidents | Invariance testing | 2 | *10* |
| **Max Authorized Ceiling** | — | — | — | **51 Calls** |

### 2.1 GPU Runtime & Financial Cost Breakdown
* **Inference Hardware:** AWS EC2 `g5.xlarge` (1x NVIDIA A10G 24GB GPU).
* **On-Demand Hourly Rate:** **\$1.006 USD/hour** (AWS US-East/AP-South pricing).
* **Estimated Execution Time:**
  * 41 requests $\times$ ~5–8 seconds average response time $\approx$ 205–328 seconds.
  * Inter-request pacing delay (1.0s) $\approx$ 41 seconds.
  * Setup, health checks, and checkpoint verification $\approx$ 300 seconds.
  * **Total GPU Server Active Time:** $\approx$ 15–20 minutes (0.25–0.33 hours).
* **Total Estimated Financial Cost:**
  $$\text{Estimated Cost} = 0.33 \text{ hours} \times \$1.006/\text{hour} \approx \mathbf{\$0.33\text{ USD}}$$
  *(Maximum theoretical cost with counterfactuals $\le \$0.50$ USD).*

---

## 3. Resilience, Circuit Breakers & Timeout Controls

To protect system integrity and prevent runaway cloud billing, the harness incorporates hard automated circuit breakers:

1. **Request Timeout:** Fixed at **30.0 seconds** per inference request.
2. **Retry Protocol:** Maximum of **3 retries** with exponential backoff ($1.0s, 2.0s, 4.0s$) strictly for transient HTTP `429` (Rate Limited) or socket reset errors.
3. **Hard Circuit Breaker:**
   * **Condition:** **Two (2) consecutive HTTP 5xx errors** (e.g., vLLM internal CUDA crash, OOM) OR **two (2) consecutive request timeouts**.
   * **Action:** Immediate process abort (`EXIT_CIRCUIT_BROKEN`). No further inference calls are dispatched. State is written to `BENCHMARK_RESUMPTION_MANIFEST.json`.
4. **Inter-Call Pacing:** Mandatory **1,000 ms (1.0s) sleep** between sequential requests to prevent GPU queue starvation and monitor thermal/VRAM stability.

---

## 4. Execution Telemetry & Ledger Integrity

Every individual live request is recorded to an append-only JSONL ledger (`PILOT_EXECUTION_LEDGER.jsonl`, `MODE_A_LIVE_EXECUTION_LEDGER.jsonl`, `MODE_B_LIVE_EXECUTION_LEDGER.jsonl`) capturing mandatory empirical telemetry:
- `request_id`: Server-generated UUID from vLLM.
- `incident_id`: Unique identifier of the incident evaluated.
- `mode`: `MODE_A_NEUTRAL` or `MODE_B_APPROVED_POLICY`.
- `prompt_tokens`: Actual prompt tokens measured by vLLM tokenizer.
- `completion_tokens`: Actual output tokens generated.
- `latency_ms`: Exact wall-clock duration from socket write to socket read completion.
- `model_id`: Exact string returned in vLLM response (`Qwen/Qwen2.5-7B-Instruct-AWQ`).
- `raw_response`: Complete verbatim JSON output from vLLM.
- `execution_timestamp_utc`: ISO 8601 UTC timestamp.

Simulated responses (`is_live_measurement = false`, `OFFLINE_SIMULATION`) are strictly prohibited from entering these ledgers.

---

## 5. Resumption and Checkpoint Recovery

The benchmark harness supports deterministic state resumption:
- If execution is interrupted after request $N$, state is preserved in `BENCHMARK_RESUMPTION_MANIFEST.json`.
- Upon re-invocation with the `--resume` flag, the harness inspects the existing ledger, verifies cryptographically that existing records match the cohort manifest, and resumes precisely at request $N+1$.
- Zero duplicate requests are sent to the GPU server.
