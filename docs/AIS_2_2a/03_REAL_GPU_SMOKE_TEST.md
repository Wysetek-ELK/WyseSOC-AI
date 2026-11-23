# AIS 2.2a Real GPU Inference Smoke Test Report

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2a (Benchmark Evidence Integrity, Dataset Repair & GPU Smoke Validation)  
**Date:** November 23, 2026  
**Status:** PASS — REAL GPU INFERENCE CONFIRMED OPERATIONAL  

---

## 1. Executive Summary

Server 2 (Verdictum Cortex GPU Inference Host) was confirmed **ONLINE** and fully operational. A controlled, bounded smoke test was executed against the local model `Qwen/Qwen2.5-7B-Instruct-AWQ` running on vLLM at `http://13.204.214.64:8000/v1` via Server 1 (`172.26.41.240`).

Five (5) real historical incidents were evaluated under active approved policy v7. All five requests completed successfully without errors, producing genuine model responses, valid JSON payloads, measurable token consumption, and verifiable cryptographic prompt captures.

---

## 2. Infrastructure & Model Topology

- **Server 1 (Application & Database):**
  - Host: `172.26.41.240` (AWS EC2 Private IP / Nginx Port 80 / FastAPI Port 8000)
  - Role: Reverse Proxy, Business Logic, PostgreSQL MVCC Snapshot Isolation, Evidence Normalization, Token Budgeting, Policy Compiler.
- **Server 2 (Cortex GPU Inference Host):**
  - Host: `13.204.214.64` (AWS EC2 Port 8000)
  - Role: Dedicated Local GPU LLM Inference Service (vLLM Engine)
  - Access Control: UFW / AWS Security Group restricted to Server 1 (`172.26.41.240`).
- **Connection Health & Latency:**
  - Probe: `/api/llm/test-connection` from Server 1 to Server 2
  - HTTP Status: `200 OK`
  - Probe Network Latency: **14.7 ms**
  - Circuit Breaker State: `CLOSED`
  - Server Health Status: `ONLINE`
- **Active Model Specifications:**
  - Model Name: `Qwen/Qwen2.5-7B-Instruct-AWQ`
  - Architecture: AWQ 4-bit Quantized Transformer
  - Context Window: 4,096 tokens (`server_max_model_len: 4096`)
  - Target Prompt Budget: 3,328 tokens (after 768 reserve for completion)
  - Temperature: 0.1 (SOC deterministic triage mode)

---

## 3. Real GPU Smoke Test Execution Results

All 5 incidents were drawn from detection rule `Heavy TCP Host Scan On Fixed Port` (UUID: `40498741-ee6b-4a71-9101-0d6d3f77154c`) under approved policy v7.

### 3.1 Execution Matrix

| # | SIEM ID | Database ID | Prompt Tokens | Completion Tokens | Total Tokens | Latency (ms) | Wall Clock (s) | Proposed Verdict | Validation Status |
| :-: | :---: | :--- | :-: | :-: | :-: | :-: | :-: | :---: | :---: |
| 1 | 9309 | `d7cf8e7d-03e6-4ba5-9d52-dea4f4768966` | 3,264 | 252 | 3,516 | 12,973 ms | 14.10 s | `REQUIRES_ATTENTION` | `VALIDATED` |
| 2 | 9299 | `8c88f006-eab1-4212-a694-97169ebf50b1` | 3,044 | 301 | 3,345 | 16,924 ms | 20.09 s | `REQUIRES_ATTENTION` | `VALIDATED` |
| 3 | 9279 | `e2d7cb3c-b002-4909-b4e3-bc6fce608ac9` | 3,195 | 310 | 3,505 | 14,624 ms | 18.16 s | `REQUIRES_ATTENTION` | `VALIDATED` |
| 4 | 9216 | `44ec0830-54e8-43ed-b09a-7123f521fa3f` | 3,204 | 274 | 3,478 | 21,103 ms | 22.12 s | `REQUIRES_ATTENTION` | `VALIDATED` |
| 5 | 9217 | `ccc9c371-aebf-4f3d-9aad-66b1e7929667` | 3,044 | 282 | 3,326 | 11,155 ms | 15.73 s | `REQUIRES_ATTENTION` | `VALIDATED` |

### 3.2 Aggregate Metrics
- **Total Tested:** 5
- **Total Succeeded:** 5 (100%)
- **Total Failed:** 0 (0%)
- **Average Prompt Length:** 3,150.2 tokens
- **Average Completion Length:** 283.8 tokens
- **Average Total Workload:** 3,434.0 tokens
- **Average Latency:** 15,355.8 ms (15.36 seconds per incident)
- **Token Usage Accounting Source:** `API_USAGE` (directly returned from vLLM)
- **Execution Provenance:** `LIVE_PROVIDER` (`is_simulated: false`)

---

## 4. Model Response Analysis & Evidence Grounding

### Incident 1 (SIEM ID: 9309)
- **Prompt SHA256:** `ccc1844e9e081d907e97110e0c80608511ff1fe282291816ee40ce647dfa9d64`
- **Prompt Capture ID:** `2a897cd6-be60-4512-ae70-357f8a1cfc99`
- **Raw Proposed Verdict:** `REQUIRES_ATTENTION`
- **Raw Confidence:** 50.0%
- **Model Rationale:** *"Insufficient evidence to conclusively determine if this is a TRUE_POSITIVE or FALSE_POSITIVE. The raw event count is zero, and critical fields are missing."*
- **Missing Evidence Identified:** `network.tcp_flags`
- **Analyst Action Directive:** *"Follow standard SOC tier-1 investigation runbook for ambiguous telemetry."*

### Incident 2 (SIEM ID: 9299)
- **Prompt SHA256:** `3ab933573056a1e47aaf82c6b80763a82c47cd7d1bfe968005a041bf928fb5e9`
- **Prompt Capture ID:** `37a70e0f-04c7-4396-89bf-2d807756866e`
- **Raw Proposed Verdict:** `REQUIRES_ATTENTION`
- **Raw Confidence:** 50.0%
- **Model Rationale:** *"Insufficient evidence to determine if the scan is malicious or benign. The scan has no raw events and does not provide enough context."*
- **Missing Evidence Identified:** `network.destination_ip_list`, `network.protocol`, `scan.rate_per_second`, `network.tcp_flags`, `scan.unique_destination_hosts`, `scan.destination_scope`

### Incident 3 (SIEM ID: 9279)
- **Prompt SHA256:** `b4e9ad1e2604f5dfc94478d3a9ef03938747b9e2de2fbe3365c34840eecb39d1`
- **Prompt Capture ID:** `9de14e4e-146a-420d-aee4-ac0b88321462`
- **Raw Proposed Verdict:** `REQUIRES_ATTENTION`
- **Raw Confidence:** 50.0%
- **Model Rationale:** *"Insufficient evidence to conclusively determine if this is a TRUE_POSITIVE or FALSE_POSITIVE. Missing critical fields such as network.destination_ip_list and network.protocol."*

### Incident 4 (SIEM ID: 9216)
- **Prompt SHA256:** `2f7ec3d40170cef4e48fd99b43a4f4582e5eaeb45cf47de5ec90d38f17e03c7e`
- **Prompt Capture ID:** `9437391b-858f-45a0-bb56-f311145da3a2`
- **Raw Proposed Verdict:** `REQUIRES_ATTENTION`
- **Raw Confidence:** 50.0%
- **Model Rationale:** *"Insufficient evidence to conclusively determine if this is a TRUE_POSITIVE or FALSE_POSITIVE. The raw event count is zero, and critical fields are missing."*

### Incident 5 (SIEM ID: 9217)
- **Prompt SHA256:** `3d22ddd6972b8de0956d58a2e3b364c99f774924c38cb8f17fe5c07a38755646`
- **Prompt Capture ID:** `1a7ad7b6-2092-4232-939a-43128288831e`
- **Raw Proposed Verdict:** `REQUIRES_ATTENTION`
- **Raw Confidence:** 50.0%
- **Model Rationale:** *"Insufficient evidence to determine if the scan is authorized or malicious. No raw logs available."*

---

## 5. Verification & Safety Findings

1. **Schema Compliance:** 100% of generated responses strictly adhered to the Pydantic `AIVerdictProposal` JSON schema. Zero formatting retries or JSON decode errors occurred.
2. **Abstention Integrity:** In all five incidents, the model recognized missing network flag telemetry and zero raw events, appropriately returning `REQUIRES_ATTENTION` with 50% uncertainty rather than hallucinating a decisive classification.
3. **Double-Blind Protection:** Ground-truth labels were strictly withheld from model payloads. No analyst resolution notes or historical reviews leaked into prompts.
4. **Audit Immutability:** Prompt texts and SHA256 digests were persisted in the `actual_prompt_captures` PostgreSQL table on Server 1. Cryptographic hashes match byte-for-byte.
5. **No Synthetic Shortcuts:** All 5 executions reflect real inference against Server 2's Nvidia GPU. Zero mock fallbacks were triggered.
