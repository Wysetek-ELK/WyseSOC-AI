# Phase 2: Canonical Evaluation Status & Source of Truth

## 1. Status Hierarchy & Precedence Engine

To eliminate ambiguity across the UI and API, the system implements a strict deterministic precedence chain.

```mermaid
graph TD
    A[Start Incident Inspection] --> B{Active Execution in Progress?}
    B -- Yes: QUEUED --> S1[QUEUED]
    B -- Yes: RUNNING --> S2[RUNNING]
    B -- No --> C{Execution Record Exists?}
    C -- No --> S3[NOT EVALUATED]
    C -- Yes --> D{Is Execution Simulated / Mock?}
    D -- Yes --> S3M[NOT EVALUATED (Mock Only)]
    D -- No --> E{Execution Status Failed / Timed Out?}
    E -- Yes --> S4[EVALUATION FAILED]
    E -- No --> F{Deterministic Validator Rejected?}
    F -- Yes --> S5[VALIDATION REJECTED]
    F -- No --> G{Effective Verdict is TP or FP?}
    G -- Yes --> S6[EVALUATED — DECISIVE]
    G -- No: REQUIRES_ATTENTION --> S7[ABSTAINED]
```

---

## 2. Canonical Status Definitions

| Canonical Status | Precedence | Conditions | Governed Effective Verdict | UI Color / Badge |
|---|---|---|---|---|
| **QUEUED** | 1 | Task in Celery/Redis queue, `dispatch_status == 'QUEUED'` | `PENDING` | Blue / Neutral Outline |
| **RUNNING** | 2 | GPU execution active, `dispatch_status == 'RUNNING'` | `PENDING` | Blue Pulse |
| **VALIDATION REJECTED** | 3 | Deterministic validator rejected raw output (evidence grounding or format failure) | `REQUIRES_ATTENTION` | Red / Destructive |
| **EVALUATED — DECISIVE** | 4 | Real GPU inference completed; output validated; verdict is `TRUE_POSITIVE` or `FALSE_POSITIVE` | `TRUE_POSITIVE` or `FALSE_POSITIVE` | Green / Success |
| **ABSTAINED** | 5 | Real GPU inference completed; output validated; verdict is `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | Amber / Warning |
| **EVALUATION FAILED** | 6 | Inference failed due to model crash, timeout, connection reset, or context overflow | `FAILED` | Red / Destructive |
| **NOT EVALUATED** | 7 | No execution attempted, or only simulated/mock results exist | `NONE` | Gray / Neutral |

---

## 3. Strict Distinctions & Invariants

1. **Rejected Raw Output $\neq$ Decisive Verdict:**
   If a model produces a raw `TRUE_POSITIVE` prediction, but evidence validation fails (e.g. invalid IP address cited), the canonical status is `VALIDATION_REJECTED`. The system safely converts the effective verdict to `REQUIRES_ATTENTION`, preserving both the rejection and the abstention.
2. **Missing Inference $\neq$ Abstention:**
   An incident with no inference execution is `NOT EVALUATED`. It must never be counted as an AI abstention.
3. **Mock / Simulation Isolation:**
   Simulated dry runs (`is_simulated == True`) are flagged as `is_mock_only: True`. The canonical status remains `NOT EVALUATED` for live production purposes.
4. **Strict Policy Version Pinning:**
   An evaluation executed under policy `v7` does not satisfy policy `v8`. The resolver enforces version isolation.
5. **Tenant Isolation:**
   Inferences are strictly bound to `(tenant_id, rule_uuid, incident_id)`. Cross-tenant contamination is blocked server-side.
