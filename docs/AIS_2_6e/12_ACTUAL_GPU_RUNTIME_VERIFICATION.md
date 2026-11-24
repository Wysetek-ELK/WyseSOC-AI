# AIS 2.6e — Actual GPU Runtime Verification & Infrastructure Audit

**Document Identifier:** `12_ACTUAL_GPU_RUNTIME_VERIFICATION.md`  
**Phase:** AIS 2.6e  
**Status:** SPECIFICATION / PRE-FLIGHT AUDITED  
**Audited Target:** Server 2 (vLLM on AWS EC2)  
**Related Manifests:** [CHECKPOINT_A_STATUS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CHECKPOINT_A_STATUS.json), [GPU_GO_NO_GO.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/GPU_GO_NO_GO.json)

---

## 1. Executive Summary & Verification Mandate

Non-Negotiable Requirement 1 mandates: *"Never fabricate GPU inference results"*, and Requirement 18 mandates: *"Never automatically start, stop, resize or replace billable GPU infrastructure"*.

This document formalizes the runtime verification checklist and technical requirements that must be empirically established when Server 2 is started by the human operator. Prior to sending evaluation prompts, the runtime environment must be validated against the frozen architectural baseline.

---

## 2. Server 2 Infrastructure Specifications

| Infrastructure Attribute | Target Specification | Verification Method |
| :--- | :--- | :--- |
| **Hosting Platform** | AWS EC2 `g5.xlarge` | AWS Console / Instance Metadata |
| **GPU Hardware** | 1x NVIDIA A10G (24 GB VRAM) | `nvidia-smi` |
| **Inference Server** | vLLM (OpenAI-compatible) | HTTP GET `/v1/models` |
| **Port** | `8000` | Socket connection check |
| **Target Model** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | vLLM model string match |
| **Context Window** | `8,192` tokens | Max model length in vLLM config |
| **Quantization** | AWQ (4-bit activation-aware weight) | VRAM footprint ~5.5 GB |
| **Temperature / Top-P** | `temperature=0.0`, `top_p=1.0` | Request payload assertion |
| **Completion Budget** | `768` max completion tokens | Request payload assertion |

---

## 3. Pre-Flight Runtime Verification Sequence

When the operator powers on Server 2, the following verification commands must be executed in sequence:

### Step 1: Network Reachability & Public IP Check
```bash
# Verify TCP connectivity to port 8000
curl -s -m 5 http://<SERVER2_IP>:8000/health
```
*Expected Result:* HTTP 200 OK.

### Step 2: Model Identity Verification
```bash
# Query active model list
curl -s http://<SERVER2_IP>:8000/v1/models | jq .
```
*Expected Result:*
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "object": "model",
      "owned_by": "vllm",
      "root": "Qwen/Qwen2.5-7B-Instruct-AWQ"
    }
  ]
}
```

### Step 3: Smoke Test Single Inference Call
Before initiating the 5-incident pilot, dispatch a single synthetic smoke test:
```bash
curl -s http://<SERVER2_IP>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Respond with JSON: {\"status\": \"ok\"}"}],
    "temperature": 0.0,
    "max_tokens": 50
  }'
```
*Validation:* Verify returned payload contains valid JSON, actual token usage numbers, server request ID, and latency under 2,000 ms.

---

## 4. Current Status: Standby

At the conclusion of Stage A, Server 2 is STOPPED. No live HTTP calls have been dispatched. The circuit breaker on Server 1 is OPEN. Standby status is maintained until operator completion of priority human reviews and explicit authorization.
