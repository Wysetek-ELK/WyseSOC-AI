# AIS 3.1 — Workstream 7: Active Policy & Exact Wire Prompt Freeze

**Machine-Readable Evidence:** [POLICY_FREEZE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/POLICY_FREEZE_MANIFEST.json)

---

## 1. Discovered Policy State Across the 30 Holdout Rules

Audit of Server 1 rule registry (`rule_details` across all 30 holdout FortiSIEM rules) showed:

| Policy State Category | Rules | Incidents | Observation |
|---|---:|---:|---|
| `APPROVED` active & selected | 16 | — | Legacy v1 approved templates from prior AIS phases |
| `APPROVED` active + newer `DRAFT` selected | 4 | — | Newer draft unapproved; active remains v1 |
| **Total Rules with `APPROVED` Policy** | **20** | **81** | Mixed readiness/templates |
| **Rules with `DRAFT v1` Only (No `APPROVED` Policy)** | **10** | **19** | `AI Verdict Execution: BLOCKED` under strict Mode B |
| **Total Holdout Rules** | **30** | **100** | — |

---

## 2. Frozen Benchmark Policy Specification (Pre-Execution Freeze)

Because **10/30** rules have no `APPROVED` policy version and **no prompts were tuned against the 100 holdout labels**, AIS 3.1 freezes a single deterministic, neutral, rule-definition-grounded policy configuration uniformly across all 100 holdout incidents prior to running GPU inference:

| Configuration Parameter | Frozen Value |
|---|---|
| **Policy Mode** | `FROZEN_NEUTRAL_MODE_A_WITH_COMPLETE_RULE_SPEC_AND_EVIDENCE_INTELLIGENCE` |
| **Neutral Prompt Version** | `NEUTRAL_SOC_BASELINE_V2` + `_MODE_A_SCHEMA_SUFFIX` |
| **Neutral System Prompt SHA-256** | `3b09dd249e3fad38ac795f88e957b1b305bd04025cc8fb6cc4605584b461fb6c` |
| **Prompt Builder** | `AIS31BenchmarkService._prepare_incident_wire_payload` + `ModelTokenizerService.render_wire_user_message` |
| **Rule Definition Builder** | `RuleDefinitionBuilder.build_complete_rule_spec` |
| **Evidence Enrichment** | `EvidenceIntelligenceEngine.enrich_incident_evidence` |
| **Validator Version** | `IndependentVerdictValidator` + `ModelClaimExtractor` (unmodified) |
| **Temperature / Top-P** | `0.0` / `1.0` |
| **Qwen3 Thinking Mode** | `enable_thinking: false` (`chat_template_kwargs`) |
| **Context Limit / Completion Reserve** | `8192` total / `768` reserved completion / `7424` input ceiling |
| **RAG & Agent Memory** | Strictly excluded (`rag_excluded=True`, `memory_excluded=True`) |
| **Mock Fallback** | Strictly disabled (`allow_mock_fallback=False`) |

---

## 3. Exact Wire Prompt Audit & RBAC Protection

- **Verbatim Wire Persistence:** `AIS31BenchmarkResult` stores `wire_system_prompt`, `wire_user_content`, `wire_prompt_sha256`, `wire_token_audit_json`, `raw_response_text`, and `raw_vllm_envelope_json` for every executed incident — capturing the exact payload sent on the wire rather than a post-hoc reconstruction.
- **RBAC Protection:** `GET /api/ground-truth/ais31/runs/{run_id}/wire-prompt/{incident_id}` enforces `require_admin` (`403 Forbidden` for `SOC Analyst`, `Viewer`, and unauthenticated callers).
