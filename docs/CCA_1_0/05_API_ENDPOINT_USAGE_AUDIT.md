# 05 — API Endpoint Usage Audit

## 1. Endpoint Inventory Summary
- **Total Registered Handler Definitions:** 187 across 25 API router modules.
- **Status Breakdown:** {'ACTIVELY_USED': 166, 'DEVELOPMENT_ONLY': 1, 'POTENTIALLY_UNUSED': 12, 'ADMINISTRATIVE': 6, 'EXTERNALLY_USED': 2}
- **Duplicate Route Anomalies:**
  1. `backend/app/api/health.py` defines `@router.get("/health")` & `@router.get("/api/health")` (and `/metrics` & `/api/metrics`), while `main.py:310-311` mounts `health.router` at both `""` and `"/api"`. This creates duplicate `/api/health` and `/api/metrics` registrations and unintended `/api/api/health` and `/api/api/metrics` routes.
  2. `backend/app/main.py` mounts 5 routers (`prompts`, `verdict_intelligence`, `rule_learning`, `ais_evaluation`, `ground_truth`) under both `/api` and `/api/v1`. Zero frontend files call `/api/v1`; only 4 backend test suites call `/api/v1`.

## 2. Endpoints Without Frontend Consumers (20 Handlers)

| Method | Path | Handler | Auth | Tests | Scripts | Status | Recommended Action |
|---|---|---|---|---:|---:|---|---|
| `GET` | `/api/dev/status` | `backend/app/api/dev.py:12` | `Public / Unauthenticated` | 1 | 0 | `DEVELOPMENT_ONLY` | `RETAIN (dev-guarded)` |
| `POST` | `/api/dry-run/jobs/{job_id}/cancel` | `backend/app/api/dry_run.py:302` | `get_db, require_analyst` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/dry-run/jobs/{job_id}/progress` | `backend/app/api/dry_run.py:338` | `get_db, get_current_active_user` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/ground-truth/cohorts/{cohort_key}/audit` | `backend/app/api/ground_truth.py:214` | `get_db, get_current_active_user` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/ground-truth/ais27/runtime-verify` | `backend/app/api/ground_truth.py:228` | `require_admin` | 0 | 1 | `ADMINISTRATIVE` | `RETAIN (AIS 2.7 CLI/Benchmark)` |
| `POST` | `/api/ground-truth/ais27/smoke-test` | `backend/app/api/ground_truth.py:238` | `require_admin` | 0 | 1 | `ADMINISTRATIVE` | `RETAIN (AIS 2.7 CLI/Benchmark)` |
| `POST` | `/api/ground-truth/ais27/cohorts/{cohort_key}/incidents/{incident_id}/run` | `backend/app/api/ground_truth.py:248` | `get_db, require_admin` | 0 | 3 | `ADMINISTRATIVE` | `RETAIN (AIS 2.7 CLI/Benchmark)` |
| `GET` | `/api/metrics` | `backend/app/api/health.py:129` | `get_db` | 0 | 0 | `EXTERNALLY_USED` | `FIX_DUPLICATE_ROUTE_REGISTRATION` |
| `GET` | `/api/imports/jobs/{job_id}` | `backend/app/api/imports.py:90` | `get_current_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `PUT` | `/api/learning/records/{id}/verify` | `backend/app/api/learning.py:68` | `get_db, require_admin` | 1 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `POST` | `/api/pilot/evaluate/{incident_id}` | `backend/app/api/pilot.py:178` | `get_db, require_analyst` | 2 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/pilot/eligibility-report` | `backend/app/api/pilot.py:370` | `get_db, get_current_active_user` | 1 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/prompts/rule/{rule_id}/assessments` | `backend/app/api/prompts.py:681` | `get_db, get_current_active_user` | 1 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `POST` | `/api/prompts/rule/{rule_id}/suspend-ai` | `backend/app/api/prompts.py:1277` | `get_db, require_admin` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `POST` | `/api/prompts/actual-prompt/retention/cleanup` | `backend/app/api/prompts.py:1931` | `get_db, require_admin` | 1 | 0 | `ADMINISTRATIVE` | `VERIFY_FIRST` |
| `POST` | `/api/rules/sync/fortisiem` | `backend/app/api/rules.py:296` | `get_db` | 1 | 0 | `ADMINISTRATIVE` | `VERIFY_FIRST` |
| `GET` | `/api/rules/{identifier}/compiled-policy` | `backend/app/api/rules.py:352` | `get_current_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/rules/{identifier}/calibration-report` | `backend/app/api/rules.py:376` | `get_current_user, get_db` | 1 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `PATCH` | `/api/users/{user_id}` | `backend/app/api/users.py:71` | `get_admin_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` | `VERIFY_FIRST` |
| `GET` | `/api/verdict-intelligence/integration-diagnostics` | `backend/app/api/verdict_intelligence.py:671` | `get_db, require_analyst` | 1 | 0 | `ADMINISTRATIVE` | `VERIFY_FIRST` |

## 3. Complete Endpoint Matrix (187 Handlers)

| Method | Full Path(s) | Handler | Auth | FE Refs | Test Refs | Status |
|---|---|---|---|---:|---:|---|
| `GET` | `/api/ais/rules/{rule_uuid}/evaluation-status, /api/v1/ais/rules/{rule_uuid}/evaluation-status` | `backend/app/api/ais_evaluation.py:36` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/ais/incidents/{incident_id}/evaluation-history, /api/v1/ais/incidents/{incident_id}/evaluation-history` | `backend/app/api/ais_evaluation.py:95` | `get_db, get_current_active_user` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/ais/rules/{rule_uuid}/evaluate-missing-batch, /api/v1/ais/rules/{rule_uuid}/evaluate-missing-batch` | `backend/app/api/ais_evaluation.py:129` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/audit` | `backend/app/api/audit.py:16` | `get_db` | 1 | 3 | `ACTIVELY_USED` |
| `POST` | `/api/auth/login` | `backend/app/api/auth.py:17` | `get_db` | 1 | 4 | `ACTIVELY_USED` |
| `POST` | `/api/auth/logout` | `backend/app/api/auth.py:93` | `get_current_user, get_db` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/auth/me` | `backend/app/api/auth.py:122` | `get_current_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/chat/status` | `backend/app/api/chat.py:54` | `get_current_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/chat/message` | `backend/app/api/chat.py:257` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/chat/stream` | `backend/app/api/chat.py:366` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dashboard/metrics` | `backend/app/api/dashboard.py:17` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dashboard/llm-status` | `backend/app/api/dashboard.py:26` | `get_current_user` | 2 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dev/status` | `backend/app/api/dev.py:12` | `Public / Unauthenticated` | 0 | 1 | `DEVELOPMENT_ONLY` |
| `POST` | `/api/dry-run/configs` | `backend/app/api/dry_run.py:28` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dry-run/configs` | `backend/app/api/dry_run.py:68` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dry-run/configs/{config_id}` | `backend/app/api/dry_run.py:95` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/dry-run/trigger` | `backend/app/api/dry_run.py:121` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dry-run/jobs` | `backend/app/api/dry_run.py:177` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dry-run/jobs/{job_id}` | `backend/app/api/dry_run.py:203` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/dry-run/jobs/{job_id}/results` | `backend/app/api/dry_run.py:229` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/dry-run/jobs/{job_id}/cancel` | `backend/app/api/dry_run.py:302` | `get_db, require_analyst` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/dry-run/jobs/{job_id}/progress` | `backend/app/api/dry_run.py:338` | `get_db, get_current_active_user` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/evaluations/job/{job_id}/metrics` | `backend/app/api/evaluations.py:28` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/evaluations/prompt-comparison/{rule_id}` | `backend/app/api/evaluations.py:46` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/evaluations/rule-maturity` | `backend/app/api/evaluations.py:64` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/evaluations/rule-maturity/{rule_id}/approve` | `backend/app/api/evaluations.py:74` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/evaluations/job/{job_id}/export/csv` | `backend/app/api/evaluations.py:135` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/evaluations/job/{job_id}/export/json` | `backend/app/api/evaluations.py:157` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/fortisiem/status` | `backend/app/api/fortisiem.py:37` | `get_current_user, get_db` | 3 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/fortisiem/config` | `backend/app/api/fortisiem.py:63` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/config` | `backend/app/api/fortisiem.py:74` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/test-connection` | `backend/app/api/fortisiem.py:97` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/fetch` | `backend/app/api/fortisiem.py:116` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/pull-all` | `backend/app/api/fortisiem.py:143` | `get_db` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/fortisiem/scheduler/status` | `backend/app/api/fortisiem.py:174` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/process-pending-verdicts` | `backend/app/api/fortisiem.py:193` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/scheduler/start` | `backend/app/api/fortisiem.py:263` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/scheduler/stop` | `backend/app/api/fortisiem.py:285` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/scheduler/trigger` | `backend/app/api/fortisiem.py:301` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/batch-ai-verdict` | `backend/app/api/fortisiem.py:312` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/sync-rules` | `backend/app/api/fortisiem.py:331` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/pull-rule` | `backend/app/api/fortisiem.py:345` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/sync-resolutions` | `backend/app/api/fortisiem.py:364` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/fortisiem/incident/{incident_id}/sync-resolution` | `backend/app/api/fortisiem.py:378` | `get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/ground-truth/cohorts, /api/v1/ground-truth/cohorts` | `backend/app/api/ground_truth.py:32` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/ground-truth/cohorts/{cohort_key}/ensure, /api/v1/ground-truth/cohorts/{cohort_key}/ensure` | `backend/app/api/ground_truth.py:40` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/ground-truth/cohorts/{cohort_key}/queue, /api/v1/ground-truth/cohorts/{cohort_key}/queue` | `backend/app/api/ground_truth.py:56` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}, /api/v1/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}` | `backend/app/api/ground_truth.py:89` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/evidence, /api/v1/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/evidence` | `backend/app/api/ground_truth.py:107` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/review, /api/v1/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/review` | `backend/app/api/ground_truth.py:127` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/adjudicate, /api/v1/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/adjudicate` | `backend/app/api/ground_truth.py:149` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/ground-truth/cohorts/{cohort_key}/reviews/reopen, /api/v1/ground-truth/cohorts/{cohort_key}/reviews/reopen` | `backend/app/api/ground_truth.py:171` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/post-certification-comparison, /api/v1/ground-truth/cohorts/{cohort_key}/incidents/{incident_id}/post-certification-comparison` | `backend/app/api/ground_truth.py:194` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/ground-truth/cohorts/{cohort_key}/audit, /api/v1/ground-truth/cohorts/{cohort_key}/audit` | `backend/app/api/ground_truth.py:214` | `get_db, get_current_active_user` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/ground-truth/ais27/runtime-verify, /api/v1/ground-truth/ais27/runtime-verify` | `backend/app/api/ground_truth.py:228` | `require_admin` | 0 | 0 | `ADMINISTRATIVE` |
| `POST` | `/api/ground-truth/ais27/smoke-test, /api/v1/ground-truth/ais27/smoke-test` | `backend/app/api/ground_truth.py:238` | `require_admin` | 0 | 0 | `ADMINISTRATIVE` |
| `POST` | `/api/ground-truth/ais27/cohorts/{cohort_key}/incidents/{incident_id}/run, /api/v1/ground-truth/ais27/cohorts/{cohort_key}/incidents/{incident_id}/run` | `backend/app/api/ground_truth.py:248` | `get_db, require_admin` | 0 | 0 | `ADMINISTRATIVE` |
| `GET` | `/health, /api/health` | `backend/app/api/health.py:23` | `get_db` | 1 | 10 | `ACTIVELY_USED` |
| `GET` | `/api/health, /api/api/health` | `backend/app/api/health.py:23` | `get_db` | 1 | 5 | `ACTIVELY_USED` |
| `GET` | `/metrics, /api/metrics` | `backend/app/api/health.py:129` | `get_db` | 2 | 16 | `EXTERNALLY_USED` |
| `GET` | `/api/metrics, /api/api/metrics` | `backend/app/api/health.py:129` | `get_db` | 0 | 0 | `EXTERNALLY_USED` |
| `POST` | `/api/imports/upload` | `backend/app/api/imports.py:19` | `get_db` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/imports/jobs` | `backend/app/api/imports.py:78` | `get_current_user, get_db` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/imports/jobs/{job_id}` | `backend/app/api/imports.py:90` | `get_current_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/incidents` | `backend/app/api/incidents.py:31` | `get_current_user, get_db` | 3 | 15 | `ACTIVELY_USED` |
| `GET` | `/api/incidents/{identifier}` | `backend/app/api/incidents.py:70` | `get_current_user, get_db` | 3 | 13 | `ACTIVELY_USED` |
| `GET` | `/api/incidents/{identifier}/model-payload` | `backend/app/api/incidents.py:117` | `get_current_user, get_db` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/incidents/{identifier}/ai-verdict` | `backend/app/api/incidents.py:156` | `require_analyst, get_db` | 1 | 4 | `ACTIVELY_USED` |
| `GET` | `/api/incidents/{identifier}/timeline` | `backend/app/api/incidents.py:214` | `get_current_user, get_db` | 1 | 5 | `ACTIVELY_USED` |
| `DELETE` | `/api/incidents/purge-all` | `backend/app/api/incidents.py:239` | `require_admin, get_db` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/investigations/queue` | `backend/app/api/investigations.py:29` | `get_db, get_current_active_user` | 1 | 4 | `ACTIVELY_USED` |
| `GET` | `/api/investigations/{id}` | `backend/app/api/investigations.py:70` | `get_db, get_current_active_user` | 1 | 7 | `ACTIVELY_USED` |
| `GET` | `/api/investigations/by-incident/{incident_id}` | `backend/app/api/investigations.py:124` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/{id}/assign` | `backend/app/api/investigations.py:178` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/{id}/status` | `backend/app/api/investigations.py:203` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/{id}/questions` | `backend/app/api/investigations.py:232` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/questions/{question_id}/answer` | `backend/app/api/investigations.py:248` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/{id}/evidence` | `backend/app/api/investigations.py:263` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/investigations/{id}/verdict` | `backend/app/api/investigations.py:285` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `GET` | `/api/learning/records` | `backend/app/api/learning.py:23` | `get_db, get_current_active_user` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/learning/records/{id}` | `backend/app/api/learning.py:55` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `PUT` | `/api/learning/records/{id}/verify` | `backend/app/api/learning.py:68` | `get_db, require_admin` | 0 | 1 | `POTENTIALLY_UNUSED` |
| `POST` | `/api/learning/similar-cases` | `backend/app/api/learning.py:109` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/learning/seed-historical` | `backend/app/api/learning.py:120` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/llm/config` | `backend/app/api/llm_config.py:16` | `get_current_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/llm/config` | `backend/app/api/llm_config.py:27` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/llm/test-connection` | `backend/app/api/llm_config.py:49` | `Public / Unauthenticated` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/config` | `backend/app/api/pilot.py:33` | `get_db, get_current_active_user` | 1 | 2 | `ACTIVELY_USED` |
| `PUT` | `/api/pilot/config` | `backend/app/api/pilot.py:44` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/activate` | `backend/app/api/pilot.py:56` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/pause` | `backend/app/api/pilot.py:68` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/resume` | `backend/app/api/pilot.py:80` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/disable` | `backend/app/api/pilot.py:95` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/rollback` | `backend/app/api/pilot.py:107` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/history` | `backend/app/api/pilot.py:122` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/audit` | `backend/app/api/pilot.py:148` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/evaluate/{incident_id}` | `backend/app/api/pilot.py:178` | `get_db, require_analyst` | 0 | 2 | `POTENTIALLY_UNUSED` |
| `POST` | `/api/pilot/run-batch` | `backend/app/api/pilot.py:199` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/evaluations` | `backend/app/api/pilot.py:281` | `get_db, get_current_active_user` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/evaluations/{evaluation_id}/feedback` | `backend/app/api/pilot.py:328` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/pilot/evaluations/{evaluation_id}/supervisor-verify` | `backend/app/api/pilot.py:344` | `get_db, require_admin` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/metrics` | `backend/app/api/pilot.py:360` | `get_db, get_current_active_user` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/pilot/eligibility-report` | `backend/app/api/pilot.py:370` | `get_db, get_current_active_user` | 0 | 1 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/prompts/summary, /api/v1/prompts/summary` | `backend/app/api/prompts.py:92` | `get_db, get_current_active_user` | 1 | 4 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/readiness, /api/v1/prompts/rule/{rule_id}/readiness` | `backend/app/api/prompts.py:278` | `get_db, get_current_active_user` | 1 | 4 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/export, /api/v1/prompts/export` | `backend/app/api/prompts.py:309` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/quality/summary, /api/v1/prompts/quality/summary` | `backend/app/api/prompts.py:328` | `get_db, get_current_active_user` | 2 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/quality/bulk-assess, /api/v1/prompts/quality/bulk-assess` | `backend/app/api/prompts.py:341` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/quality/bulk-assess/{job_id}, /api/v1/prompts/quality/bulk-assess/{job_id}` | `backend/app/api/prompts.py:365` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}, /api/v1/prompts/rule/{rule_id}` | `backend/app/api/prompts.py:397` | `get_db, get_current_active_user` | 1 | 17 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/intelligence, /api/v1/prompts/rule/{rule_id}/intelligence` | `backend/app/api/prompts.py:447` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/analyze, /api/v1/prompts/rule/{rule_id}/analyze` | `backend/app/api/prompts.py:473` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/generate-intelligent-draft, /api/v1/prompts/rule/{rule_id}/generate-intelligent-draft` | `backend/app/api/prompts.py:503` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/assessments, /api/v1/prompts/rule/{rule_id}/assessments` | `backend/app/api/prompts.py:681` | `get_db, get_current_active_user` | 0 | 1 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/prompts/rule/{rule_id}/quality-preview, /api/v1/prompts/rule/{rule_id}/quality-preview` | `backend/app/api/prompts.py:736` | `get_db, get_current_active_user` | 1 | 4 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/validate-quality, /api/v1/prompts/rule/{rule_id}/validate-quality` | `backend/app/api/prompts.py:748` | `get_db, require_analyst` | 1 | 5 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/evaluate-simulation, /api/v1/prompts/rule/{rule_id}/evaluate-simulation` | `backend/app/api/prompts.py:787` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/drift, /api/v1/prompts/rule/{rule_id}/drift` | `backend/app/api/prompts.py:850` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/acknowledge-drift, /api/v1/prompts/rule/{rule_id}/acknowledge-drift` | `backend/app/api/prompts.py:876` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/export, /api/v1/prompts/rule/{rule_id}/export` | `backend/app/api/prompts.py:895` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/generate-draft, /api/v1/prompts/rule/{rule_id}/generate-draft` | `backend/app/api/prompts.py:917` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/draft, /api/v1/prompts/rule/{rule_id}/draft` | `backend/app/api/prompts.py:942` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/approve/{version_id}, /api/v1/prompts/rule/{rule_id}/approve/{version_id}` | `backend/app/api/prompts.py:988` | `get_db, require_admin` | 1 | 9 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/rollback/{version_id}, /api/v1/prompts/rule/{rule_id}/rollback/{version_id}` | `backend/app/api/prompts.py:1018` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/activate-approved/{version_id}, /api/v1/prompts/rule/{rule_id}/activate-approved/{version_id}` | `backend/app/api/prompts.py:1044` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/version/{version_id}/revoke, /api/v1/prompts/rule/{rule_id}/version/{version_id}/revoke` | `backend/app/api/prompts.py:1092` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/version-history, /api/v1/prompts/rule/{rule_id}/version-history` | `backend/app/api/prompts.py:1143` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/rule/{rule_id}/version/{version_id}/deletion-preview, /api/v1/prompts/rule/{rule_id}/version/{version_id}/deletion-preview` | `backend/app/api/prompts.py:1156` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `DELETE` | `/api/prompts/rule/{rule_id}/version/{version_id}, /api/v1/prompts/rule/{rule_id}/version/{version_id}` | `backend/app/api/prompts.py:1169` | `get_db, require_admin` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/version/{version_id}/archive, /api/v1/prompts/rule/{rule_id}/version/{version_id}/archive` | `backend/app/api/prompts.py:1190` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/version/{version_id}/restore, /api/v1/prompts/rule/{rule_id}/version/{version_id}/restore` | `backend/app/api/prompts.py:1212` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/versions/bulk-delete, /api/v1/prompts/rule/{rule_id}/versions/bulk-delete` | `backend/app/api/prompts.py:1231` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/resume-ai, /api/v1/prompts/rule/{rule_id}/resume-ai` | `backend/app/api/prompts.py:1251` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/rule/{rule_id}/suspend-ai, /api/v1/prompts/rule/{rule_id}/suspend-ai` | `backend/app/api/prompts.py:1277` | `get_db, require_admin` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/prompts/rule/{rule_id}/eligibility, /api/v1/prompts/rule/{rule_id}/eligibility` | `backend/app/api/prompts.py:1304` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/actual-prompt/incident/{incident_id}, /api/v1/prompts/actual-prompt/incident/{incident_id}` | `backend/app/api/prompts.py:1384` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/actual-prompt/incident/{incident_id}/executions, /api/v1/prompts/actual-prompt/incident/{incident_id}/executions` | `backend/app/api/prompts.py:1651` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/actual-prompt/rule/{rule_id}/captures, /api/v1/prompts/actual-prompt/rule/{rule_id}/captures` | `backend/app/api/prompts.py:1684` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/actual-prompt/rule/{rule_id}/preview, /api/v1/prompts/actual-prompt/rule/{rule_id}/preview` | `backend/app/api/prompts.py:1702` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/prompts/actual-prompt/incident/{incident_id}/export, /api/v1/prompts/actual-prompt/incident/{incident_id}/export` | `backend/app/api/prompts.py:1837` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `POST` | `/api/prompts/actual-prompt/retention/cleanup, /api/v1/prompts/actual-prompt/retention/cleanup` | `backend/app/api/prompts.py:1931` | `get_db, require_admin` | 0 | 1 | `ADMINISTRATIVE` |
| `GET` | `/api/learning/rules, /api/v1/learning/rules` | `backend/app/api/rule_learning.py:201` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/learning/rules/{rule_id}, /api/v1/learning/rules/{rule_id}` | `backend/app/api/rule_learning.py:257` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/learning/rules/{rule_id}/evaluate-accuracy, /api/v1/learning/rules/{rule_id}/evaluate-accuracy` | `backend/app/api/rule_learning.py:282` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/learning/rules/{rule_id}/history, /api/v1/learning/rules/{rule_id}/history` | `backend/app/api/rule_learning.py:304` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/learning/rules/{rule_id}/initialize, /api/v1/learning/rules/{rule_id}/initialize` | `backend/app/api/rule_learning.py:343` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/learning/rules/initialize-all, /api/v1/learning/rules/initialize-all` | `backend/app/api/rule_learning.py:362` | `get_db, require_admin` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/learning/rules/{rule_id}/suggest-prompt-improvement, /api/v1/learning/rules/{rule_id}/suggest-prompt-improvement` | `backend/app/api/rule_learning.py:379` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/learning/rules/{rule_id}/transition, /api/v1/learning/rules/{rule_id}/transition` | `backend/app/api/rule_learning.py:403` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/reviews/pending, /api/v1/reviews/pending` | `backend/app/api/rule_learning.py:451` | `get_db, get_current_active_user` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/reviews/{incident_id}/submit, /api/v1/reviews/{incident_id}/submit` | `backend/app/api/rule_learning.py:483` | `get_db, require_analyst` | 1 | 6 | `ACTIVELY_USED` |
| `POST` | `/api/reviews/{review_id}/adjudicate, /api/v1/reviews/{review_id}/adjudicate` | `backend/app/api/rule_learning.py:519` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/governance/promotion/requests, /api/v1/governance/promotion/requests` | `backend/app/api/rule_learning.py:550` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/governance/promotion/request, /api/v1/governance/promotion/request` | `backend/app/api/rule_learning.py:570` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/governance/promotion/decide, /api/v1/governance/promotion/decide` | `backend/app/api/rule_learning.py:623` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/governance/automation/policy/{rule_id}, /api/v1/governance/automation/policy/{rule_id}` | `backend/app/api/rule_learning.py:663` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `PUT` | `/api/governance/automation/policy/{rule_id}, /api/v1/governance/automation/policy/{rule_id}` | `backend/app/api/rule_learning.py:708` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/governance/automation/decide/{incident_id}, /api/v1/governance/automation/decide/{incident_id}` | `backend/app/api/rule_learning.py:742` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/governance/automation/audits, /api/v1/governance/automation/audits` | `backend/app/api/rule_learning.py:774` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `POST` | `/api/governance/automation/emergency-disable, /api/v1/governance/automation/emergency-disable` | `backend/app/api/rule_learning.py:814` | `get_db, get_current_active_user` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/rules` | `backend/app/api/rules.py:25` | `get_current_user, get_db` | 4 | 8 | `ACTIVELY_USED` |
| `GET` | `/api/rules/stats` | `backend/app/api/rules.py:234` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/rules/sync/fortisiem` | `backend/app/api/rules.py:296` | `get_db` | 0 | 1 | `ADMINISTRATIVE` |
| `GET` | `/api/rules/{identifier}` | `backend/app/api/rules.py:311` | `get_current_user, get_db` | 3 | 5 | `ACTIVELY_USED` |
| `GET` | `/api/rules/{identifier}/compiled-policy` | `backend/app/api/rules.py:352` | `get_current_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `GET` | `/api/rules/{identifier}/calibration-report` | `backend/app/api/rules.py:376` | `get_current_user, get_db` | 0 | 1 | `POTENTIALLY_UNUSED` |
| `POST` | `/api/rules/{identifier}/import-definition` | `backend/app/api/rules.py:403` | `get_db` | 2 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/system/servers/live` | `backend/app/api/system_monitor.py:14` | `get_current_user, get_db` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/system/servers/history` | `backend/app/api/system_monitor.py:24` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/telemetry/timeline` | `backend/app/api/telemetry.py:14` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/tokens/analytics` | `backend/app/api/tokens.py:14` | `get_current_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/users` | `backend/app/api/users.py:17` | `get_admin_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/users` | `backend/app/api/users.py:27` | `get_admin_user, get_db` | 1 | 1 | `ACTIVELY_USED` |
| `PATCH` | `/api/users/{user_id}` | `backend/app/api/users.py:71` | `get_admin_user, get_db` | 0 | 0 | `POTENTIALLY_UNUSED` |
| `POST` | `/api/verdict-intelligence/evaluate-incident-trust, /api/v1/verdict-intelligence/evaluate-incident-trust` | `backend/app/api/verdict_intelligence.py:63` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `POST` | `/api/verdict-intelligence/evaluate-incident, /api/v1/verdict-intelligence/evaluate-incident` | `backend/app/api/verdict_intelligence.py:63` | `get_db, require_analyst` | 1 | 3 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/incident/{incident_id}/trust, /api/v1/verdict-intelligence/incident/{incident_id}/trust` | `backend/app/api/verdict_intelligence.py:197` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
| `POST` | `/api/verdict-intelligence/dry-run/evaluate, /api/v1/verdict-intelligence/dry-run/evaluate` | `backend/app/api/verdict_intelligence.py:267` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/dry-run/runs, /api/v1/verdict-intelligence/dry-run/runs` | `backend/app/api/verdict_intelligence.py:391` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/dry-run/runs/{run_id}, /api/v1/verdict-intelligence/dry-run/runs/{run_id}` | `backend/app/api/verdict_intelligence.py:425` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/dry-run/compare, /api/v1/verdict-intelligence/dry-run/compare` | `backend/app/api/verdict_intelligence.py:496` | `get_db, require_analyst` | 1 | 0 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/metrics/summary, /api/v1/verdict-intelligence/metrics/summary` | `backend/app/api/verdict_intelligence.py:516` | `get_db, require_analyst` | 2 | 5 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/metrics, /api/v1/verdict-intelligence/metrics` | `backend/app/api/verdict_intelligence.py:516` | `get_db, require_analyst` | 2 | 6 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/metrics/rule-wise, /api/v1/verdict-intelligence/metrics/rule-wise` | `backend/app/api/verdict_intelligence.py:566` | `get_db, require_analyst` | 1 | 1 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/eligibility-report, /api/v1/verdict-intelligence/eligibility-report` | `backend/app/api/verdict_intelligence.py:647` | `get_db, get_current_active_user` | 2 | 2 | `ACTIVELY_USED` |
| `GET` | `/api/verdict-intelligence/integration-diagnostics, /api/v1/verdict-intelligence/integration-diagnostics` | `backend/app/api/verdict_intelligence.py:671` | `get_db, require_analyst` | 0 | 1 | `ADMINISTRATIVE` |
| `GET` | `/api/verdict-intelligence/export, /api/v1/verdict-intelligence/export` | `backend/app/api/verdict_intelligence.py:699` | `get_db, require_analyst` | 1 | 2 | `ACTIVELY_USED` |
