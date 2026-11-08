# 11. Evidence and Ground Truth Audit

## 1. Executive Summary

A core promise of an enterprise AI Verdict platform is **unbiased evaluation** and **evidence-grounded reasoning**. To ensure objective evaluation, the platform must rigorously isolate historical ground truth (the final human or SIEM resolution) from the AI model and the reviewing analyst during blind review. Furthermore, any evidence cited by the model must be strictly verifiable against raw telemetry.

This audit evaluates the ground-truth segregation mechanism, allowlist filtering, evidence extraction fidelity, and reveals critical data leakage and evidence truncation vulnerabilities.

---

## 2. Ground-Truth Data Architecture

Ground truth is captured during ingestion and stored across two primary locations:
1. **Dedicated Table (`historical_ground_truth`):**
   - Stores `incident_id`, `resolution_status`, `assigned_analyst`, `close_reason`, and `ingestion_timestamp`.
   - Used by the evaluation service ([`evaluation_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evaluation_service.py)) to compute benchmark accuracy, precision, and recall against model predictions.
2. **Raw Ingestion Payload (`incidents.raw_payload`):**
   - The full JSON or XML object exported by FortiSIEM is persisted in the `raw_payload` column of the `incidents` table.
   - Contains fields such as `clearedReason`, `resolution`, `clearedUser`, and internal investigation notes.

---

## 3. Critical Vulnerability: Ground-Truth Leakage in Blind Review Mode (`AV-006`)

The application offers a **Blind Review Mode** designed to allow human analysts to audit incidents without being biased by historical outcomes.

### 3.1 Mechanism of Failure
In [`incident_service.py#L188-L229`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/incident_service.py#L188-L229) and [`incidents.py#L65-L91`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py#L65-L91):
- When `blind_mode=True`, the backend explicitly sets:
  ```python
  # Suppresses top-level ground_truth field
  incident_dto.ground_truth = None
  ```
- **However, `raw_payload` is passed through completely unredacted:**
  ```python
  incident_dto.raw_payload = inc.raw_payload  # Untouched JSON!
  ```

```mermaid
flowchart LR
    subgraph "Backend Database"
        Inc[(Incident Record)]
        Inc --> GT[ground_truth: 'FALSE_POSITIVE']
        Inc --> Raw["raw_payload: {<br/>  'clearedReason': 'Legitimate Admin Activity',<br/>  'resolution': 'False Positive',<br/>  'events': [...]<br/>}"]
    end

    subgraph "API Response (Blind Review = TRUE)"
        API[GET /api/incidents/123?blind_mode=true]
        GT -.->|Suppressed (NULL)| API
        Raw ==>|Passed Unredacted AV-006| API
    end

    subgraph "Analyst Browser Console"
        API --> UI[Investigation View]
        UI --> Tab[Raw JSON / Telemetry Tab]
        Tab --> Leak[Analyst Sees Historical Resolution & Comments!]
    end
```

> [!CRITICAL]
> **Audit Finding (AV-006): Total Compromise of Blind Evaluation:**
> An analyst inspecting the "Raw Telemetry / Payload" tab in the frontend during a supposedly blind evaluation can directly see the historical `clearedReason`, `resolution`, and closing comments. This invalidates scientific double-blind validation studies conducted on the platform.

---

## 4. Model-Facing Allowlist Filter & Evidence Truncation (`AV-009`)

While the frontend leaks ground truth to analysts in blind mode, the LLM input is sanitized by [`backend/app/llm/model_payload_allowlist.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/llm/model_payload_allowlist.py#L30-L165). However, this filter applies aggressive truncation:

### 4.1 Filter Limits & Truncation Parameters
- **`FORBIDDEN_GROUND_TRUTH_KEYS`:** Successfully filters `clearedReason`, `resolution`, `comments`, `clearedUser`, `ground_truth`, and `verdict`.
- **Event Limit:** Caps telemetry at **maximum 2 events**. Any incident with 3 or more correlated SIEM events has all subsequent events discarded.
- **Attribute Limit:** Caps attributes at **maximum 8 attributes per event**.
- **Character Limits:**
  - Individual attribute values are sliced at **180 characters**.
  - Incident description is sliced at **250 characters**.

### 4.2 Impact on Threat Detection
- Encoded PowerShell commands (e.g. `powershell.exe -enc JABjAGwAaQBl...`) typically span 400 to 2,000 characters. Slicing at 180 characters cuts off the decoded command payload, leaving the LLM unable to inspect the executed script.
- Complex multi-host lateral movement detections lose all event context beyond the first two network hops.

---

## 5. Verification of Model Evidence Claims (`AV-005`)

The model output schema includes a list of strings called `key_evidence`.

### 5.1 Reality of Evidence Validation
The system performs **zero deterministic validation** of the strings returned in `key_evidence`:
1. The backend does not run substring searches against the raw event payloads.
2. The backend does not verify that cited IP addresses, process names, or usernames exist in the incident record.
3. The backend does not check whether cited timestamps correspond to the event timeline.

### 5.2 Verification Assessment
Any claim that the AI Verdict system produces "cryptographically verifiable" or "independently proven" evidence is **factually false**. The evidence presentation is purely an unverified generative summary produced by the local LLM.

---

## 6. Evidence & Ground Truth Summary Table

| Control Dimension | Design Claim | Source Implementation | Finding |
| :--- | :--- | :--- | :--- |
| **Model Ground Truth Isolation** | Zero ground truth exposed to LLM | `model_payload_allowlist.py#L30-L55` | **Effective**: Keys are actively stripped before prompt generation. |
| **Analyst Blind Review Isolation** | Analyst cannot see historical outcome | `incident_service.py#L229` | **Defeated (AV-006)**: Ground truth leaked via `raw_payload`. |
| **Telemetry Completeness** | Full event telemetry evaluated | `model_payload_allowlist.py#L34,L96` | **Severely Truncated (AV-009)**: Max 2 events, 8 attributes, 180 chars. |
| **Evidence Grounding** | Decisions backed by verified evidence | `ai_verdict_service.py#L261-L285` | **Unverified (AV-005)**: LLM text accepted verbatim with no verification. |

