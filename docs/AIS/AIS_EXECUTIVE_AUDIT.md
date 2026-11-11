# Agent Intelligence Studio 2.0 — Executive Audit Report

**Audit Scope:** Strictly Read-Only Static Code, Configuration, Local DB, and Automated Test Audit  
**Codebase Commit:** `9616971` (HEAD; pre-existing formatting diff on `frontend/src/app/agent-intelligence-studio/page.tsx` untouched)  
**Target Reference Rule:** `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`, Archetype: `NETWORK_SCAN`)

---

## 1. Executive Summary & Current Operational Status

Agent Intelligence Studio 2.0 (AIS) and the AI Triage Workbench (`VerdictTriageAgent`) implement strong foundational guardrails (zero ground-truth data leakage, SHA-256 policy digests, structural gate validation G1–G7, and deterministic live claim grounding). However, **AIS 2.0 is currently NOT operationally complete for empirical validation (`G8`) or safe autonomous promotion**:

1. **AIS G8 Simulation runs a mock rule-blind simulator (`SIMULATED`), NOT the local Qwen LLM (`AIS-F02`):** `PolicySimulationService.evaluate_candidate_policy` (`policy_simulation_service.py:1084-1090`) never passes `provider_type` (defaulting to `"SIMULATED"`), and `_simulate_model_output()` (`:937-1045`) contains **zero `NETWORK_SCAN` heuristics**, guaranteeing `REQUIRES_ATTENTION (50%)` abstentions on port-scan incidents. Even when `OPENAI_COMPATIBLE` is invoked manually via `/api/verdict-intelligence/dry-run/evaluate`, G8 skips `EvidencePreflightValidator`, RAG, `TokenBudgetService`, `IndependentVerdictValidator`, and `RuleIntelligenceSnapshot` (`AIS-F09`).
2. **AIS Policy Approval bypasses G8 empirical requirements into Live Triage (`AIS-F03` — CRITICAL):** Policies with `G8 = INSUFFICIENT_DATA` (`0/15`, `autonomous_operation_eligible = False`) pass structural approval (`approval_eligible = True` because G8 returns `WARNING`), and `VerdictTriageAgent.evaluate_incident` (`ai_verdict_service.py:277`) immediately uses any `status == "APPROVED"` policy for live SOC triage without checking `autonomous_operation_eligible`.
3. **Why AIS scanned 52 incidents (`50 RULE_MISMATCH + 2 RULE_MATCHED`) vs Workbench's 33 (`AIS-F01`, `AIS-F07`):** AIS merges `matched_q` (`Incident.rule_id.in_(rule_ids)`, omitting `event_type`) with an **unfiltered global query** (`scanned_q`) fetching the 50 newest incidents across **all** rules (`2 + 50 = 52`), discarding the 50 unrelated alerts as `RULE_MISMATCH`. Meanwhile, AI Triage Workbench (`incident_service.py:100-111`) runs 6-column `ILIKE '%Heavy TCP Host Scan%'` text search, merging distinct rules (`PH_RULE_HEAVY_TCP_HOST_SCAN`, `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`, etc.) into 33 results.
4. **Ground Truth Qualification Loss (`AIS-F04`):** Ingestion (`ingestion_service.py:639`) and SIEM sync (`fortisiem_service.py:1145`) use raw substring `"ml" in comments.lower()` / `"ML" in comments` (false-positive on `normal`, `html`, `xml`, etc.), and FortiSIEM's `"Resolution set by Machine Learning"` comment prefix permanently overrides incidents with genuine human attribution (`e.g. cleared_user="Yash Mungekar"` on local DB incident `132501348`).
5. **G1–G8 Score Denominators & Export Schema (`AIS-F05`, `AIS-F06`):** `81/100` (`structural_raw = 81`) and `95.3%` (`81 / 85`) are exact under `PolicyQualityValidator`, while G1 (`max=20`) + G2 (`max=20`) double-count the 20-pt `detection_semantics` bucket (`sum(G1..G7 max_score) = 105`). Under v2.0.0 code, `81 / 95.3%` produces **`101/105`** across G1–G7 cards (`quality-export.test.mjs:24-116`), making **`91/105` algebraically impossible** alongside `95.3%`. `validation_status` exports as `null` because `qualityExport.ts:170` reads a field absent from `PolicyQualityAssessmentResponse`.

### Environment Verification Boundary
- **Confirmed Locally:** Static code inspection across frontend/backend, read-only SQLite DB (`backend/ai_verdict.db`: `4` rules, `26` incidents, `24` GT rows, `9` `SIMULATED` runs, `62` results; **`PH_RULE_HEAVY_TCP_HOST_SCAN` not present locally**), feature registry validation (`44` features / `19` modules), `15/15` frontend tests passing, and **`144/144` targeted backend unit tests passing** across 20 modules (executed cleanly without failing or skipped tests).
- **Unverified Remote Live State (`AIS-F13`):** The production PostgreSQL database (34 rules, 2,900+ incidents, the exact 2 matched `PH_RULE_HEAVY_TCP_HOST_SCAN` rows vs 31 other Workbench rows, why specifically 1 of 2 failed GT verification, live FortiSIEM REST responses, and live Server 2 Qwen inference) is **UNVERIFIED** from this workstation. Exact read-only SQL diagnostics are included in the domain reports.

---

## 2. Prioritized Findings Summary

| ID | Severity | Confidence | Category | Summary | Report Link |
| :-: | :-: | :-: | :--- | :--- | :--- |
| **`AIS-F03`** | **CRITICAL** | CONFIRMED | Governance / Live Triage | Live triage (`VerdictTriageAgent`) uses any `status="APPROVED"` policy regardless of `autonomous_operation_eligible=False` (`G8 = INSUFFICIENT_DATA`). | [AIS_G1_G8_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_G1_G8_AUDIT.md) |
| **`AIS-F01`** | **HIGH** | CONFIRMED | Retrieval / Funnel | AIS merges unfiltered global 50 (`scanned_q`) + `rule_id` filter (`matched_q`, no `event_type`), inflating `50+2=52` scanned and truncating >50-incident rules. | [AIS_INCIDENT_RETRIEVAL_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_INCIDENT_RETRIEVAL_AUDIT.md) |
| **`AIS-F02`** | **HIGH** | CONFIRMED | Simulation / LLM | `evaluate_candidate_policy` defaults to `SIMULATED`, never invoking local LLM; `_simulate_model_output` has zero `NETWORK_SCAN` checks (always abstains 50%). | [AIS_VERDICT_PIPELINE_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_VERDICT_PIPELINE_AUDIT.md) |
| **`AIS-F04`** | **HIGH** | CONFIRMED | Ground Truth | `"ml"` substring check false-triggers on ordinary text; ML comment prefix overrides real human `cleared_user`/`cleared_reason` (`ai_verdict.db` `132501348`, `132461358`). | [AIS_GROUND_TRUTH_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_GROUND_TRUTH_AUDIT.md) |
| **`AIS-F05`** | **HIGH** | CONFIRMED | Quality Gates Math | Structural breakdown denominator is `85` while G1–G7 card `max_score` sum is `105` (G1+G2 share 20 pts); `91/105` conflicts with `81 / 95.3%` (`101/105` in code). | [AIS_G1_G8_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_G1_G8_AUDIT.md) |
| **`AIS-F06`** | **MEDIUM** | CONFIRMED | Schema / Export | `validation_status: null` emitted by `qualityExport.ts:170` because `PolicyQualityAssessmentResponse` exposes `empirical_validation_status` instead. | [AIS_G1_G8_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_G1_G8_AUDIT.md) |
| **`AIS-F07`** | **MEDIUM** | CONFIRMED | Search vs Isolation | AI Triage Workbench 6-column `ILIKE` search merges `PH_RULE_HEAVY_TCP_HOST_SCAN` with sibling rules (`_ON_FIXED_PORT`), producing 33 vs 2 hits. | [AIS_RULE_MAPPING_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_RULE_MAPPING_AUDIT.md) |
| **`AIS-F08`** | **MEDIUM** | CONFIRMED | Rule Identity & Parser | Mixed `Rule.id` vs `Rule.rule_id` queries in `AgentPolicyEngine`/`RuleMaturityService`; `sync_all_rules_from_siem` uses latest 500 alerts; `RuleParser` drops `"Pattern Conditions"`. | [AIS_RULE_MAPPING_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_RULE_MAPPING_AUDIT.md) |
| **`AIS-F09`** | **MEDIUM** | CONFIRMED | Simulation Parity | G8 simulation omits `Preflight`, RAG, `TokenBudget`, `IndependentVerdictValidator`, `RuleIntelligenceSnapshot`, `Investigation.is_disputed`, and runs on excluded rows. | [AIS_VERDICT_PIPELINE_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_VERDICT_PIPELINE_AUDIT.md) |
| **`AIS-F10`** | **MEDIUM** | CONFIRMED | Normalization / Contracts | `EvidenceNormalizationService` omits `"Destination Port"`/`"dstPort"`/`"destinationPort"` (critical for `NETWORK_SCAN`); `EvidenceContractService` ignores Snapshot; typo at `registry:691`. | [AIS_VERDICT_PIPELINE_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_VERDICT_PIPELINE_AUDIT.md) |
| **`AIS-F11`** | **MEDIUM** | CONFIRMED | Parallel Engines | Legacy Dry-Run Lab (`dry_run_service.py` + `maturity_service.py`) operates separately from AIS G8 (`historical_evaluation_runs`). `verdict-intelligence` UI hardcodes `SIMULATED`. | [AIS_ACTUAL_ARCHITECTURE.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_ACTUAL_ARCHITECTURE.md) |
| **`AIS-F12`** | **MEDIUM** | CONFIRMED | Config / Ops Hygiene | Local `.env` enables mock fallbacks, omits `DATABASE_URL`/`SECRET_KEY`/`AUDIT_SIGNING_KEY`, has appended header lines; G8 runs synchronously on web workers. | [AIS_CONFIGURATION_GAPS.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_CONFIGURATION_GAPS.md) |
| **`AIS-F13`** | **INFO** | **UNVERIFIED** | Remote Production State | Exact 34-rule / 2,900+ incident PostgreSQL distribution, Workbench 33-row breakdown, and exact 2nd `PH_RULE_HEAVY_TCP_HOST_SCAN` exclusion cause require live SQL run. | [AIS_INCIDENT_RETRIEVAL_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_INCIDENT_RETRIEVAL_AUDIT.md) |

---

## 3. Deliverable Index (`/docs/AIS/`)

1. [AIS_EXECUTIVE_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_EXECUTIVE_AUDIT.md) — Executive summary, status, findings register
2. [AIS_ACTUAL_ARCHITECTURE.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_ACTUAL_ARCHITECTURE.md) — Actual implemented architecture & Mermaid diagram
3. [AIS_INCIDENT_RETRIEVAL_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_INCIDENT_RETRIEVAL_AUDIT.md) — `52` vs `2,900+` vs `33` reconciliation & live SQL
4. [AIS_RULE_MAPPING_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_RULE_MAPPING_AUDIT.md) — Canonical IDs, `event_type` gaps, rule distinction
5. [AIS_GROUND_TRUTH_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_GROUND_TRUTH_AUDIT.md) — Analyst resolution eligibility, ML bugs, local DB examples
6. [AIS_G1_G8_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_G1_G8_AUDIT.md) — Gate specs, `81`/`95.3%`/`101` vs `91`/`null` proofs
7. [AIS_VERDICT_PIPELINE_AUDIT.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_VERDICT_PIPELINE_AUDIT.md) — 12-step simulation vs live triage audit
8. [AIS_CONFIGURATION_GAPS.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_CONFIGURATION_GAPS.md) — Dependency readiness table (scrubbed of secrets/IPs)
9. [AIS_REMEDIATION_PLAN.md](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_REMEDIATION_PLAN.md) — P0–P3 implementation plan & acceptance criteria
10. [AIS_AUDIT_EVIDENCE.json](file:///C:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AIS/AIS_AUDIT_EVIDENCE.json) — Machine-readable evidence, checks & SQL

