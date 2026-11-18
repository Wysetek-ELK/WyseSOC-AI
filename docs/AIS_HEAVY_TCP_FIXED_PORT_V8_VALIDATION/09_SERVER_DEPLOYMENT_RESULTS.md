# 09 — Server 1 Deployment & Regression Test Results

**Target Host:** Server 1 (`172.26.41.240`, `verdictum-core-01`, `/opt/wysesoc-ai`, non-Docker systemd)
**Git Repository & Branch:** `https://github.com/Wysetek-ELK/WyseSOC-AI.git` (`feature/phase3-compact-ui`)
**Live Verified Commit SHA on Server 1:** **`10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c`**
**Server 2 Local GPU LLM (`13.204.214.64:8000`):** **UNTOUCHED** (`Qwen/Qwen2.5-7B-Instruct-AWQ`, `ONLINE` throughout)

---

## 1. UPLA Governance & Deployment Timeline (V8 Phase)

| Step | Commit SHA | UPLA Execution ID | Outcome | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **V8 Feature Commit (12 files)** | `ee9b82108b56a5b970e9e83c4e0165af946dc017` | `upla-20261118-151625-9cfa67` | Gate 1 `SYNCED_AND_VERIFIED`; deployed on Server 1 by Administrator after Windows OpenSSH transport hang on port 22 | `npm run build` **PASSED** (`2.4s`, `32/32` pages); backend pytest returned `22 passed, 1 failed` (`test_09` 4096-token budget margin) |
| **V8 Compaction Fix (2 files)** | **`10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c`** | `upla-20261118-160649-86fcd5` | Gate 1 `SYNCED_AND_VERIFIED`; deployed & verified on Server 1 by Administrator | Backend pytest: **`23 passed in 5.78s`** (`0` failures); `ai-verdict-backend.service` restarted; live `/api/health` verified `healthy` |

---

## 2. Automated Regression Suite Verification on Server 1 (`10021a3f`)

### Backend Pytest (`23 passed in 5.78s`)
Command executed on Server 1 (`/opt/wysesoc-ai/backend`):
```bash
./venv/bin/pytest tests/test_ais_heavy_tcp_e2e.py tests/test_rule_learning_platform.py tests/test_api_422_remediation.py -q
```
- `tests/test_ais_heavy_tcp_e2e.py` (**10/10 PASSED**, including new `test_10_v8_evidence_alignment_fortigate_contract_and_label_reversal` and strengthened `test_09_high_cardinality_scan_token_budget_fits_4096_context`)
- `tests/test_rule_learning_platform.py` (**ALL PASSED**)
- `tests/test_api_422_remediation.py` (**ALL PASSED**)

### Frontend Next.js Production Build (`PASS`)
Command executed on Server 1 (`/opt/wysesoc-ai/frontend`):
```bash
npm run build
```
- Next.js `16.4.5` (Turbopack): Compiled in `719ms`, TypeScript verified in `2.4s`, `32/32` static pages generated, `0` errors.

---

## 3. Live Post-Deploy API & Infrastructure Health Proof (`GET http://172.26.41.240/api/health`)

- **Application (`Verdictum Core`):** `healthy` (`environment: production`, `version: 1.0.0`)
- **PostgreSQL 16.4:** `healthy` (`connected: true`)
- **Redis / Celery:** `healthy` (`reachable: true`)
- **Server 2 Local LLM (`Verdictum Cortex`):** `healthy` (`ONLINE`, `Qwen/Qwen2.5-7B-Instruct-AWQ`, `OPENAI_COMPATIBLE`, `LIVE_PROVIDER`)
- **Live Learning API Verification (`GET /api/learning/rules/40498741-...`):** Confirmed `accuracy_status: "NOT_MEASURABLE"`, `approved_prompt_version_number: 7`, `candidate_draft_version_number: 8 (DRAFT)`, `is_production_eligible: false`.
- **Live Real LLM Benchmark Regression (12 Real GPU Calls):** `6/6` V7 runs (`ca113d0a`) + `6/6` V8 runs (`9e2ebd30`) completed with `12/12` `VERIFIED` cryptographic SHA-256 captures and `0` server errors.
- **Sibling Rule Non-Regression:** `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`) confirmed untouched (`APPROVED v2`, `ELIGIBLE`).
