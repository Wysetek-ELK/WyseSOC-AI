# 08 — Existing AIS 2.0 UI & Workflow Validation

**Design Constraint:** Zero new UI pages, zero new learning engines, and zero architectural rebuilds were introduced in V8.1. All V8.1 diagnostics, prompt captures, output integrity statuses, evidence compaction counts, and readiness gates integrate cleanly into the existing AIS 2.0 UI surfaces verified on Server 1 (`http://172.26.41.240`).

---

## 1. Verification Matrix of All 10 Existing AIS 2.0 UI Capabilities

| # | UI Capability | Existing Surface / Component | Backend Data Source Verified Live | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Actual LLM Prompt Inspector** | `SimulationLabPanel.tsx` / Prompt Capture Drawer | `GET /api/prompt-captures/{capture_id}` (`1289a418`, `27ca0371`, `5661b6ec`, `ccb491fa`, `e3b6d3b1`, `865c78c0`; `hash_match = true`, exact `request_sha256` & raw model JSON) | **VERIFIED** |
| **2** | **Token & Context Diagnostics** | Prompt Capture & Simulation Run Telemetry | `token_usage_source = API_USAGE`, `prompt_tokens` (`3,110–3,183`), `completion_tokens` (`262–561`), `max_tokens_sent = 768`, `total_tokens` (`3,372–3,724`) | **VERIFIED** |
| **3** | **Output Validation Status** | Per-Incident Simulation Row & Validation Badges | `validation_status` (`VALIDATED`, `ABSTAINED`, `REJECTED`, `TRUNCATED_OUTPUT`, `INVALID_MODEL_OUTPUT`) + `validation_reason_codes` (verified live: `EVIDENCE_CONTRACT_UNVERIFIED`, `EVIDENCE_VALUE_MISMATCH`) | **VERIFIED** |
| **4** | **Evidence Preservation Visibility** | Capture Evidence Packet & Canonical Count | `kept_fields` (`14/14` on all 5 rich runs), `canonical_evidence_count` (`10–1,156`), `evidence_completeness = 1.0`, `grounding_ratio` (`1.0` / `0.667`) | **VERIFIED** |
| **5** | **V7 vs V8 / V8.1 Controlled Comparison** | `SimulationLabPanel.tsx` (`incident_ids` cohort + run selector) | Same 6-incident cohort compared across `ca113d0a` (V7), `9e2ebd30` (V8), and `a95cd268` (V8.1) with identical `execution_provenance = REAL_LOCAL_LLM` | **VERIFIED** |
| **6** | **Double-Blind Analyst Review Workbench** | `RuleLearningWorkspace.tsx` — Pending Reviews Queue | `GET /api/learning/pending-reviews` returns `69` items with `blind_mode_active = true`, `analyst_verdict = null`, and zero AI verdict exposure before submission | **VERIFIED** |
| **7** | **Verified Learning Counts** | `RuleLearningWorkspace.tsx` — Rule Maturity Strip | `total_analyst_reviews = 0`, `eligible_evaluations = 0/100`, `verified_tp_count = 0/25`, `verified_fp_count = 0/50`, `pending_reviews = 69` | **VERIFIED** |
| **8** | **Confusion Matrix** | `RuleLearningWorkspace.tsx` — Learning Metrics Panel | `agreed_tp=0`, `agreed_fp=0`, `ai_false_alarm=0`, `critical_missed_tp=0`, `abstained_resolved=0`, `disputed=0` | **VERIFIED** |
| **9** | **Confidence vs Empirical Accuracy Separation** | `RuleLearningWorkspace.tsx` & `SimulationLabPanel.tsx` | Raw model confidence (`0.9`/`0.95`) strictly isolated to per-incident LLM trace; empirical metrics (`empirical_accuracy`, `fp_precision`, `wilson_lower_bound`, `tp_recall`) explicitly displayed as `NOT MEASURABLE` (`null`) — never conflated with model confidence | **VERIFIED** |
| **10** | **G1–G8 Quality Gates, Blockers & Maturity Strip** | `PromptStudioWorkspace.tsx` & `RuleLearningWorkspace.tsx` | Displays `7/8` gates passed (`G1–G7 PASS`, `G8 PENDING`), `is_production_eligible = false`, all 8 exact `eligibility_reasons`, active `v7 APPROVED`, candidate `v8 DRAFT`, and `automation_policy.is_enabled = false` | **VERIFIED** |

---

## 2. Frontend Build & Zero-Regression Check

- **Frontend Code Changes in V8.1:** **None required** — the V8 UI maturity strip and `NOT MEASURABLE` accuracy rendering (built and deployed on Server 1 in commit `ee9b82108` / `10021a3ff` with Next.js production build `PASS`) already consume all V8.1 backend fields (`validation_status`, `validation_reason_codes`, `token_usage`, `kept_fields`, `readiness_governance`, and `accuracy_status = "NOT_MEASURABLE"`).
- **Live Server 1 Frontend & API Proxy:** Both `ai-verdict-frontend.service` and `ai-verdict-backend.service` remain `active (running)` behind nginx `:80` (`GET /api/health` → `200 OK`, `status = healthy`).
