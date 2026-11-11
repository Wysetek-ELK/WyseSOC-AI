# Phase 9 — Controlled SOC Pilot Design

---

## 1. Operational Modes

| Mode | Default? | Inference Behavior | Authoritative Incident Impact | SIEM Writeback / Auto-Close |
|---|---|---|---|---|
| `DISABLED` | **Yes** | No pilot jobs dispatched; standard workflows unchanged | None | Strictly prohibited |
| `SHADOW` | No | Runs full `VerdictTriageAgent` + validation + trust pipeline via configured provider; stores outcome in `pilot_evaluations` | **Zero mutation** to `Incident.ai_verdict` and `Investigation` (`is_shadow_pilot=True`) | Strictly prohibited |
| `ANALYST_ASSISTED` | No | Runs validated pipeline; surfaces recommendation, validation evidence, and trust score inside Human Review Queue (`ai_assurance`) | Analyst decision in `Investigation` and `PilotEvaluationRecord` stays authoritative | Strictly prohibited |

---

## 2. Hard Safety & Governance Constraints

1. **Schema-Enforced Prohibitions (`backend/app/schemas/pilot.py`)**: `PilotConfigUpdateRequest` rejects `allow_external_writeback=True` or `allow_auto_incident_closure=True` with HTTP `422` (`PILOT_SAFETY_VIOLATION`).
2. **Live No-Mock Enforcement (`backend/app/services/pilot_service.py` & `ai_verdict_service.py`)**: Requests labeled `source_type="LIVE"` force `allow_simulated_fallback=False`. When Server 2 is offline, evaluation fails cleanly with `SERVER2_OFFLINE` (`status="FAILED"`), never substituting mock verdicts or simulated token counts.
3. **Configuration Versioning & Safe Rollback**: Every update, activation, pause, resume, disable, or rollback increments `version_number`, records a full snapshot in `pilot_config_history`, and writes an HMAC-signed entry in `audit_logs` via `AuditService.log()`. Disabling or rolling back preserves all historical evaluations, analyst decisions, and audit logs.
4. **3-Role RBAC Matrix**:
   - **Administrator**: Configure pilot, activate `SHADOW`/`ANALYST_ASSISTED`, pause, resume, safe disable, rollback config, perform independent supervisor verification (`require_admin`).
   - **SOC Analyst**: View pilot config/metrics/history/evaluations/eligibility reports, run controlled pilot batches (`POST /api/pilot/run-batch`, `POST /api/pilot/evaluate/{id}`), submit non-destructive feedback (`POST /api/pilot/evaluations/{id}/feedback`). Blocked (`403`) on Admin lifecycle & supervisor actions.
   - **Read-Only Viewer**: Read-only access to `/api/pilot/config`, `/metrics`, `/history`, `/audit`, `/evaluations`, and `/eligibility-report`. Blocked (`403`) on all mutations and batch execution.

---

## 3. Configurable Parameters

- Identity & Scope: `pilot_name`, `description`, `selected_rule_ids`, `selected_archetypes`, `included_severities` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`), `ingestion_source` (`ALL`, `LIVE`, `HISTORICAL`).
- Budgets & Throttling: `hourly_evaluation_budget`, `daily_evaluation_budget`, `max_concurrent_inference`, `request_timeout_seconds`.
- Governance & Fault Tolerance: `require_analyst_review`, `require_approved_policy`, `error_handling_policy` (`ABSTAIN_AND_LOG` or `PAUSE_ON_CONSECUTIVE_ERRORS`), `consecutive_error_pause_threshold`, `reporting_schedule` (`HOURLY`, `DAILY`, `MANUAL`).

