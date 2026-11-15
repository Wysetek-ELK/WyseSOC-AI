# VERDICTUM AI — VALIDATION V1.2.2
## 02. READINESS ENGINE CORRECTIONS & LIFECYCLE DECOUPLING

**Document Version:** 1.0.0  
**Target Services:** `ProductionReadinessService`, `PromptStudioService`, `IncidentService`  
**Status:** IMPLEMENTED & VERIFIED  

---

### 1. Invariant: Single Authoritative Readiness State

The readiness calculation is unified across the Studio header, Overview summary card, 6-stage guided checklist, rule catalog, and approval action buttons.

Every layer evaluates readiness against the tuple:
```text
Evaluation Context = (Tenant ID, Rule ID, Candidate Version ID)
```

The mathematical invariant enforced across all APIs is:
$$\text{READY\_FOR\_APPROVAL} \implies \text{approval\_eligible} = \text{True}$$

A version is **never** presented as `READY_FOR_APPROVAL` if `approval_eligible == False`.

---

### 2. Four Decoupled Lifecycle Dimensions

| Dimension | Authoritative Source | Possible States | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **SIEM Deployment Status** | `Rule.status` / FortiSIEM API | `ACTIVE`, `DISABLED` | Physical monitoring status on SIEM collectors |
| **Selected Policy Status** | `PromptVersion.status` | `DRAFT`, `APPROVED`, `ARCHIVED`, `REVOKED` | Governance lifecycle state of the candidate prompt |
| **Runtime AI Execution** | `ProductionReadinessResponse.ai_execution_status` | `Enabled`, `Suspended`, `Blocked` | Real-time decision dispatch eligibility for local LLM |
| **Authoritative Readiness** | `ProductionReadinessResponse.readiness_status` | `APPROVED`, `READY_FOR_APPROVAL`, `VALIDATING`, `LEARNING`, `BLOCKED`, `UNKNOWN` | Comprehensive G1–G8 and statistical verification stage |

#### Prevention of False Inference
Runtime AI execution is never inferred solely from SIEM `ACTIVE`. If an underlying detection rule is `ACTIVE` in FortiSIEM, but the selected candidate prompt is `DRAFT` or lacks 8/8 passing gates, AI Execution is strictly set to `Suspended`.

---

### 3. Backend Implementation Details

In `backend/app/services/production_readiness_service.py`:
```python
# Derive real-time AI Execution Status
if is_baseline and passed_gates_count == 8 and total_reviews >= 100 and wilson_passed:
    ai_execution_status = "Enabled"
elif is_baseline or (active_ver and active_ver.status == "APPROVED"):
    # Revalidation required or draft policy candidate under evaluation
    ai_execution_status = "Suspended"
elif active_ver and active_ver.status == "REVOKED":
    ai_execution_status = "Blocked"
else:
    ai_execution_status = "Suspended"
```

In `backend/app/schemas/production_readiness.py`:
Added `ai_execution_status: str = "Suspended"` to `ProductionReadinessResponse`.

In `backend/app/api/prompts.py` and `backend/app/api/rules.py`:
Readiness in catalog summaries strictly requires `prof.total_analyst_reviews >= 100` and `wilson_lower_bound >= 0.96` in addition to 8 passing gates and zero blockers before emitting `READY_FOR_APPROVAL`.
