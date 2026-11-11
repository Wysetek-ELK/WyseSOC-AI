# AIS 2.3 Remaining Gaps & Boundary Statement

> **Status Distinction:**
> - **Development Complete:** All local AIS 2.3 implementation, security hardening, context-budget optimizations, integration diagnostics tooling, and automated regression tests (`325` backend + `16` frontend) are complete on `local workspace`.
> - **Integration NOT Verified:** Multi-host Server 1 + Server 2 runtime integration has **NOT** been executed against live infrastructure.
> - **Production Readiness NOT Established:** Autonomous triage certification and production deployment signoff remain blocked until remote staging/integration tests pass.

## 1. Environment & Dependency Boundaries Remaining Unverified Locally

1. **Server 1 Production PostgreSQL & Live Corpus (2,900+ Incidents / 34 Rules):**
   - Local testing used SQLite + synthetic fixtures. Running `run_integration_diagnostics.py --probe-remote` on Server 1 is still required to observe exact production counts for canonical rule-incident links, G1 incomplete definitions, and `is_ml_generated` candidate rows.
2. **Server 2 GPU Local LLM (`OPENAI_COMPATIBLE` / vLLM):**
   - Live inference latency, structured JSON schema adherence across real historical FortiSIEM payloads, actual `max_model_len` capacity (`4096` vs `8192`), and concurrent slot throughput on Server 2 GPU remain **NOT VERIFIED** locally.
3. **Redis Broker & Celery `simulation_replay` Worker:**
   - Distributed task queuing, worker consumption on the `simulation_replay` queue, and cancellation propagation under Redis/Celery require remote Server 1 process verification (`--probe-remote`).
4. **Live FortiSIEM Ingestion & Human Review Queue Workflows:**
   - Authoritative XML/rule definition completeness across the 34 production SIEM rules and analyst re-adjudication of `is_ml_generated` false-substring candidates (`RECLASSIFY_FALSE_SUBSTRING_NEEDS_REVIEW`) must be executed by authorized SOC administrators on Server 1.
5. **Empirical G8 Policy Validation & Calibration:**
   - No rule is pre-authorized for autonomous operation; `autonomous_operation_eligible` remains `false` until real non-simulated `OPENAI_COMPATIBLE` G8 evaluation runs (`N >= 5` independently verified incidents per rule, balanced accuracy `>= 80%`, `0` critical false negatives) and explicit governance signoffs complete.

## 2. Intentionally Deferred Items

- **Removal of Legacy Dry-Run Tables (`dry_run_configs`, `dry_run_jobs`, `dry_run_results`, `rule_maturity_evaluations`):** Retained intentionally behind backward-compatible adapters in `DryRunService` and `RuleMaturityService` so historical evaluation records and Phase 1–4 API consumers remain unbroken until post-integration cutover.

