# Local LLM Dry-Run Architecture & Processing Workflow

## 1. Executive Overview

This document specifies the end-to-end architecture, communication protocol, and execution workflow for **dry-run incident replay** in the **AI Verdict (WyseSOC AI)** platform following the integration of **Server 2 (Local LLM)**.

The system executes automated, deterministic, and privacy-preserving security analysis across thousands of historical SIEM incidents without sending sensitive corporate telemetry to external cloud AI providers.

```mermaid
flowchart LR
    subgraph S1["Server 1 — Application Server (Rocky Linux 10)"]
        UI["Web UI / Dashboard<br/>Next.js 16 (Port 80)"]
        API["FastAPI Backend<br/>(Port 8000)"]
        Orch["DryRunService<br/>Replay Engine"]
        IsoGuard["Ground-Truth<br/>Isolation Guard"]
        Eval["EvaluationEngine<br/>2x3 Confusion Matrix"]
        DB[("PostgreSQL 16<br/>ai_verdict")]
    end

    subgraph S2["Server 2 — Local LLM Server (GPU Node)"]
        Inference["vLLM / Ollama Engine<br/>OpenAI-Compatible API (Port 8000)"]
        Model["Qwen2.5-7B / 14B-Instruct<br/>(Quantized AWQ/GPTQ)"]
        GPU["NVIDIA GPU (16GB+ VRAM)"]
    end

    UI -->|1. Trigger Replay| API
    API --> Orch
    Orch -->|2. Query Incidents| DB
    Orch -->|3. Assemble Telemetry| IsoGuard
    IsoGuard -->|4. Clean Investigation Payload| Inference
    Inference --> Model
    Model --> GPU
    Inference -->|5. Structured JSON Verdict| Orch
    Orch -->|6. Persist DryRunResult| DB
    Orch -->|7. Calculate Metrics| Eval
    Eval -->|8. Precision / Recall / Tiers| DB
    Eval -->|9. Real-Time Status| UI
```

---

## 2. Two-Server Physical Topology

| Attribute | Server 1 (Application Server) | Server 2 (Local LLM Server) |
| :--- | :--- | :--- |
| **Instance Type** | General Purpose Compute (e.g., `t3.xlarge` / On-Prem VM) | Accelerated GPU (e.g., AWS `g4dn.2xlarge` / On-Prem GPU) |
| **Hardware** | 4-8 vCPUs, 16GB RAM, 100GB SSD | 8 vCPUs, 32GB RAM, 1x NVIDIA T4 / A10G (16GB+ VRAM) |
| **Operating System**| Rocky Linux 10.1 / Ubuntu 24.04 LTS | Ubuntu 22.04 LTS with NVIDIA Container Toolkit |
| **Primary Software**| Python 3.12, FastAPI, Next.js 16, Nginx, PostgreSQL 16 | vLLM 0.6+ / Ollama, CUDA 12.4 |
| **Serving Protocol**| HTTP/HTTPS (Port 80/443) to Analysts | OpenAI-Compatible REST (`/v1/chat/completions`) on Private LAN |
| **Network Security**| Accessible by SOC analysts on corporate intranet | Strictly internal; accepts traffic **only** from Server 1 IP |

---

## 3. End-to-End Dry-Run Replay Sequence

The following sequence details how an analyst-initiated replay job flows through both servers from trigger to evaluation scoring:

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as SOC Analyst / Admin
    participant UI as Web Frontend (Next.js)
    participant API as FastAPI Backend (Server 1)
    participant DB as PostgreSQL Database
    participant Guard as Ground-Truth Isolation Guard
    participant Provider as OpenAICompatibleProvider
    participant LLM as Local LLM Server (Server 2)

    Analyst->>UI: Select Rule, Prompt Version, Split Strategy, and click "Start Dry-Run"
    UI->>API: POST /api/dry-run/jobs (rule_id, prompt_version_id, strategy)
    API->>DB: Create DryRunJob (status: PENDING)
    API-->>UI: Return job_id (HTTP 201)
    
    activate API
    API->>DB: Query Incidents matching Rule & Split Strategy
    DB-->>API: Return Historical Incidents (Raw Telemetry + Events)
    
    loop For Each Incident in Replay Batch
        API->>DB: Fetch Active Rule Prompt Template (Common + Rule-specific)
        DB-->>API: Return Prompt Components (Conditions, Evidence Checklist, Questions)
        
        API->>Guard: Submit Incident Payload for Scrubbing
        Note over Guard: Strips resolution, comments, clearedUser,<br/>clearedReason, and post-closure metadata!
        Guard-->>API: Return Sanitized Model Input
        
        API->>Provider: Build OpenAI Chat Completion Request
        Provider->>LLM: POST /v1/chat/completions (Sanitized Payload, temp=0.0, JSON mode)
        
        activate LLM
        Note over LLM: Executes Inference on NVIDIA GPU<br/>Evaluates Detection Criteria<br/>Generates Evidence Attribution
        LLM-->>Provider: HTTP 200: Structured JSON Response
        deactivate LLM
        
        Provider->>API: Parse & Validate Response (Predicted Verdict, Confidence, Reasoning)
        API->>DB: Store DryRunResult (predicted_verdict, latency_ms, supporting_evidence)
        API->>UI: Stream Progress (processed_items / total_items)
    end
    
    API->>DB: Update DryRunJob (status: COMPLETED)
    API->>DB: Fetch Ground Truth & Calculate 2x3 Matrix (TP, FP, Abstentions)
    API->>DB: Update Rule Automation Readiness Tier (Tier 1-5)
    deactivate API
    
    UI->>Analyst: Display Confusion Matrix, Accuracy %, and Comparison Report
```

---

## 4. Step-by-Step Processing Pipeline

### Step 1: Job Configuration & Split Selection
The analyst navigates to `/dry-run` and configures the execution parameters:
- **Rule Scope**: Specific detection rule (e.g., `PH_RULE_CS_SUSPICIOUS_ACTIVITY`) or all rules.
- **Prompt Version**: Candidate prompt version from the Rule Prompt Studio.
- **Splitting Strategy**:
  - `ALL`: Replays all matching historical incidents.
  - `CHRONOLOGICAL_70_30`: Evaluates on the oldest 70% as training/baseline and the newest 30% as out-of-time test set.
  - `GROUP_AWARE_HOST`: Partitions by reporting device/host to prevent data leakage across identical compromised endpoints.

### Step 2: Ground-Truth Isolation Enforcement
Before any telemetry leaves Server 1, the **Ground-Truth Isolation Guard** inspects the incident record:

> [!CAUTION]
> **Strict Isolation Rule**: Under no circumstances may post-investigation fields reach Server 2. The guard enforces an allowlist:
> - **ALLOWED**: `incidentId`, `eventType`, `title`, `description`, `detail`, `severity`, `sourceIp`, `reportingDevice`, `firstSeen`, `lastSeen`, `createdAt`, `rawEvents` (attributes, raw logs, network events).
> - **BLOCKED & PURGED**: `resolution`, `clearedReason`, `comments`, `clearedUser`, `analystNotes`, `historical_verdict`, `resolved_at`.

### Step 3: Prompt Assembly & JSON Framing
Server 1 injects the sanitized telemetry into the structured prompt template defined in the **Rule Prompt Studio**:
1. **System Persona**: Enterprise SOC Senior Incident Analyst role.
2. **Common Prompt**: Enterprise guidelines for malicious vs benign classification.
3. **Rule-Specific Logic**: Explicit detection conditions, known false positive patterns (e.g., sanctioned admin scripts, signed updater binaries).
4. **Evidence Checklist**: Required indicators of attack (IOAs) vs benign activity.
5. **Output Schema Mandate**: Demands strict JSON with no conversational preamble.

---

## 5. Model Communication Protocol (Server 1 ➔ Server 2)

### A. HTTP Request Payload (`Server 1 ➔ Server 2:8000/v1/chat/completions`)

```json
{
  "model": "qwen2.5-7b-instruct",
  "temperature": 0.0,
  "max_tokens": 1024,
  "response_format": { "type": "json_object" },
  "messages": [
    {
      "role": "system",
      "content": "You are AI Verdict, an autonomous Level-2 SOC analysis engine. Analyze the provided SIEM telemetry against the rule detection logic. Return a valid JSON object matching the required schema."
    },
    {
      "role": "user",
      "content": "RULE: PH_RULE_CS_SUSPICIOUS_ACTIVITY\nDESCRIPTION: Detects suspicious activity using Indicator of Attack (IOA) or tool tampering.\n\nEVIDENCE CRITERIA:\n- True Positive: Execution of unauthorized living-off-the-land binaries (certutil, powershell -enc, vssadmin delete shadows).\n- False Positive: Known IT management tools (SCCM, Tanium, Datadog agent updates).\n- Requires Attention: Insufficient telemetry or ambiguous parent-child process lineage.\n\nINCIDENT TELEMETRY:\nIncident ID: 132501348\nHost: DESKTOP-CQ4A60U\nSource IP: 198.51.100.157\nTimestamp: 2026-11-05T14:46:23Z\nRaw Events:\n- Process: powershell.exe -ExecutionPolicy Bypass -Command 'Get-Service'\n- Parent: explorer.exe\n- User: DOMAIN\\analyst_admin\n\nREQUIRED OUTPUT SCHEMA:\n{\n  \"verdict\": \"TRUE_POSITIVE\" | \"FALSE_POSITIVE\" | \"REQUIRES_ATTENTION\",\n  \"confidence\": 0-100,\n  \"reasoning\": \"string\",\n  \"supporting_evidence\": [\"string\"],\n  \"missing_evidence\": [\"string\"],\n  \"analyst_questions\": [\"string\"]\n}"
    }
  ]
}
```

### B. HTTP Response Payload (`Server 2 ➔ Server 1`)

```json
{
  "id": "chatcmpl-9f8a32b1",
  "object": "chat.completion",
  "created": 1793945890,
  "model": "qwen2.5-7b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\n  \"verdict\": \"FALSE_POSITIVE\",\n  \"confidence\": 92,\n  \"reasoning\": \"Execution of powershell.exe running a read-only reconnaissance cmdlet 'Get-Service' initiated by an administrative user account without obfuscation, encoded payloads, or privilege escalation attempts.\",\n  \"supporting_evidence\": [\n    \"Command line contains only standard Get-Service cmdlet\",\n    \"Executed under authenticated analyst_admin session\",\n    \"Zero network connections or child process spawns observed\"\n  ],\n  \"missing_evidence\": [],\n  \"analyst_questions\": [\n    \"Was this routine administrative service verification scheduled by IT?\"\n  ]\n}"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 420,
    "completion_tokens": 142,
    "total_tokens": 562
  }
}
```

---

## 6. Evaluation Scoring & Dual-Verdict Comparison

Once Server 1 receives the structured verdict from Server 2, it compares the prediction against the historical ground truth stored in PostgreSQL:

```mermaid
flowchart TD
    Verdict["Server 2 LLM Verdict<br/>(TP, FP, or REQUIRES_ATTENTION)"]
    GT["Historical Ground Truth<br/>(Analyst Closed TP or FP)"]

    Verdict & GT --> Evaluator{"Evaluation Engine"}

    Evaluator -->|LLM: TP & Ground Truth: TP| Cell1["True Positive Agreement<br/>(Correct Malicious Detection)"]
    Evaluator -->|LLM: FP & Ground Truth: FP| Cell2["False Positive Agreement<br/>(Correct Alert Suppression)"]
    Evaluator -->|LLM: TP & Ground Truth: FP| Cell3["False Positive Mismatch<br/>(Hallucinated Threat)"]
    Evaluator -->|LLM: FP & Ground Truth: TP| Cell4["CRITICAL MISS (FN)<br/>(Escaped Incident!)"]
    Evaluator -->|LLM: REQUIRES_ATTENTION| Cell5["Safe Abstention<br/>(Routed to Human Analyst)"]

    Cell1 & Cell2 & Cell3 & Cell4 & Cell5 --> Metrics["2x3 Confusion Matrix<br/>- Precision: TP / (TP + FP)<br/>- Recall: TP / (TP + FN)<br/>- Coverage: Resolved / Total<br/>- F1 Score"]

    Metrics --> TierCheck{"Rule Automation Readiness"}
    TierCheck -->|Accuracy >= 98% & Sample >= 100| T4["Tier 4: Shadow Mode"]
    TierCheck -->|Accuracy >= 95% & Sample >= 50| T3["Tier 3: Supervised AI"]
    TierCheck -->|Accuracy >= 90% & Sample >= 25| T2["Tier 2: Candidate Rule"]
    TierCheck -->|Accuracy < 90%| T1["Tier 1: Experimental (Draft)"]
    TierCheck -->|Tier 4 + Mandatory Admin Sign-Off| T5["Tier 5: Automated Production"]
```

---

## 7. Performance & Latency Budgets

To handle enterprise SOC throughput (~10,000 SIEM incidents daily):

| Metric | Target SLA | Strategy to Achieve |
| :--- | :--- | :--- |
| **Inference Latency per Alert** | `< 450 ms` | vLLM continuous batching + FlashAttention-2 + AWQ 4-bit quantization |
| **Concurrent Dry-Run Throughput**| `40-60 incidents/sec` | Batch queuing with asynchronous worker thread pool in FastAPI |
| **Replay Job (100 incidents)** | `< 15 seconds` | Server 1 sends chunked parallel requests (concurrency: 8-16) |
| **Memory Footprint on Server 2** | `< 12 GB VRAM` | 7B model at 4-bit requires ~5.5GB; leaves 10GB for KV-cache |
| **Network Overhead** | `< 5 ms` | Private AWS VPC / internal 10Gbps Ethernet link between servers |

---

## 8. Summary of Benefits

1. **Zero Data Leakage**: No corporate SIEM alerts, internal IPs, usernames, or process hashes ever leave the local data center / private cloud.
2. **Safe Before Automated**: New prompts and detection rules can be tested against thousands of historical records in seconds before ever interacting with live analysts.
3. **Auditability**: Every prompt version, LLM inference latency, reasoning chain, and attribution is version-controlled and cryptographically logged for SOC governance.

