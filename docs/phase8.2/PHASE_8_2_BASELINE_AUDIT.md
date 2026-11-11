# Phase 8.2 — Stage A Baseline Repository & Environment Audit

**Evidence Source:** `docs/phase8.2/evidence/baseline/stage_a_baseline_reconciliation.json`  
**Git Commit:** `cefe4ad031c873e9d7f97c01d1aba6f5486dbaa1`  
**Branch:** `feat/verdict-intelligence-validation-v2.1`

## 1. Baseline Reconciliation Findings

- **Architecture Verified:** Agent Intelligence Studio 2.1 + Audit Remediation v2.2.1 + Phase 8.1 Hardening (`P8.1-DEF-001` through `P8.1-DEF-006` confirmed present in source before Phase 8.2 edits).
- **Phase 8 / Phase 8.1 Artifact Integrity:** Preserved `docs/phase8/` and `docs/phase8.1/` 100% unmodified (`git diff docs/phase8/ docs/phase8.1/` empty).
- **Historical Registry Baseline:** `docs/feature_registry.json` recorded 37 features across 19 modules, 67/67 implementation criteria (`100.0%`), and 61/67 verified criteria (`91.0%`), leaving 6 external hardware/live-integration criteria unverified (`LLM-01-C2`, `QGS-02-C3`, `MON-02-C2`, `FSI-01-C3`, `DBM-01-C2`, `WRK-02-C2`).

## 2. Sanitized `.env` & Local Tooling Audit

- **Sanitized Runtime Configuration (`backend/.env`):**
  - `LOCAL_LLM_BASE_URL`: `"http://192.0.2.50:8000/v1"` (RFC-5737 TEST-NET-1 placeholder)
  - `LOCAL_LLM_MODEL_NAME`: `"Qwen/Qwen2.5-7B-Instruct-AWQ"`
  - `LOCAL_LLM_ALLOW_MOCK_FALLBACK`: `"true"` (`LOCAL_LLM_API_KEY` redacted len=5)
  - `FORTISIEM_HOST`: `"https://<CONFIGURED_FORTISIEM_HOST>"` (`FORTISIEM_VERIFY_SSL="false"`, `FORTISIEM_MOCK_FALLBACK="true"`, `FORTISIEM_AUTO_POLL_ENABLED="false"`, `FORTISIEM_AUTO_AI_VERDICT="true"`)
- **Installed Local Binaries (`shutil.which`):**
  - Present (`true`): `celery`, `uvicorn`
  - Missing (`false`): `psql`, `pg_ctl`, `postgres`, `redis-server`, `memurai`, `nginx`, `vllm`

## 3. Baseline Discrepancies Triggering Phase 8.2 Remediation

Independent code and screenshot inspection exposed seven concrete gaps beyond Phase 8.1:
1. `PH_RULE_DEBUG_FUNNEL` (`INC-DEBUG-*`) 0-event synthetic fixtures lacked explicit pre-exclusion (`P8.2-DEF-001`).
2. Near-duplicate Prisma SASE batch closures inflated historical cluster counts (`P8.2-DEF-002`).
3. Zero-decisive runs could persist/display `balanced_accuracy: 100%` without denominator checks (`P8.2-DEF-003` / `P8.2-DEF-004`).
4. `POST /api/prompts/rule/{rule_id}/validate-quality` permitted any active user (including `Read-Only Viewer`), causing 403/mutation ambiguity (`P8.2-DEF-005`).
5. Unauthenticated `GET /api/health` leaked raw `LOCAL_LLM_BASE_URL` while Inference Control hardcoded `HEALTHY` and Workbench showed `GPU Live` when S2 was offline (`P8.2-DEF-006`).
6. `VerdictTriageAgent.is_local_llm_available()` cached `_is_local_llm_online` without tracking `_last_probed_base_url` changes.
7. `EvidenceNormalizationService` computed `event.timestamp` as `observed_at` metadata but never emitted a canonical `event.timestamp` record despite archetype contracts requiring it (`P8.2-DEF-007`).
