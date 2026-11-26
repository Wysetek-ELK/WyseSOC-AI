# 11 — Configuration & Environment Audit

*(No secrets or credential values are exposed; only configuration key names and code references are reported.)*

## 1. `backend/app/config.py` Settings Keys (59 Keys)

| Setting Key | Line | Prod Refs | Test Refs | Deploy Refs | Status |
|---|---:|---:|---:|---:|---|
| `Settings.APP_NAME` | L40 | 0 | 0 | 1 | `CONFIRMED_UNUSED` |
| `Settings.PROJECT_NAME` | L41 | 1 | 1 | 1 | `ACTIVE` |
| `Settings.VERSION` | L42 | 14 | 3 | 1 | `ACTIVE` |
| `Settings.API_V1_STR` | L43 | 2 | 0 | 0 | `ACTIVE` |
| `Settings.APP_ENV` | L44 | 15 | 12 | 1 | `ACTIVE` |
| `Settings.PLATFORM_OPERATING_MODE` | L45 | 1 | 1 | 1 | `ACTIVE` |
| `Settings.SECRET_KEY` | L48 | 3 | 8 | 1 | `ACTIVE` |
| `Settings.ALGORITHM` | L49 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` | L50 | 2 | 0 | 1 | `ACTIVE` |
| `Settings.COOKIE_NAME` | L53 | 2 | 0 | 0 | `ACTIVE` |
| `Settings.COOKIE_SECURE` | L54 | 2 | 0 | 1 | `ACTIVE` |
| `Settings.COOKIE_SAMESITE` | L55 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.DATABASE_URL` | L59 | 5 | 10 | 1 | `ACTIVE` |
| `Settings.SYNC_DATABASE_URL` | L63 | 2 | 9 | 1 | `ACTIVE` |
| `Settings.ALLOWED_ORIGINS` | L69 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.UPLOAD_MAX_FILE_SIZE` | L77 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.ZIP_MAX_UNCOMPRESSED_SIZE` | L78 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.ZIP_MAX_FILE_COUNT` | L79 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.ZIP_MAX_RATIO` | L80 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.FORTISIEM_HOST` | L83 | 3 | 5 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_USERNAME` | L84 | 3 | 3 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_PASSWORD` | L85 | 2 | 4 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_VERIFY_SSL` | L86 | 3 | 3 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_TIMEOUT` | L87 | 1 | 2 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_MOCK_FALLBACK` | L88 | 2 | 5 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_AUTO_POLL_ENABLED` | L89 | 5 | 1 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_POLL_INTERVAL_SECONDS` | L90 | 3 | 0 | 1 | `ACTIVE` |
| `Settings.FORTISIEM_AUTO_AI_VERDICT` | L91 | 4 | 0 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_BASE_URL` | L94 | 14 | 12 | 2 | `ACTIVE` |
| `Settings.LOCAL_LLM_MODEL_NAME` | L95 | 11 | 8 | 2 | `ACTIVE` |
| `Settings.LOCAL_LLM_API_KEY` | L96 | 7 | 2 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_TIMEOUT` | L97 | 5 | 4 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_CONTEXT_BUDGET` | L98 | 7 | 3 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_MAX_TOKENS` | L99 | 6 | 3 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_TARGET_INPUT_BUDGET` | L100 | 3 | 1 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN` | L101 | 4 | 2 | 0 | `ACTIVE` |
| `Settings.LOCAL_LLM_DISCOVERED_AT_UTC` | L102 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK` | L103 | 7 | 15 | 1 | `ACTIVE` |
| `Settings.LOCAL_LLM_PROVENANCE` | L104 | 1 | 3 | 0 | `ACTIVE` |
| `Settings.TEST_ENVIRONMENT_ID` | L105 | 1 | 1 | 0 | `ACTIVE` |
| `Settings.SERVER1_HOST` | L108 | 2 | 0 | 0 | `ACTIVE` |
| `Settings.SERVER1_OUTBOUND_IP` | L109 | 2 | 1 | 0 | `ACTIVE` |
| `Settings.DB_POOL_SIZE` | L112 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.DB_MAX_OVERFLOW` | L113 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.DB_POOL_TIMEOUT` | L114 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.DB_POOL_RECYCLE` | L115 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.AUTO_MIGRATE_ON_STARTUP` | L116 | 1 | 1 | 1 | `ACTIVE` |
| `Settings.REDIS_URL` | L119 | 4 | 1 | 1 | `ACTIVE` |
| `Settings.CELERY_BROKER_URL` | L120 | 4 | 1 | 1 | `ACTIVE` |
| `Settings.CELERY_RESULT_BACKEND` | L121 | 2 | 1 | 1 | `ACTIVE` |
| `Settings.USE_ASYNC_CELERY` | L122 | 5 | 7 | 1 | `ACTIVE` |
| `Settings.CELERY_TASK_TIMEOUT_SECONDS` | L123 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.LLM_MAX_CONCURRENT_REQUESTS` | L126 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.LLM_CIRCUIT_BREAKER_FAIL_THRESHOLD` | L127 | 1 | 1 | 1 | `ACTIVE` |
| `Settings.LLM_CIRCUIT_BREAKER_RECOVERY_TIME` | L128 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.QUEUE_BACKPRESSURE_LIMIT` | L129 | 1 | 0 | 1 | `ACTIVE` |
| `Settings.AUDIT_SIGNING_KEY` | L132 | 2 | 1 | 2 | `ACTIVE` |
| `Settings.PROMPT_CAPTURE_RETENTION_DAYS` | L135 | 1 | 0 | 0 | `ACTIVE` |
| `Settings.PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED` | L136 | 0 | 0 | 0 | `CONFIRMED_UNUSED` |

## 2. Unused Configuration Findings
1. `Settings.APP_NAME` (`backend/app/config.py:40`): 0 references in Python code or tests (`PROJECT_NAME` is used everywhere). `install_ubuntu.sh` only writes `NEXT_PUBLIC_APP_NAME` for Next.js. -> `CONFIRMED_UNUSED` (`REMOVE`).
2. `Settings.PROMPT_CAPTURE_AUTO_CLEANUP_ENABLED` (`backend/app/config.py:136`): 0 references across codebase, tests, and deployment templates. -> `CONFIRMED_UNUSED` (`REMOVE` after confirming no upcoming cron job expects it).
