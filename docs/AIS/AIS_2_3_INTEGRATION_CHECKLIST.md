# AIS 2.3 Server 1 + Server 2 Integration Pre-Flight & Execution Checklist

> **Current Environment Boundary:** Code development and local automated tests run against local SQLite and HTTP mocks. Remote Server 1 PostgreSQL, Redis/Celery workers, FortiSIEM Supervisor, and Server 2 GPU vLLM are **NOT VERIFIED** from this workstation.

## 1. Non-Destructive Diagnostic Tooling

- **Service:** `backend/app/services/integration_diagnostic_service.py` (`IntegrationDiagnosticService`)
- **CLI Runner:** `backend/scripts/run_integration_diagnostics.py`
  ```bash
  # Local/offline read-only schema, parity, config & GT audit
  cd backend && python scripts/run_integration_diagnostics.py --format json

  # Staging/Integration read-only check WITH live Server 2 + Redis/Celery probes
  cd backend && python scripts/run_integration_diagnostics.py --probe-remote --strict-prod --fail-on-blocker
  ```
- **API Endpoint (Read-Only, Analyst/Admin):** `GET /api/verdict-intelligence/integration-diagnostics?probe_remote=false`
- **Guarantees:** Zero incident mutations, zero SIEM alert closures, zero database writes (`read_only=true`, `database_mutated=false`, `external_mutations=false`), and full secret redaction.

## 2. Server 1 + Server 2 Step-by-Step Verification Sequence

1. **Configuration & Operating Mode Verification:**
   - Set `APP_ENV="production"` (or integration env) and `PLATFORM_OPERATING_MODE="integration"` / `"advisory"` in Server 1 secret/systemd environment (never `'development'`).
   - Confirm `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false"` and `FORTISIEM_MOCK_FALLBACK="false"`.
   - Confirm strong `SECRET_KEY` and `AUDIT_SIGNING_KEY` (`>= 32` chars).
2. **PostgreSQL & Alembic Schema Verification:**
   - Confirm `DATABASE_URL` and `SYNC_DATABASE_URL` point to Server 1 PostgreSQL.
   - Verify `alembic current` matches head `008_soc_pilot` (zero runtime DDL).
3. **Rule Corpus, Canonical Mapping & Workbench Parity:**
   - Run `run_integration_diagnostics.py --probe-remote --rule-id PH_RULE_HEAVY_TCP_HOST_SCAN`.
   - Verify `corpus_and_canonical_associations.dangling_rule_fk_count == 0` and `workbench_ais_parity.parity_mismatches_count == 0`.
4. **Ground-Truth Readiness & `is_ml_generated` Audit:**
   - Verify `ground_truth_eligibility_and_ml_audit.summary.ml_reevaluation_audit.mutated_records == 0`.
   - Review `false_positive_ml_candidates` and `human_verified_ready_candidates` via human analyst governance before any manual label re-verification.
5. **G1 Authoritative Rule Definitions:**
   - Inspect `g1_authoritative_definition_coverage`; import authoritative FortiSIEM XML definitions for priority rules where `definition_status == INCOMPLETE`.
6. **Server 2 GPU LLM Endpoint & Context Budget Capacity:**
   - Verify `server2_llm_readiness.reachable == true`, `active_model_present == true`, and check `verified_server_max_model_len`.
   - Keep `LOCAL_LLM_CONTEXT_BUDGET=4096` by default; switch to `8192` ONLY if `verified_server_max_model_len >= 8192` is confirmed live.
7. **Redis & Celery `simulation_replay` Worker:**
   - With `USE_ASYNC_CELERY=true`, verify `redis_celery_readiness.redis_reachable == true` and at least one live Celery worker appears in `simulation_replay_workers`.
8. **Controlled Real-LLM Historical Simulation (Target Rule):**
   - Execute `POST /api/prompts/rule/{rule_id}/evaluate-simulation?provider_type=OPENAI_COMPATIBLE&async_execution=true` for target rule (`PH_RULE_HEAVY_TCP_HOST_SCAN`) and verify `validation_state`, real token usage ledger, zero GT leakage, and honest G8 scoring.
9. **Autonomous Governance Verification:**
   - Confirm `policy_digest_and_governance.autonomous_default_blocked == true` for any rule without completed non-simulated empirical G8 certification.

