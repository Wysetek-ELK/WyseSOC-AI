# 17. End-to-End System Workflows Audit

## 1. Executive Summary

This report maps the end-to-end operational execution paths of AI Verdict. We provide comprehensive Mermaid sequence diagrams and source-code traceability for the **14 core workflows** governing the application lifecycle, from rule ingestion to model inference, analyst feedback, and system rollback.

---

## 2. Workflow Index & Sequence Diagrams

```mermaid
flowchart TD
    W1[1. Rule Ingestion] --> W3[3. Policy Draft Synthesis]
    W3 --> W4[4. Policy Approval Gate]
    W4 --> W5[5. Runtime Prompt Assembly]
    
    W2[2. Incident Ingestion] --> W5
    W10[10. Historical RAG Retrieval] --> W5
    
    W5 --> W6[6. LLM Inference & JSON Repair]
    W6 --> W7[7. Final Verdict Decision]
    W7 --> W14[14. Persistence & Downstream Display]
    
    W14 --> W8[8. Analyst Review & Override]
    W8 --> W9[9. Learning Record Creation]
    W9 -.-> W10
    
    W4 -.-> W11[11. Simulation & Dry-Run]
    W4 -.-> W12[12. Policy Rollback]
    
    W6 -.-> W13[13. Error Handling & Fallback]
```

---

### Workflow 1: Detection Rule Ingestion & Synchronization
- **Trigger:** Scheduled sync or `POST /api/fortisiem/sync-rules`
- **Source:** [`backend/app/services/fortisiem_service.py#L180-L240`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L180-L240)

```mermaid
sequenceDiagram
    autonumber
    participant Admin as SOC Admin
    participant API as FortiSIEM Router
    participant Svc as FortiSIEM Service
    participant FS as FortiSIEM Supervisor
    participant Parser as DetectionContextEngine
    participant DB as Database (rules table)

    Admin->>API: POST /api/fortisiem/sync-rules
    API->>Svc: sync_rules_from_fortisiem()
    Svc->>FS: GET /phoenix/rest/config/rules
    FS-->>Svc: XML Rules Payload
    loop For Each Rule
        Svc->>Parser: parse_xml_rule(xml)
        Parser-->>Svc: RuleMetadata & ParsedCriteria
        Svc->>DB: Upsert Rule Record
    end
    Svc-->>API: { synced_count: N }
    API-->>Admin: HTTP 200 OK
```

---

### Workflow 2: Incident Ingestion (Continuous Polling & Archive Upload)
- **Trigger:** 180s scheduler tick or `POST /api/incidents/upload`
- **Source:** [`ingestion_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ingestion_service.py) & [`fortisiem_scheduler.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_scheduler.py)

```mermaid
sequenceDiagram
    autonumber
    participant Sch as Scheduler Daemon
    participant FS as FortiSIEM Supervisor
    participant Ing as Ingestion Service
    participant Norm as Field Normalizer
    participant DB as Incidents Table

    Sch->>FS: POST /incident/query (Watermark - 2 min buffer)
    FS-->>Sch: Incidents JSON Array
    loop For Each Incident
        Sch->>Ing: ingest_single_incident(raw_data)
        Ing->>Norm: extract_incident_timestamps()
        Ing->>Norm: extract_event_data()
        Ing->>DB: Check external_id deduplication
        alt New Incident
            Ing->>DB: INSERT into incidents
            Ing->>DB: INSERT into historical_ground_truth
        else Existing Incident
            Ing->>DB: UPDATE incident status
        end
    end
```

---

### Workflow 3: Policy Draft Synthesis
- **Trigger:** Rule creation or `POST /api/prompts/synthesize/{rule_id}`
- **Source:** [`prompt_studio_service.py#L45-L160`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py#L45-L160)

```mermaid
sequenceDiagram
    autonumber
    participant User as SOC Analyst
    participant API as Prompts Router
    participant Studio as PromptStudioService
    participant DB as PromptVersions Table

    User->>API: POST /api/prompts/synthesize/{rule_id}
    API->>Studio: synthesize_draft_prompt(rule_id)
    Studio->>Studio: Classify Rule Archetype (EDR/Web/Generic)
    Studio->>Studio: Build 9-Section Directive Template
    Studio->>DB: INSERT PromptVersion (status = 'DRAFT', version = N+1)
    Studio-->>API: PromptVersionDTO
    API-->>User: HTTP 201 Created
```

---

### Workflow 4: Policy Approval Gate & Activation
- **Trigger:** `POST /api/prompts/{prompt_id}/approve/{version_id}`
- **Source:** [`prompt_studio_service.py#L180-L220`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py#L180-L220)

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Administrator
    participant API as Prompts Router (require_admin)
    participant Studio as PromptStudioService
    participant DB as Database
    participant Audit as AuditService

    Admin->>API: POST /api/prompts/{prompt_id}/approve/{version_id}
    API->>Studio: approve_prompt_version(version_id)
    Studio->>DB: Fetch existing active version
    opt Existing Active Version Exists
        Studio->>DB: UPDATE existing active SET status = 'ARCHIVED'
    end
    Studio->>DB: UPDATE target version SET status = 'APPROVED'
    Studio->>DB: UPDATE rule_prompts SET active_version_id = version_id
    Studio->>Audit: log_action('POLICY_APPROVED', version_id)
    Studio-->>API: Success Response
    API-->>Admin: HTTP 200 OK
```

---

### Workflow 5: Runtime Prompt Assembly & Ground-Truth Stripping
- **Trigger:** Internal call prior to model execution
- **Source:** [`ai_verdict_service.py#L130-L185`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L130-L185) & [`model_payload_allowlist.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/llm/model_payload_allowlist.py)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as VerdictTriageAgent
    participant Filter as ModelPayloadAllowlist
    participant DB as Database
    
    Agent->>Filter: build_model_facing_payload(incident)
    Filter->>Filter: Strip FORBIDDEN_GROUND_TRUTH_KEYS
    Filter->>Filter: Truncate to Max 2 Events, Max 8 Attrs (AV-009)
    Filter-->>Agent: Sanitized Context JSON
    Agent->>DB: Fetch Active PromptVersion (or Draft v0 AV-002)
    Agent->>Agent: Concatenate Sections 1,2,4,5,6,7 (Omits 3,8,9 AV-003)
    Agent->>DB: Query Latest LearningRecord (Single record limit 1 AV-007)
    Agent->>Agent: Assemble Final String Prompt
```

---

### Workflow 6: LLM Inference Call & JSON Repair
- **Trigger:** Assembled prompt execution
- **Source:** [`openai_compatible.py#L140-L390`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/llm/openai_compatible.py#L140-L390)

```mermaid
sequenceDiagram
    autonumber
    participant Prov as OpenAICompatibleProvider
    participant GPU as Server 2 (vLLM / Ollama)
    participant Repair as robust_parse_model_verdict_json

    Prov->>GPU: POST /v1/chat/completions (temp=0.1, max_tokens=350)
    GPU-->>Prov: Raw String Response
    Prov->>Repair: parse(raw_text)
    Repair->>Repair: Strip Markdown Fences
    Repair->>Repair: Clean Unescaped Control Characters
    opt JSON Decode Fails
        Repair->>Repair: Repair Unclosed Braces / Quotes
        opt Still Fails
            Repair->>Repair: Regex Pattern Extraction Fallback
        end
    end
    Repair-->>Prov: StructuredModelVerdict DTO
```

---

### Workflow 7: Final Verdict Decision & Verification Acceptance
- **Trigger:** Receipt of parsed model response
- **Source:** [`ai_verdict_service.py#L260-L290`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L260-L290)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as VerdictTriageAgent
    participant DB as Incidents Table
    
    Note over Agent: Model Verdict Accepted Verbatim (AV-005)
    Note over Agent: ZERO Deterministic Telemetry Proof
    Agent->>DB: UPDATE incidents SET ai_verdict = verdict.verdict, confidence = verdict.confidence, reasoning = verdict.reasoning
    Agent->>DB: INSERT into token_usage_records
    Agent-->>Agent: Return Completed Incident Record
```

---

### Workflow 8: Analyst Review & Override
- **Trigger:** Analyst submits feedback in Investigation Console
- **Source:** [`investigation_service.py#L303-L355`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/investigation_service.py#L303-L355)

```mermaid
sequenceDiagram
    autonumber
    participant Analyst as SOC Analyst
    participant UI as Investigation Console
    participant API as Incidents Router
    participant Svc as Investigation Service
    participant DB as Database

    Analyst->>UI: Select Incident & View Evidence
    Analyst->>UI: Submit Override Verdict + Notes
    UI->>API: POST /api/incidents/{id}/feedback
    API->>Svc: submit_analyst_feedback()
    Svc->>DB: Record LearningRecord
    opt is_independently_verified == True
        Note over Svc,DB: Record Marked 'VERIFIED' Immediately (AV-008)
    end
    Svc-->>API: Feedback Confirmed
    API-->>UI: HTTP 200 OK
```

---

### Workflow 9: Learning Record Creation & State Transition
- **Trigger:** Internal persistence of feedback
- **Source:** [`learning_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/learning_service.py)

```mermaid
sequenceDiagram
    autonumber
    participant Svc as LearningService
    participant DB as LearningRecords Table
    participant Admin as Administrator

    alt Unverified Submission
        Svc->>DB: INSERT LearningRecord (status = 'PENDING_REVIEW')
        Admin->>Svc: PUT /api/learning/{id}/verify
        Svc->>DB: UPDATE LearningRecord SET status = 'VERIFIED'
    else Self-Verified by Analyst (AV-008)
        Svc->>DB: INSERT LearningRecord (status = 'VERIFIED', is_verified = True)
    end
```

---

### Workflow 10: Historical RAG Retrieval
- **Trigger:** Incident triage few-shot lookup
- **Source:** [`ai_verdict_service.py#L149-L180`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L149-L180)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as VerdictTriageAgent
    participant DB as LearningRecords Table

    Agent->>DB: SELECT * WHERE rule_id = incident.rule_id AND status = 'VERIFIED' ORDER BY feedback_timestamp DESC LIMIT 1
    alt Found Rule Record
        DB-->>Agent: Rule Specific Record
    else None Found
        Agent->>DB: SELECT * WHERE status = 'VERIFIED' ORDER BY feedback_timestamp DESC LIMIT 1 (Cross-Rule Fallback AV-007)
        DB-->>Agent: Arbitrary Cross-Rule Record
    end
    Agent->>Agent: Truncate notes to 150 chars (Discard telemetry)
```

---

### Workflow 11: Simulation & Dry-Run Evaluation
- **Trigger:** `POST /api/dry-run/start`
- **Source:** [`dry_run_service.py#L75-L220`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/dry_run_service.py#L75-L220)

```mermaid
sequenceDiagram
    autonumber
    participant Analyst as SOC Analyst
    participant API as DryRun Router
    participant Svc as DryRunService
    participant LLM as Model Provider
    participant DB as Database

    Analyst->>API: POST /api/dry-run/start (rule_prompt_id, version_id, split)
    API->>Svc: execute_dry_run_job() (Synchronous Loop AV-013)
    loop For Each Historical Incident in Split
        Svc->>LLM: generate_verdict(prompt_sections_1_and_2_ONLY) (AV-003)
        LLM-->>Svc: Predicted Verdict
        Svc->>DB: INSERT DryRunResult
    end
    Svc->>Svc: Compute Accuracy, F1, Confusion Matrix
    Svc->>DB: UPDATE DryRun SET status = 'COMPLETED', metrics = JSON
    Svc-->>API: DryRunSummaryDTO
    API-->>Analyst: HTTP 200 OK
```

---

### Workflow 12: Policy Rollback
- **Trigger:** `POST /api/prompts/{prompt_id}/rollback/{target_version_id}`
- **Source:** [`prompt_studio_service.py#L225-L260`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py#L225-L260)

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Administrator
    participant API as Prompts Router
    participant Svc as PromptStudioService
    participant DB as Database

    Admin->>API: POST /api/prompts/{prompt_id}/rollback/{target_version_id}
    API->>Svc: rollback_to_version(prompt_id, target_version_id)
    Svc->>DB: Fetch target archived version
    Svc->>DB: Clone attributes into NEW PromptVersion (version = MAX+1, status = 'APPROVED')
    Svc->>DB: UPDATE rule_prompts SET active_version_id = new_version.id
    Svc-->>API: New PromptVersionDTO
    API-->>Admin: HTTP 200 OK
```

---

### Workflow 13: Error Handling & Mock Fallback
- **Trigger:** Model inference failure or timeout
- **Source:** [`ai_verdict_service.py#L225-L235`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L225-L235)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as VerdictTriageAgent
    participant LLM as OpenAICompatibleProvider
    participant GPU as Server 2 GPU Node
    participant Sim as SimulatedModelProvider
    participant DB as Incidents Table

    Agent->>LLM: generate_verdict()
    LLM->>GPU: POST /chat/completions
    GPU--xLLM: Timeout / Connection Refused
    LLM--xAgent: Raise HTTPConnectionError
    Note over Agent: Catch Exception & Check allow_mock (AV-004)
    alt allow_mock is True
        Agent->>Sim: generate_verdict(incident_context)
        Sim->>Sim: Keyword Match ('select2', 'adrum', '70cb...')
        Sim-->>Agent: Synthetic Verdict (96% Confidence)
        Agent->>DB: UPDATE incidents (Silent Mock Persistence)
    else allow_mock is False
        Agent-->>Agent: Re-raise Exception (HTTP 500)
    end
```

---

### Workflow 14: Incident Persistence & Downstream Actions
- **Trigger:** Successful verdict formation
- **Source:** [`incidents.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py) & [`fortisiem_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as VerdictTriageAgent
    participant DB as Incidents Table
    participant UI as Analyst Console
    participant FS as FortiSIEM Supervisor

    Agent->>DB: Commit Incident Triage State
    Note over Agent,UI: Incident Visible on Web Console
    Note over Agent,FS: ZERO Write-Back to SIEM (Read-Only Integration)
    Note over UI: Analyst Must Manually Close Ticket in FortiSIEM
```

