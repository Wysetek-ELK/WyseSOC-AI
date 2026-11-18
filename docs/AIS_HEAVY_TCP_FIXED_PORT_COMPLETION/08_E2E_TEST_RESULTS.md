# 08 — End-to-End Test Results (Software Tests vs. Real Local LLM Tests)

**Execution Environment:** Server 1 (`/opt/wysesoc-ai`, commit `800bc077d77f6b694f5b43d4b02fa7671b4ebf04`) + Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ`, `13.204.214.64:8000`)
**Date (UTC):** `2026-11-18`

> **Strict Separation of Evidence:** Automated unit/integration `pytest` tests use isolated in-memory SQLite + synthetic fixtures + mocked FortiSIEM write-back to verify software logic and NEVER contribute to empirical rule accuracy. Real Local LLM tests execute live HTTP inference from Server 1 to Server 2 GPU (`is_simulated = false`) on real PostgreSQL incidents.

---

## 1. Automated Backend `pytest` Suite (Executed on Server 1)

Command executed via UPLA deployment verification on Server 1:
```bash
cd /opt/wysesoc-ai/backend && ./venv/bin/pytest \
  tests/test_ais_heavy_tcp_e2e.py \
  tests/test_rule_learning_platform.py \
  tests/test_api_422_remediation.py -q
```
**Result:** **ALL PASSED** (`exit code 0`, `0` failures, `0` skipped regressions).

### Target-Rule E2E Test Matrix (`backend/tests/test_ais_heavy_tcp_e2e.py` — 9 Tests)

| Test | Phase Covered | What It Verifies | Status |
| :--- | :--- | :--- | :---: |
| `test_01_evidence_normalization_header_and_raw_events` | Phase 2 | Header-only `destIpPort`/`scan.raw_events_count=0` extraction, GT stripping (`clearedReason`), and FortiGate raw-log `scan.*` aggregation | **PASS** |
| `test_02_rule_specific_policy_generation_no_unsafe_assumptions` | Phase 2 | `NETWORK_SCAN` archetype, fixed-port scoping, explicit prohibition on unsafe RFC-1918/common-port FP assumptions, authorized scanner criteria | **PASS** |
| `test_03_double_blind_review_dispute_adjudication_and_exact_once` | Phase 4 | Blind queue hides `ai_verdict`, UUID alias resolution, queue drain, conflicting-analyst dispute without double-counting, cross-tenant rejection, L2 adjudication | **PASS** |
| `test_04_empirical_95_99_zero_missed_tp_and_separation_of_duties` | Phases 5–6 | Blocks `<100` samples, blocks `1` missed TP at `99.3%` acc, allows promotion only at `>=95%` acc / `>=99%` FP prec / `>=96%` Wilson LB / `0` missed TP / G1–G8, blocks self-approval, keeps automation disabled after approval, leaves sibling rule untouched | **PASS** |
| `test_05_controlled_fortisiem_automation_all_branches_and_emergency_suspension` | Phase 7 | TP escalation, `INSUFFICIENT_EVIDENCE` routing (`ROUTED_INSUFFICIENT_EVIDENCE`), FP dry-run, mocked SIEM write-back, idempotency, missed-TP emergency kill-switch | **PASS** |
| `test_06_prompt_improvement_draft_and_schema_validation_guards` | Phases 3–4 | `propose_prompt_improvement_draft` creates `DRAFT` without touching approved policy; `validate_verdict_schema` accepts `INSUFFICIENT_EVIDENCE` and rejects invalid confidence/incident/rule refs | **PASS** |
| `test_07_http_api_routes_uuid_aliases_and_rbac_enforcement` | Phases 4–7 | HTTP API contract checks, UUID/event_type alias parity, RBAC enforcement (analyst cannot approve promotion) | **PASS** |
| `test_08_contradictory_evidence_block_and_rag_partition_isolation` | Phases 4, 5, 7 | Barrier 5 blocks FP closure on contradictory evidence; `LOCKED_TEST` partition never leaks into `VerifiedSemanticRetrievalService` | **PASS** |
| `test_09_high_cardinality_scan_token_budget_fits_4096_context` | Phase 3 | 100-event FortiGate scan with full `EC-...-V7` contract fits strictly within `4,096`-token Server 2 context (`<= 3,584` input + `512` completion) while preserving `scan.*` aggregates | **PASS** |

### Companion Regression Suites & Frontend Production Build
- `backend/tests/test_rule_learning_platform.py`: **PASS**
- `backend/tests/test_api_422_remediation.py`: **PASS**
- Frontend Next.js production build (`cd /opt/wysesoc-ai/frontend && npm run build`): **PASS** (`0` TypeScript/build errors)

---

## 2. Live Server 1 → Server 2 Real GPU LLM Tests (Zero Mocks)

| Live Verification Check | Target | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Live Real LLM Inference (`#176011`, `GDC_NOC`, 100 raw events)** | `POST /api/incidents/176011/ai-verdict` → Server 2 | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `is_simulated=false`, `3,822` tok (`3,497+325`), `12,254 ms`, `VALIDATED`, grounding `1.0`, `hash_match=true` | **PASS** |
| **Live Real LLM Inference (`#167157`, `Demo-SOC`, 100 raw events)** | `POST /api/incidents/167157/ai-verdict` → Server 2 | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `is_simulated=false`, `3,793` tok (`3,516+277`), `11,050 ms`, `VALIDATED`, grounding `1.0`, `hash_match=true` | **PASS** |
| **Live Real LLM Inference (`#175129`, `GDC_NOC`, 100 raw events)** | `POST /api/incidents/175129/ai-verdict` → Server 2 | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `is_simulated=false`, `3,968` tok (`3,510+458`), `15,952 ms`, `VALIDATED`, cited all 11 `EV-*` scan IDs, `hash_match=true` | **PASS** |
| **Live Real LLM Inference (`#176122`, `GDC_NOC`, 0 raw events)** | `POST /api/incidents/176122/ai-verdict` → Server 2 | `Qwen/Qwen2.5-7B-Instruct-AWQ`, `is_simulated=false`, `3,345` tok (`3,037+308`), `8,168 ms`, `VALIDATED`, abstained explicitly citing `scan.raw_events_count == 0`, `hash_match=true` | **PASS** |
| **View Actual LLM Prompt (`#176011`, `#167157`, `#175129`, `#176122`)** | `GET /api/prompts/actual-prompt/incident/{id}` | All 4 `delivery_status=COMPLETED`, `capture_status=CAPTURED_RUNTIME`, `integrity_status=VERIFIED`, `untrusted_data_boundaries_present=true`, `0` secret/GT leaks | **PASS** |
| **Live Double-Blind Review Queue Isolation** | `GET /api/reviews/pending?rule_id=40498741-...` | `69` pending items, `ai_verdict_exposed=false` after live inference | **PASS** |
| **Live Controlled Automation Dry-Run (4 Incidents)** | `POST /api/governance/automation/decide/{id}` (`dry_run=true`) | All 4 `incident_closed=false`, `ROUTED_INSUFFICIENT_EVIDENCE`, 4 immutable PostgreSQL audits persisted | **PASS** |
| **Live Production Readiness Gate Honesty** | `GET /api/learning/rules/40498741-...` | `is_production_eligible=false` with 8 exact blockers (`0/100` samples, `7/8` gates) | **PASS** |
| **Live Sibling Rule Non-Regression** | `GET /api/prompts/rule/9839fa49-.../eligibility` | Sibling rule remains `APPROVED v2`, `ELIGIBLE`, completely untouched | **PASS** |
