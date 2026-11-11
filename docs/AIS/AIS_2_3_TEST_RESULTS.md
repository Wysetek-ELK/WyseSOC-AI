# AIS 2.3 Test & Verification Results

All automated checks below were executed cleanly **after the final code edit** in local development/test mode (SQLite + mocked HTTP + local Chromium Playwright; remote Server 1 PostgreSQL, Redis/Celery daemon, FortiSIEM Supervisor, and Server 2 vLLM were **NOT VERIFIED** locally).

## 1. Automated Verification Summary

| Suite / Command | Outcome | Observed Result | Scope & Environment |
| --- | --- | --- | --- |
| `cd backend; python -m pytest -q` | **PASSED** | `325 passed in 505.00s` (0 failed, 0 skipped) | Complete backend unit, security, AIS 2.0/2.1/2.2/2.3, & Playwright browser E2E suite |
| `cd backend; python -m pytest tests/test_ais_2_3_remediation.py -v` | **PASSED** | `5 passed` (included inside `325 passed`) | AIS-F11 consolidation, AIS-F12 `.env`/modes/fail-closed, 4-archetype 4096/8192 context budget + clamping, read-only integration diagnostics |
| `cd frontend; node --experimental-strip-types --test tests/quality-export.test.mjs tests/admin-guide.test.mjs` | **PASSED** | `16 passed, 0 failed` | Quality Gates export schema/CSV CWE-1236 & Admin Guide metadata tests |
| `cd frontend; npx tsc --noEmit` | **PASSED** | Exit code `0` | Full frontend TypeScript type check |
| `cd frontend; npm run build` | **PASSED** | Exit code `0` (`32/32` routes compiled) | Next.js `16.4.5` (Turbopack) production bundle build |
| `python scripts/validate_feature_registry.py` | **PASSED** | `OK: Registry verified (44 features, 19 modules, Impl=100.0%, Verif=88.5%)` | Feature registry consistency check |
| `cd backend; python scripts/run_integration_diagnostics.py --format json` | **PASSED (Local Only)** | `overall_status = LOCAL_VERIFIED_REMOTE_NOT_PROBED`, `read_only = true`, `database_mutated = false`, `external_mutations = false` | Local SQLite DB (`alembic head = 008_soc_pilot`, 4 rules, 26 incidents, Workbench/AIS parity PASS); Server 2 & Redis marked `NOT_PROBED` / `DISABLED_IN_CONFIG` |

## 2. Highlights Verified by New Suite (`backend/tests/test_ais_2_3_remediation.py`)

1. `test_1_consolidated_dry_run_adapter_uses_canonical_pipeline_and_preserves_legacy`: Proved `DryRunService` executes through `run_shared_verdict_pipeline`, isolates sibling rules, creates linked canonical `HistoricalEvaluationRunRecord`/`ResultRecord` entries, preserves legacy `DryRunResult` rows, prevents simulated runs from granting autonomous certification, and surfaces canonical metrics in `RuleMaturityService` and `EvaluationService`.
2. `test_2_idempotent_env_upsert_never_duplicates_blocks_or_secrets`: Proved 5 sequential `LLMConfigService.update_config()` updates against `.env` keep exactly 1 section header, 1 entry per `LOCAL_LLM_*` key, preserve unrelated env keys, and omit secrets.
3. `test_3_operating_modes_fail_closed_and_secret_redaction`: Proved explicit `development` mode is blocked in `APP_ENV=production`, invalid operating modes fail closed, mock fallbacks are forced `False` in production, `RuntimeConfigValidator.enforce_fail_closed` raises on mock/SQLite/unverified prod configs, and zero plaintext credentials appear in exported JSON snapshots.
4. `test_4_context_budget_readiness_across_all_archetypes_and_verified_capacity`: Proved `Heavy TCP Host Scan` (`NETWORK_SCAN`, 3,515 tokens), `Suspicious PowerShell Execution` (`MALWARE_EXECUTION`, 2,743 tokens), `Large Outbound Data Exfiltration` (`NETWORK_EXFILTRATION`, 3,404 tokens), and `Repeated Brute Force Logon Failure` (`AUTHENTICATION`, 2,589 tokens) all succeed under `4096` and `8192`, Server 2 `max_model_len=4096` safely clamps configured `8192`, `OpenAICompatibleProvider` omits duplicated Section 11 JSON schemas, and oversized critical telemetry still abstains safely with `CONTEXT_WINDOW_EXCEEDED`.
5. `test_5_non_destructive_integration_diagnostics_api_and_service`: Proved `GET /api/verdict-intelligence/integration-diagnostics` & `IntegrationDiagnosticService` execute strictly read-only with zero mutations to incidents or `is_ml_generated` rows while accurately reporting rule counts, parity, digests, and probed Server 2 `max_model_len=8192`.

