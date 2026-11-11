# Phase 9 — Pilot Execution Orchestration & Workflow

---

## 1. Execution Sequence

1. **Trigger Points**:
   - Scheduled / API FortiSIEM pull hook (`FortiSIEMService.pull_all_incidents` triggers `PilotService.evaluate_incident_for_pilot` only when active pilot `mode != "DISABLED"` and `not is_paused`).
   - Manual controlled batch execution (`POST /api/pilot/run-batch` or single incident `POST /api/pilot/evaluate/{incident_id}`).
2. **Pre-Inference Gates (`PilotService.check_incident_eligibility`)**:
   - Verify `mode != "DISABLED"` and `not is_paused`.
   - Enforce `ingestion_source` match (`LIVE` vs `HISTORICAL` vs `ALL`).
   - Match `selected_rule_ids`, `selected_archetypes`, and `included_severities`.
   - Enforce rolling 1-hour and 24-hour `EVALUATED` budget caps against `pilot_evaluations`.
   - Enforce per-`(pilot_id, mode, incident_id)` idempotency (`IDEMPOTENT_SKIP` when already `EVALUATED` or `ABSTAINED`).
3. **Locking & Triage Pipeline**:
   - Acquire DB-backed + optional Redis distributed lease (`pilot_eval:{pilot_id}:{incident_id}`) via `DistributedLockManager.acquire()`.
   - Resolve approved `PromptVersion` and `RuleEvidenceContract`, normalize telemetry via `EvidenceNormalizationService`, compute `evidence_snapshot_hash` (SHA-256), and run `VerdictTriageAgent.evaluate_incident(..., pilot_context=...)`.
   - Live runs invoke `OpenAICompatibleProvider` with configurable `request_timeout_seconds` / `LOCAL_LLM_CONTEXT_BUDGET` / `LOCAL_LLM_MAX_TOKENS`; validator & trust engine cannot be bypassed.
4. **Failure & Circuit Breaker Handling**:
   - On `LocalLLMUnavailableError` or unexpected runtime exception, `await self.db.rollback()` cleanly clears session state, logs `PilotEvaluationRecord(eligibility_status="FAILED")` using pre-snapshotted primitives, increments `PilotService._consecutive_errors`, and if `error_handling_policy == "PAUSE_ON_CONSECUTIVE_ERRORS"` at threshold, flips `is_paused=True` and logs `PILOT_AUTO_PAUSED_ERRORS` in `pilot_config_history` and `audit_logs`.
   - Concurrently respects `gpu_workload_manager` circuit breaker state reflected in `GET /api/pilot/metrics`.

---

## 2. Provenance Captured Per Record

Every row in `pilot_evaluations` stores:
- Execution metadata (`pilot_id`, `pilot_version`, `execution_mode`, `source_type`, `eligibility_status`)
- Policy & model lineage (`policy_version_id`, `policy_version_number`, `policy_digest`, `model_identifier`, `is_simulated`)
- Evidence snapshot digest & itemized lists (`evidence_snapshot_hash`, `supporting_evidence`, `contradictory_evidence`, `missing_evidence`)
- Validation & trust outcome (`proposed_verdict`, `validated_verdict`, `validation_status`, `abstention_reason`, capped `trust_score`, `raw_trust_score`, `is_calibrated`)
- Resource telemetry (`latency_ms`, `prompt_tokens`, `completion_tokens`, `total_tokens`)
- Separated analyst & supervisor fields (`analyst_feedback_action`, `analyst_decision`, `analyst_override_reason`, `analyst_user`, `analyst_decided_at`, `supervisor_verified`, `supervisor_user`, `supervisor_verified_at`).

