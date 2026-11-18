# 01 — Existing System Audit (AIS 2.0 Single-Rule Lifecycle)

**Audit Timestamp (UTC):** `2026-11-18T14:52:00Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port`
**Canonical Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`
**Canonical Rule UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`
**Explicitly Excluded Sibling Rule:** `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`)
**Starting Baseline Commit:** `db27c7a` → **Verified Deployed Commit:** `800bc077d77f6b694f5b43d4b02fa7671b4ebf04`

---

## 1. Environment & Topology Audit

| Component | Host / Deployment | Verified Live State |
| :--- | :--- | :--- |
| **Server 1 (Verdictum Core)** | `172.26.41.240` (`verdictum-core-01`), non-Docker systemd in `/opt/wysesoc-ai` | `ai-verdict-backend.service` & `ai-verdict-frontend.service` active; nginx HTTP `:80`; CPU `0.5%`, RAM `12.6%` (`1.94/15.36 GB`), Disk `9.4%` |
| **PostgreSQL** | Local to Server 1 (PostgreSQL 16.4) | `healthy`, `connected: true`, query latency `2.19 ms` |
| **Redis / Celery** | `redis://127.0.0.1:6379/0` | `healthy`, `reachable: true`, `live_triage_queue_depth: 0` |
| **Server 2 (Verdictum Cortex)** | `13.204.214.64:8000` (`verdictum-cortex-01`), Local GPU vLLM | `ONLINE`, `Qwen/Qwen2.5-7B-Instruct-AWQ`, `OPENAI_COMPATIBLE`, `LIVE_PROVIDER`, circuit breaker `CLOSED`, `0/4` slots; **verified runtime `max_model_len = 4096`** (untouched; never restarted or replaced) |

---

## 2. Historical Incident Dataset Audit (Target Rule vs. Prior Report)

Prior historical notes referenced **31 canonical incidents**. Live Server 1 PostgreSQL audit confirmed the dataset has grown organically and now contains **69 real canonical historical incidents** bound to `40498741-ee6b-4a71-9101-0d6d3f77154c`:

| Dimension | Live Server 1 Observation |
| :--- | :--- |
| **Total Canonical Incidents** | **69** (0 fabricated, 0 duplicated) |
| **Tenant Breakdown** | `GDC_NOC`: **41** incidents; `Demo-SOC`: **28** incidents |
| **Telemetry Richness** | **32** incidents with attached FortiGate raw logs (up to 100 events each, e.g., `#176011`, `#167157`, `#175129`); **37** header-only incidents with `0` raw logs (e.g., `#176122`) |
| **Fixed Destination Port** | **69 / 69** on TCP port `443` (`destIpPort: 443`) |
| **Distinct Source IPs** | **69** distinct source IPs (internal RFC-1918 clients traversing FortiGate-120G) |
| **Verified Analyst Reviews** | **0** verified analyst ground-truth reviews (all 69 pending double-blind review) |
| **Eligible Empirical Samples** | **0 / 100** required minimum floor (`< 100` even if all 69 existing incidents were reviewed) |

---

## 3. Architectural & Codebase Defect Audit (Findings & Remediations)

Comprehensive inspection of AIS 2.0 backend services, APIs, database models, frontend `RuleLearningDashboard.tsx`, and test suites identified **12 concrete defects** blocking end-to-end single-rule completion. All 12 were repaired in place without introducing duplicate pipelines or redundant tables:

| # | Area | Audited Defect | Remediation Applied | Commit |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Model Output Schema** | `StructuredModelVerdict` & `validate_verdict_schema` rejected `INSUFFICIENT_EVIDENCE` and omitted `recommended_action`; `openai_compatible.py` lacked `rule_id` mismatch checks (`INVALID_RULE_REF`) and skipped `post_capture_cb(FAILED)` on schema rejection. | Added `recommended_action`, accepted `INSUFFICIENT_EVIDENCE`, enforced `INVALID_RULE_REF`, and invoked `post_capture_cb(FAILED)` on all validation failures in [base.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/base.py) and [openai_compatible.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/openai_compatible.py). | `ebffba0e` |
| 2 | **Policy Compiler Contract** | `MODEL_RESPONSE_SCHEMA` omitted `incident_id`, `rule_id`, `supporting_evidence`, `contradictory_evidence`, `recommended_action`, and `INSUFFICIENT_EVIDENCE`, and serialized a verbose JSON schema that consumed excessive context tokens. | Added all required fields and compacted Section 11 JSON wire contract in [policy_compiler_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_compiler_service.py). | `ebffba0e` → `4e709713` |
| 3 | **Evidence Contract Catalog** | 7 deterministic `scan.*` aggregate fields emitted by `EvidenceNormalizationService` were missing from `CANONICAL_FIELD_CATALOG`. | Registered all 7 `scan.*` fields (`scan.raw_events_count`, `scan.unique_destination_hosts`, `scan.destination_scope`, `scan.firewall_action_summary`, `scan.tcp_behavior_summary`, `scan.policy_and_service`, `scan.window_seconds`) in [evidence_requirement_mapper.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_requirement_mapper.py). | `ebffba0e` |
| 4 | **Feedback Learning Prompt Proposal** | `RuleLearningService.propose_prompt_improvement_draft` referenced nonexistent `rp.active_version` and passed raw kwargs instead of `PromptVersionCreate`. | Repaired attribute lookup and `PromptVersionCreate` instantiation in [rule_learning_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/rule_learning_service.py). | `ebffba0e` |
| 5 | **RAG Partition Isolation** | `VerifiedSemanticRetrievalService` did not explicitly reject `LOCKED_TEST` partition records from retrieval candidates. | Enforced strict `LOCKED_TEST` exclusion with leakage counters in [verified_semantic_retrieval_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verified_semantic_retrieval_service.py). | `ebffba0e` |
| 6 | **Automation Governor DB Overflow** | `"ROUTED_MANUAL_INSUFFICIENT_EVIDENCE"` (35 chars) overflowed PostgreSQL `VARCHAR(32)` `execution_status` column. | Shortened to `"ROUTED_INSUFFICIENT_EVIDENCE"` (28 chars) and normalized `policy_version_id`/`policy_version_number` aliases in [automation_governor.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/automation_governor.py). | `ebffba0e` |
| 7 | **Async Session Commit Ordering** | `rule_learning.py` transition/promotion endpoints triggered `MissingGreenlet` after rollback/refresh paths. | Fixed async commit/refresh ordering in [rule_learning.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/api/rule_learning.py). | `ebffba0e` |
| 8 | **Frontend Governance UI** | `RuleLearningDashboard.tsx` attempted direct 403 transition instead of navigating to Governance tab, showed `≥98%` instead of `≥99%` FP precision, and lacked Verified Accuracy, G1–G8 gate count, and Admin Enable/Disable FP Automation controls. | Updated [RuleLearningDashboard.tsx](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/learning/RuleLearningDashboard.tsx) cleanly without adding new pages. | `ebffba0e` |
| 9 | **Authoritative Rule Metadata Persistence** | `fortisiem_service.py` mutated `existing.parsed_metadata` in place, which SQLAlchemy ignored on PostgreSQL `JSON` columns. | Replaced with shallow copy `dict(existing.parsed_metadata or {})` in [fortisiem_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py). | `359b1382` |
| 10 | **G5 Policy Validator & Offline Simulation** | Draft FP indicators triggered false G5 warnings on RFC-1918 wording; `verdict_pipeline.py` blocked real-LLM simulation on `DRAFT` policies (`PREFLIGHT_GUARD`). | Corrected G5-compliant phrasing in [policy_generation_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_generation_service.py) and enabled real-LLM simulation for `is_simulation=True` in [verdict_pipeline.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_pipeline.py) while keeping `LIVE` mode strictly fail-closed. | `95a57e8a` |
| 11 | **Pure-Python BPE Tokenizer Overcount & `max_tokens` Cap** | `_count_tokens_pure_python` counted every single inter-word space as `+1` token and split 5–8 char words into `2` tokens (~1.7x overcount vs. Qwen2.5), blocking even header-only `#176122`; `OpenAICompatibleProvider` did not honor `reserved_comp_tokens` cap (`512`) under `4096` vLLM context. | Calibrated `_count_tokens_pure_python` in [tokenizer_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/tokenizer_service.py) (measured within `2.9%` of real Qwen2.5 API usage: `2,951` est vs `3,037` actual!) and wired `max_tokens_override=reserved_comp_tokens`. | `8502a24d` |
| 12 | **100-Event FortiGate Scan Compaction under 4,096 Context** | Real 100-event incidents (`#176011`: 1,155 canonical records) exceeded `avail_ev_budget` by ~121 tokens in `core_records`, causing compaction abort (`42,758` tokens). | Added deterministic scan-aggregate essential-core priority fit in [evidence_compaction_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_compaction_service.py) and exact header overhead margin in [token_budget_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/token_budget_service.py). | `800bc077` |

---

## 4. Sibling Rule Isolation Confirmation

Sibling rule `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`) was audited before and after every deployment:
- Policy remains strictly on its pre-existing **APPROVED v2** (`status: ELIGIBLE`, `reason_code: APPROVED_ACTIVE`, `ai_verdict_execution_status: ENABLED`).
- Zero policy edits, zero rule definition changes, and zero incident mutations occurred on the sibling rule.
