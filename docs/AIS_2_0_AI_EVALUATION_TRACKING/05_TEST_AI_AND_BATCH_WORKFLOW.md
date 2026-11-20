# Phase 5: Test AI & Controlled Batch Inference Workflow

## 1. Test AI Preflight Status Checks
The **Test AI** workbench (`frontend/src/components/compact/AiTestWorkbench.tsx`) was upgraded with dynamic preflight checks:

1. **Pre-Evaluation Check:**
   When an incident is selected, the workbench immediately queries `GET /api/ais/incidents/{incident_id}/evaluation-history`.
2. **Context-Aware Action Buttons:**
   - If **Evaluated — Decisive**: Prominently shows "Incident already evaluated under v7. Stored verdict: FALSE_POSITIVE (Confidence: 94.0%)". Primary action: "View History". Secondary: "Rerun AI Test (Admin Override)".
   - If **Abstained**: Shows "Incident abstained (Effective verdict: REQUIRES_ATTENTION)". Action: "Rerun Test".
   - If **Validation Rejected**: Shows "Validation rejected on previous run: Evidence grounding failed". Action: "Retry AI Test".
   - If **Not Evaluated**: Primary action: "Run Real AI Test".

---

## 2. Controlled Batch Inference Workflow

To eliminate manual one-by-one testing while strictly preventing unmonitored GPU execution, an administrative **Controlled Batch Inference** modal was implemented.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Authorized Admin
    participant UI as Test AI Workbench
    participant API as AIS Evaluation API
    participant Worker as Inference Task Worker
    participant LLM as Server 2 Local LLM (vLLM)

    Admin->>UI: Click "Evaluate Missing Incidents"
    UI->>API: Query missing incidents count & GPU health
    API-->>UI: 15 eligible incidents, Server 2 GPU Online (VRAM OK)
    UI-->>Admin: Show Preflight Dialog (Budget, Concurrency, Confirmation)
    Admin->>UI: Set concurrency=2, check "Confirm Execution", click "Start"
    UI->>API: POST /api/ais/rules/{rule_uuid}/evaluate-missing-batch
    API->>Worker: Enqueue 15 scoped background tasks
    API-->>UI: Return batch_id, 15 queued
    loop Progress Polling
        UI->>API: Check batch status & incident evaluation status
        Worker->>LLM: Dispatch inference (RETROSPECTIVE_EVALUATION)
        LLM-->>Worker: Return completions
        Worker->>API: Store pilot_verdicts & captures
        API-->>UI: Updated completed counts
    end
    UI-->>Admin: Batch Complete (0 Failed, 15 Evaluated)
```

### Safety Controls in Batch Workflow:
- **No Accidental Execution:** Requires explicit confirmation checkbox.
- **Strict Concurrency Limit:** Configurable concurrency (1 to 4) prevents GPU out-of-memory or high latency on Server 2.
- **Provenance Tagging:** Stored executions are marked with `execution_type = 'RETROSPECTIVE_EVALUATION'`.
- **Graceful Cancellation:** Cancellation stops subsequent queued items without corrupting completed ones.
