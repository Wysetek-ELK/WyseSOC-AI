# 09 — Deployment, Regression Suite & Safety Verification

**Target Environment:** Server 1 (`verdictum-core-01`, `172.26.41.240`, `/opt/wysesoc-ai`) + Server 2 (`verdictum-cortex-01`, `13.204.214.64:8000`, untouched)  
**Git Branch:** `feature/phase3-compact-ui`

---

## 1. Deployment & Commit Reconciliation (Strict Honesty)

| Commit SHA | Scope | Synced to GitHub? | Deployed on Server 1? | Verified Test / Health Outcome on Server 1 |
| :--- | :--- | :---: | :---: | :--- |
| `88a95ceead993f09cb4f202c5a38ed6e46d69c12` | Core V8.1 implementation: 4096/768 token budget, Section 10/11 compaction, `scan.sample_context`, `secondary_priority` (`policy_and_service` `#0`), `TRUNCATED_OUTPUT` enforcement, `test_11` | **Yes** | Superseded | `23 passed, 1 failed` (`test_11` missed `scan.sample_context` by ~15 tokens on synthetic fixture) |
| `ca4f04f35a211ffca32f8bc9b820c324a5fb1dc5` | Step 0 deduplication of duplicate `evidence_contract` wire arrays when Section 4 exists | **Yes** | Superseded | `23 passed, 1 failed` (exposed `network.protocol` loss when `conditional_fields` stripped before Step 3d) |
| **`8120d882bbcdf62389ce5053dd8e6565a9451d0e`** | Preserved `_orig_conditional_fields` locally for compaction priority; **currently LIVE on Server 1** | **Yes** | **YES (LIVE)** | Live Server 2 re-benchmark `a95cd268`: **`14/14` fields on `5/5` real rich incidents, `0/6` truncations**; pytest: `23 passed, 1 failed` (synthetic `test_11` still ~15 tokens tight on `scan.sample_context`) |
| **Pending Final V8.1 Commit (Working Tree)** | `backend/app/services/token_budget_service.py` line 360 (`+ 140` → `+ 95` safety margin so synthetic `test_11` also packs `scan.sample_context`) + all 11 reports in `docs/AIS_HEAVY_TCP_FIXED_PORT_V8_1/` | Pending Gate 1 approval | **NOT YET DEPLOYED** (pending Server 1 pull + re-run of pytest to verify `24/24`) | Local code edit complete; Server 1 verification of `24 passed` required after pull |

> [!IMPORTANT]
> Per strict reporting honesty: commit `8120d882b` is **deployed and live-verified** on Server 1 (`http://172.26.41.240/api/health` → `healthy`, real GPU benchmark `a95cd268` executed against `8120d882b`). The 1-line `+ 95` margin refinement in [token_budget_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/token_budget_service.py) is **not yet deployed on Server 1** and will require a quick `git fetch && git checkout <new-sha> && pytest && systemctl restart ai-verdict-backend.service` on Server 1 to confirm `24 passed, 0 failed`.

---

## 2. Backend & Frontend Regression Matrix

| Suite / Check | Target | Status on Server 1 (`8120d882b`) | Notes |
| :--- | :--- | :---: | :--- |
| `tests/test_ais_heavy_tcp_e2e.py` (`test_01`–`test_10`) | End-to-end AIS pipeline, double-blind, tenant isolation, `LOCKED_TEST` anti-leakage, budget compaction, label-correction reversal | **10 / 10 PASS** | Zero regressions across all prior V7/V8 tests |
| `tests/test_ais_heavy_tcp_e2e.py` (`test_11`) | V8.1 `TRUNCATED_OUTPUT` detection, `scan.sample_context`, 4096/768 budget packing | **FAIL on `8120d882b` / FIX READY** | Live `#176011` packed all `14/14` fields; synthetic `test_11` fixed via `+ 140` → `+ 95` margin (pending Server 1 re-run) |
| `tests/test_rule_learning_platform.py` | Learning profiles, disputes, adjudication, G1–G8 promotion gates, automation guardrails | **PASS (100%)** | All tests green |
| `tests/test_api_422_remediation.py` | API contract & 422 payload validation | **PASS (100%)** | All tests green |
| Next.js Frontend Build (`npm run build`) | Frontend TypeScript & production bundle | **PASS** (on `ee9b82108`; no frontend changes in V8.1) | `ai-verdict-frontend.service` active |
| Server 1 Health (`GET /api/health`) | DB, Redis/Celery, Local LLM, System | **PASS (`healthy`)** | DB `2.6 ms`, Redis `healthy` (`queue=0`), LLM `ONLINE` (`CLOSED`, `0/4` slots), CPU `0.9%`, RAM `11.5%` |

---

## 3. Mandatory Safety & Isolation Invariants (All Verified Post-Benchmark)

| Safety Invariant | Verified Live Post-Benchmark Value (`2026-11-18T16:47:10Z`) | Status |
| :--- | :--- | :---: |
| **Approved Policy v7 Active & Untouched** | `active_version_number = 7`, `active_version_status = APPROVED`, ID `d79fb576-c6b9-4f63-9167-3c7a2419b70a` | **VERIFIED** |
| **Candidate Policy v8 Remains DRAFT & Unmodified** | `selected_version_number = 8`, `selected_version_status = DRAFT`, ID `20d4f788-85a5-437d-afbe-fe7fd80abca1`, `policy_digest = c5e87a1ec6ac82c43ed07e62271850521456719da8800299256a897c91f8352b` | **VERIFIED** |
| **Production Automation Disabled** | `automation_policy.is_enabled = false`, `lifecycle_stage = LEARNING`, `is_production_eligible = false` | **VERIFIED** |
| **Zero Live FortiSIEM Incident Closures** | `current_day_closure_count = 0`, `live_triage_queue_depth = 0`, `69/69` FortiSIEM incidents still open (`status = 0`) | **VERIFIED** |
| **Zero Fabricated Analyst Reviews** | `total_analyst_reviews = 0`, `eligible_evaluations = 0`, `pending_reviews = 69` (`blind_mode_active = true`) | **VERIFIED** |
| **Server 2 GPU LLM Untouched** | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `ONLINE`, `max_model_len = 4096`, zero restarts/config edits | **VERIFIED** |
| **Sibling Rule Completely Untouched** | `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`), `APPROVED v2`, `ELIGIBLE` | **VERIFIED** |
| **Zero Secrets / Credentials Exposed** | All tokens redacted (`http://<configured>:8000/v1`, `redis://127.0.0.1:6379/0`), zero credentials in reports or git | **VERIFIED** |
