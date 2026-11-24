# AIS 2.6d — Deliverable 05: Actual GPU Runtime, Connectivity & Checkpoint B Specification

**Phase:** VERDICTUM AI — AIS 2.6d  
**Evaluator Roles:** Infrastructure & Security Architect, Principal AI/LLM Engineer, Deployment Governance Auditor  
**Date:** November 24, 2026  
**Status:** AUDITED — BLOCKED PENDING GPU AUTHORIZATION (CHECKPOINT B ACTIVE)  
**Target Host:** AWS GPU Server 2 (`13.204.214.64:8000`)  
**Referenced Workstream:** Workstream 4 (GPU Runtime Truth and Actual Connectivity)  

---

## 1. Executive Summary & GPU Governance Contract

To achieve true empirical accuracy measurement, Verdictum AI must connect to the live GPU inference engine running on **GPU Server 2** (AWS EC2 instance). In Phase AIS 2.6c, all reported Three-Mode evaluations were conducted using offline deterministic simulations because GPU Server 2 was unreachable.

Under Phase AIS 2.6d Non-Negotiable Requirements:
- **Requirement 1:** Never fabricate GPU inference results.
- **Requirement 2:** Never substitute simulated responses for live LLM responses.
- **Requirement 9:** Never use successful HTTP responses as proof of correct inference.
- **Requirement 18:** **Never automatically start, stop, resize, or replace billable GPU infrastructure.**

During technical preflight, an automated probe was executed against `http://13.204.214.64:8000/v1/models`. The connection timed out after 5,000 ms. Conforming strictly to Rule 18, the agent did not execute any AWS CLI, API, or cloud infrastructure commands to start the instance automatically. All GPU-dependent workstreams (Pilot, Full Benchmark, Counterfactual Remediation) are formally marked **`BLOCKED_GPU_UNAVAILABLE`** until the operator starts the server.

---

## 2. Target GPU Runtime Specification

When started, GPU Server 2 operates the following inference architecture:

| Component | Target Runtime Value | Verification Method |
|---|---|---|
| **Host IP & Port** | `13.204.214.64:8000` | TCP Socket & HTTP `/v1/models` |
| **Inference Framework** | `vLLM` (v0.6.3+ / OpenAI-Compatible API) | `/v1/models` JSON response |
| **Loaded Model** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Model identifier string |
| **Weight Quantization** | `AWQ` (4-bit activation-aware weight quantization) | Configuration manifest |
| **Maximum Model Context** | `8192` tokens | Token budget preflight validator |
| **Target Input Budget** | `7424` tokens ($8192 - 768$) | `TokenBudgetService` ceiling |
| **Max Output Tokens** | `768` tokens | Request parameter `max_tokens` |
| **Chat Template** | `qwen2` (ChatML style `<\|im_start\|>`) | vLLM internal template |
| **Sampling Parameters** | `temperature=0.0`, `top_p=1.0`, greedy decoding | OpenAI-compatible payload |

---

## 3. Connectivity Probe & Smoke Test Outcome

A minimal HTTP probe was executed:
- **Timestamp:** 2026-11-24T16:09:00Z
- **Target Endpoint:** `http://13.204.214.64:8000/v1/models`
- **Socket Result:** `ConnectTimeout (Connection timed out after 5000 ms)`
- **Smoke Test Determination:** **`BLOCKED_GPU_UNAVAILABLE`**
- **Mock Fallback Handling:** Disabled (`LOCAL_LLM_ALLOW_MOCK_FALLBACK = False`). No fallback response was manufactured.

---

## 4. Estimated GPU Inference Workload (Sizing Analysis)

To prevent unnecessary AWS EC2 hourly billing, the entire experimental workload is bounded and sized upfront:

| Experimental Phase | Mode | Requests | Est. Tokens / Req | Est. Duration |
|---|---|---|---|---|
| **Smoke Test** | Diagnostic Ping | 1 | ~500 | ~5 seconds |
| **Pilot (5 Priority Cases)** | Mode A (Neutral Baseline) | 5 | ~3,000 | ~2 minutes |
| **Pilot (5 Priority Cases)** | Mode B (Approved Policy) | 5 | ~4,500 | ~3 minutes |
| **Pilot (5 Priority Cases)** | Mode C (Validator) | **0** (Zero GPU calls) | 0 | 0 seconds |
| **Complete Benchmark** | Mode A (Remaining 15) | 15 | ~3,000 | ~6 minutes |
| **Complete Benchmark** | Mode B (Remaining 15) | 15 | ~4,500 | ~7 minutes |
| **Complete Benchmark** | Mode C (Remaining 15) | **0** (Zero GPU calls) | 0 | 0 seconds |
| **Controlled Remediation** | Counterfactual Pilot | 5 | ~4,000 | ~2 minutes |
| **Total Workload** | **All Live Experiments** | **51 calls** | **~190,000 tokens** | **~20 minutes** |

> [!TIP]
> GPU Server 2 is only required for approximately **20 to 25 minutes of uptime** to complete all pilot, benchmark, and counterfactual remediation runs.

---

## 5. Operator Checkpoint B — Resumption Directive

**Checkpoint B is currently ACTIVE:**
1. All offline preparation, code audits, token budgeting, anti-leakage filters, and test suites are 100% complete.
2. The operator is requested to start GPU Server 2 in the AWS EC2 Management Console when ready to execute live inference.
3. Verification Command:
   ```bash
   curl -s http://13.204.214.64:8000/v1/models
   ```
4. As soon as HTTP 200 is returned, live evaluation will proceed without manual re-configuration.

*Machine-readable manifests:*  
- [GPU_RUNTIME_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/GPU_RUNTIME_MANIFEST.json)  
- [LIVE_INFERENCE_SMOKE_TEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/LIVE_INFERENCE_SMOKE_TEST.json)  
- [GPU_GO_NO_GO.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/GPU_GO_NO_GO.json)
