# AI Verdict — Comprehensive Codebase Gap Audit & Findings Register

- **Updated At:** 2026-11-10T19:55:00+05:30
- **Repository Commit:** `0148142` (`0148142f3abd6dad87a903b90f7b25edb8d41def`)
- **Audit Scope:** All 25+ frontend pages, 22 backend FastAPI router files, 45+ backend services, 19 ORM model modules, 6 Alembic migrations, Celery/APScheduler workers, and existing pytest suites.

---

## 1. Classification Legend

| Status | Meaning |
|---|---|
| `IMPLEMENTED_VERIFIED` | Code exists, runtime connection traced end-to-end, and automated tests pass after final edits. |
| `IMPLEMENTED_UNVERIFIED` | Code exists and wired, but runtime hardware/external dependency prevented live execution verification. |
| `PARTIAL` | Core implementation verified in local/mocked scope; external appliance/browser/worker verification or sub-requirement remains incomplete. |
| `DEFECTIVE` *(Pre-Remediation)* | Broken, bypassed, hardcoded, or mismatched contract found during audit (detailed with remediation status below). |
| `MISSING` / `NOT_APPLICABLE` | Absent functionality or outside test/runtime scope with justification. |

Note on small service files (~300–500 bytes): All 10 compact files (`agent_memory_engine.py`, `agent_policy_engine.py`, `detection_context_engine.py`, `evidence_integrity_guardrail.py`, `inference_health_monitor.py`, `review_orchestrator.py`, `sentinel_ingest_worker.py`, `validation_engine.py`, `verdict_evaluation_engine.py`, `verdict_triage_agent.py`) were inspected and confirmed to be intentional backward-compatible nomenclature re-export shims, **not** dead stubs.

---

## 2. Prioritized Findings & Remediation Register

### P0 — Critical Verdict Safety, Trustworthiness & Persistence Defects

| ID | Severity | Audit Finding & Pre-Fix Status | Root Cause & Affected Code | Remediation Implemented & Post-Fix Status |
|---|---|---|---|---|
| **GAP-01** | **P0** | **AIS 2.1 Trustworthiness & Guardrail Engines Disconnected from Live Triage** (`DEFECTIVE` / `MISSING`) | `VerdictTriageAgent.evaluate_incident` ([`ai_verdict_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py)) only ran `IndependentVerdictValidator` and hardcoded `"calibration_status": "NOT_CALIBRATED"`, `"is_calibrated": False`, never calling `VerdictTrustworthinessEngine` or persisting `VerdictTrustAssessmentRecord` / `EvidenceSufficiencyAssessmentRecord`. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Wired `VerdictTrustworthinessEngine` + real DB calibration lookup into `evaluate_incident`, persisted AIS 2.1 records, synchronized hard guardrail blocks (`G1/G2/G3/G4/G6/G7`), and surfaced real scores in `incident.ai_verdict`. |
| **GAP-02** | **P0** | **Empty-Claim Validation Bypass & Schema Mismatch** (`DEFECTIVE`) | `ModelClaimExtractor` returned `grounding_ratio=1.0` when `total_claims == 0`; `IndependentVerdictValidator` (`check 5`) skipped claim checks when `total_claims == 0`; `PolicyCompilerService.MODEL_RESPONSE_SCHEMA` asked for `claim_text`/`cited_evidence_ids`, `OpenAICompatibleProvider` dropped `supporting_claims` entirely, and `ModelClaimExtractor` expected `field`/`asserted_value`/`evidence_ids`. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Updated `OpenAICompatibleProvider` to instruct & extract `supporting_claims` + `contradictory_evidence`; unified `ModelClaimExtractor` & `VerdictClaimValidator` for V3 & P2 schemas; enforced `grounded_claims >= 1` & blanket-FP rejection in both `IndependentVerdictValidator` & `VerdictGuardrailsEngine`. |
| **GAP-03** | **P0** | **Fabricated Historical Metrics (`10`, `85.0%`) & Simulation Blindness** (`DEFECTIVE`) | `api/verdict_intelligence.py:114-115` hardcoded `historical_sample_count=10, historical_accuracy=85.0` and silently simulated in prod; `PolicySimulationService` passed `total_cases` (including excluded other-rule cases!) + `85.0` and ignored `policy_version_id` and `provider_type`. Also `VerdictTrustworthinessEngine` failed to unify `hist_status == "CALIBRATED"` with `apply_guardrails(is_calibrated=...)`. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Added `PolicySimulationService.get_rule_calibration_stats()` reading verified DB records; updated `evaluate_incident_trust` & `PolicySimulationService` to forbid unpermitted/production simulation, honor candidate `PromptVersion` (`policy_digest`, policy-aware indicators), and honor `provider_type`. |
| **GAP-04** | **P0** | **Unvalidated Model Proposals Logged Downstream, Unmapped Policy Bypass & Missing Reevaluation** (`DEFECTIVE`) | `ai_verdict_service.py` logged unvalidated `verdict.verdict` & `verdict.confidence` to `Investigation.analyst_notes`, `TelemetryTimelineRecord`, `TokenUsageRecord`, and `AuditLog`; `if rule:` skipped policy approval when `rule is None`; deferred `POLICY_NOT_APPROVED` / `CRITICAL_TELEMETRY_MISSING` wrote non-null `ai_verdict` never re-evaluated by `reconcile_pending_triage`; concurrent evaluations risked duplicate notes. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Enforced `POLICY_NOT_APPROVED` when `active_v` absent even if `rule is None`; logged authoritative `final_auth_verdict` & validated confidence across all downstream tables; added event-loop-scoped per-incident `asyncio.Lock` & idempotent note upsert; tagged recoverable abstentions `reevaluation_eligible=True` and wired bounded reevaluation (`attempts < 3`) upon policy approval. |

---

### P1 — Quality Gates, Normalization, Worker & UI/API Contract Gaps

| ID | Severity | Audit Finding & Pre-Fix Status | Root Cause & Affected Code | Remediation Implemented & Post-Fix Status |
|---|---|---|---|---|
| **GAP-05** | **P1** | **Quality Gate G5 Dilution, Weak G7 Blockers, & Unenforced G8 Digest/Approval** (`DEFECTIVE`) | `PolicyQualityValidator._evaluate_gate_5_fp_criteria` diluted `fp_indicators` with `common_prompt` (containing `"not"` and `"verify"`); G7 emitted zero hard blockers; G8 ignored `policy_digest` edits; `PromptStudioService.approve_version` ignored simulation regressions; `rollback_version` skipped quality validation; `api/prompts.py` `/summary` hardcoded `"NOT_EVALUATED"`. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Isolated `fp_lower` check in G5; added G7 blocking checks on blank Section 4 & TP/FP self-contradiction; added G8 digest staleness detection; enforced latest completed G8 simulation regression checks inside `approve_version`; validated `rollback_version` via Quality Gates; wired `/summary` to real DB records. |
| **GAP-06** | **P1** | **Unwired `PolicyLifecycleMonitor`, Auto-Activated Draft in `pull_rule_and_register`, & Prod Fallback Gap** (`DEFECTIVE`) | `PolicyLifecycleMonitor` was imported in `api/prompts.py` but never invoked on SIEM rule updates or verified feedback; `fortisiem_service.pull_rule_and_register` assigned `rp.active_version_id = draft.id` (DRAFT auto-activation); `fortisiem_service.py:1570,1627` omitted production `is_prod` mock block. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Removed draft auto-activation in `pull_rule_and_register`; wired `PolicyLifecycleMonitor` into `import_authoritative_rule_definition`, `pull_rule_and_register(..., force_refresh=True)`, and `LearningService.update_verification_status(..., "VERIFIED")`; enforced `is_prod` mock prohibition in `fortisiem_service.py`. |
| **GAP-07** | **P1** | **`EvidenceSufficiencyEngine` Non-Telemetry Blocker, Colliding IDs & Claim Validator Quirks** (`DEFECTIVE`) | `EvidenceRequirementMapper` flagged `detection.authoritative_threshold` as `required_for_tp=True, critical=False`, causing `EvidenceSufficiencyEngine` (`critical or required_for_tp`) to fail every live incident as missing mandatory field; `CanonicalEvidenceRecord.generate_id` collided on multi-event `PAYLOAD` values; `VerdictClaimValidator` lacked canonical ID map, failed on string `"Process Blocked": "true"`, and falsely grounded `"high"` / `"rule"` substrings. | **REMEDIATED (`IMPLEMENTED_VERIFIED`)**: Prioritized `critical=True` & excluded non-telemetry `detection.*` defaults in `EvidenceSufficiencyEngine`; digest-salted colliding IDs & added FortiSIEM aliases (`sentBytes64`, `direction`, `processBlocked`); fixed `VerdictClaimValidator` canonical lookup, generalized threshold guard, boolean string handling, and `_LOW_SIGNAL_VALUES` filtering. |
| **GAP-08** | **P1** | **Broken Celery `run_dry_run_job_task`** (`DEFECTIVE`) | `backend/app/workers/tasks.py:200` imported nonexistent `dry_run_service` singleton and passed invalid `(db=session, job_id=...)` args to `DryRunService`. | **REMEDIATED (`IMPLEMENTED_VERIFIED` import/wiring; `PARTIAL` on Redis broker)**: Replaced with `DryRunService(session).execute_dry_run_job(config_id=...)` with `DryRunJob.id` resolution fallback. |
| **GAP-09** | **P1** | **Frontend/API Contract Mismatches (`model-payload`, Workbench Badges, Trust Fallback)** (`DEFECTIVE`) | `GET /api/incidents/{id}/model-payload` & `ModelFacingIncidentPayload` omitted `canonical_evidence`; `ai-triage-workbench/[id]/page.tsx` read nonexistent keys (`evidence_category`, `canonical_field`), hardcoded `• GPU Live`, and displayed `0/0` claims as green `100%`; `get_incident_trust` passed `{}` to `TrustScoreDimensionBreakdown`; `verdict-intelligence` silently forced `allow_simulation: true`. | **REMEDIATED (`IMPLEMENTED_VERIFIED` backend/tsc; `PARTIAL` browser E2E)**: Added `canonical_evidence` to `ModelFacingIncidentPayload` & endpoint; fixed UI badges, `0/0` neutral display, and field mapping fallback; hardened `get_incident_trust` schema & added explicit UI simulation toggle. |

---

## 3. Remaining External / Hardware Verification Gaps (Unchanged / Non-Simulated Scope)

1. **Physical Server 2 vLLM Live Roundtrip (`PARTIAL` verification):** Client schema & fail-closed offline handling verified, while live inference against GPU weights and Prometheus `/metrics` scraping could not execute offline.
2. **Live FortiSIEM Supervisor API (`PARTIAL` verification):** Offline ingestion, XML import, and fixture sync pass; live appliance TLS/REST connectivity unverified here.
3. **PostgreSQL & Distributed Celery Redis Cluster (`PARTIAL` verification):** Alembic `001`–`006` and pooling config pass in SQLite/pytest; live external Postgres upgrade and multi-process Redis Celery execution unexecuted in unit sandbox.
4. **Headless Browser UI Tests (`PARTIAL` verification):** `npx tsc --noEmit` & `npm run test:admin-guide` pass; Playwright DOM click-through tests do not exist yet.

