# VERDICTUM AI — VALIDATION V1.2.2a
## 03. Authoritative AI Execution Status & Runtime Source of Truth

### 1. Conceptual Principle

In Agent Intelligence Studio 2.0, the core governance tenet is:
> **Production Readiness ≠ SIEM Deployment Status ≠ AI Policy Approval Status ≠ AI Execution Status**

These four states must never be conflated:
1. **SIEM Deployment Status** (`rule_deployment_status`): Tracks whether the detection rule is active in the FortiSIEM cluster (`ACTIVE`, `INACTIVE`, `TESTING`).
2. **AI Policy Approval Status** (`version_status`): Tracks whether the specific prompt policy version has completed governance sign-off (`DRAFT`, `APPROVED`, `REJECTED`, `ARCHIVED`).
3. **Current Production Readiness** (`readiness_status`): Evaluates whether the rule/version satisfies all active AIS 2.0 quality gates G1–G8, minimum ground-truth volume, and confidence bounds (`BLOCKED`, `INCOMPLETE`, `LEARNING`, `READY_FOR_APPROVAL`, `APPROVED`).
4. **AI Execution Status** (`ai_execution_status`): Represents whether the live verdict engine is actively evaluating incidents in production (`Enabled`, `Disabled`, `Suspended`, `Offline`, `Unknown`, `Blocked`).

---

### 2. State Derivation Logic

In `backend/app/services/production_readiness_service.py`, `ai_execution_status` is derived deterministically from four real control surfaces:

```
                                  [Active Version Approved?]
                                        │
                         No ────────────┴──────────── Yes
                         │                             │
                     [Blocked]             [Emergency Kill-Switch Active?]
                                                       │
                                        Yes ───────────┴─────────── No
                                         │                           │
                                    [Suspended]             [Automation Configured?]
                                                                     │
                                                      No ────────────┴──────────── Yes
                                                      │                             │
                                                 [Disabled]              [Local LLM Runtime Healthy?]
                                                                                    │
                                                                     No ────────────┴──────────── Yes
                                                                     │                             │
                                                                 [Offline]                     [Enabled]
```

#### Precise Derivation Rules:
1. **`Blocked`**: The rule has no active version, or the target version is not approved in production governance.
2. **`Suspended`**: The active version is approved, but execution has been manually halted via `rule_prompt.ai_execution_suspended` or `RulePrompt.emergency_disable`.
3. **`Disabled`**: The active version is approved and not suspended, but automated production evaluation is turned off in `ProductionAutomationPolicy.is_enabled = False`.
4. **`Offline`**: The active version is approved, not suspended, and automation is enabled, but the runtime inference agent (`VerdictTriageAgent.is_local_llm_available()`) is unreachable or failing health checks.
5. **`Enabled`**: The active version is approved, not suspended, automation is configured, and the local LLM runtime is healthy and responsive.
6. **`Unknown`**: Telemetry or policy records cannot be resolved.

---

### 3. Separation of Configuration vs. Runtime Availability

To prevent deceptive UI states where an enabled policy falsely appears working during a model failure, the backend schema and frontend UI explicitly separate:
- `automation_configured: bool`: Reflects the administrative setting in `ProductionAutomationPolicy`.
- `runtime_availability: str`: Reflects the real-time inference agent status (`"Healthy"` vs `"Offline"`).

#### UI Visual Representation:
In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:
- **Offline**: Rose dot (`bg-rose-500 animate-pulse`), `text-rose-400 font-semibold`, tooltip: *"Automation is configured in policy, but the local LLM runtime (Server 2) is currently offline or unreachable."*
- **Suspended**: Amber dot (`bg-amber-400`), `text-amber-400 font-semibold`, tooltip: *"AI inference is suspended by administrative kill-switch."*
- **Disabled**: Slate dot (`bg-slate-400`), `text-slate-400`, tooltip: *"Automated AI execution is disabled in production policy."*
- **Enabled**: Emerald dot (`bg-emerald-400`), `text-emerald-400 font-semibold`, tooltip: *"AI inference is actively evaluating incidents."*
- **Blocked**: Rose dot (`bg-rose-500`), `text-rose-400 font-semibold`, tooltip: *"AI execution blocked: Version requires governance approval."*

---

### 4. Empirical Test Validation

In Scenario 8 (`studio_ai_execution_runtime_offline`), Heavy TCP v1 was evaluated with:
- `ProductionAutomationPolicy.is_enabled = True`
- `ai_execution_suspended = False`
- `VerdictTriageAgent.is_local_llm_available() = False` (Server 2 GPU offline)

**Result:**
- Backend API returned: `ai_execution_status: "Offline"`, `automation_configured: true`, `runtime_availability: "Offline"`.
- Frontend UI rendered: `AI Execution: Offline` with red pulsing dot and accurate tooltip.
- Confirms zero conflation between administrative configuration and runtime health.
