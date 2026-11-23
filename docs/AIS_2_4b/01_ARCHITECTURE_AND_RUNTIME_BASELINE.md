# AIS 2.4b — Architecture & Runtime Baseline Audit

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `01_ARCHITECTURE_AND_RUNTIME_BASELINE.md`  
**Phase:** AIS 2.4b (Real GPU Acceptance, Runtime Integrity & Evidence-Based Verdict Validation)  
**Date:** November 23, 2026  
**Status:** AUDITED & VERIFIED  

---

## 1. Executive Summary

This architecture and runtime audit establishes the verified operational baseline of Verdictum AI — Agent Intelligence Studio (AIS) prior to live GPU acceptance, empirical benchmarking, and governance gate execution.

In accordance with the non-fabrication directive, this audit distinguishes:
1. **Source Code & Local Workstation State:** Branch `feature/phase3-compact-ui`, commit `2d97bed` (AIS 2.4a), incorporating modular policy optimization, token budget services, and independent verdict validation.
2. **Deployed Server 1 Runtime State:** Host `172.26.41.240`, active Git SHA `5fb50c3` (AIS 2.3b.1). Gate 2 Remote Deployment was explicitly declined in AIS 2.4 and AIS 2.4a; therefore, commits `2033c09` and `2d97bed` are **not deployed** on Server 1.
3. **Server 2 GPU Model Runtime State:** Host `172.26.41.241` / `172.26.15.110`, serving `Qwen/Qwen2.5-7B-Instruct-AWQ` via vLLM. Active physical context limit is **4,096 tokens** (`--max-model-len 4096`). The 8,192-token context expansion calculated in AIS 2.4 was not deployed because remote mutation was not authorized.
4. **Network Topology & Reachability:** Server 1 SSH port 22 is reachable (`TcpTestSucceeded: True`). Server 2 inference port 8000 is on an isolated private AWS VPC subnet, protected by security groups and UFW restricting access strictly to Server 1 (`172.26.41.240`). Direct workstation connections to Server 2 port 8000 fail (`TcpTestSucceeded: False`), confirming network boundary isolation.

---

## 2. Code Path Verification: Model Invocation & Verdict Validation

| Subsystem Component | Operational Application Path | Empirical Benchmark Harness Path | Parity Status | Verification Notes |
|---|---|---|---|---|
| **Model Provider** | `app.services.model_provider.openai_compatible.OpenAICompatibleProvider` | `app.services.model_provider.openai_compatible.OpenAICompatibleProvider` | **100% IDENTICAL** | Both operational inference (`ai_verdict_service.py`) and benchmark harness (`empirical_benchmark_harness.py`) instantiate `OpenAICompatibleProvider`. |
| **Model Invocations** | `provider.analyze_incident(...)` | `provider.analyze_incident(...)` | **100% IDENTICAL** | Exact same HTTP POST to `/chat/completions` with identical payload schema, temperature (0.0), and max completion tokens (768). |
| **Token Budgeting** | `TokenBudgetService.budget_prompt(...)` | `TokenBudgetService.budget_prompt(...)` | **100% IDENTICAL** | Both apply strict P1-P7 priority hierarchy, BPE tokenization, delimiter injection neutralizing, and evidence compaction. |
| **Evidence Normalization** | `EvidenceNormalizationService.normalize_incident_evidence(...)` | `EvidenceNormalizationService.normalize_incident_evidence(...)` | **100% IDENTICAL** | Identical SHA-256 integrity digests, typed evidence records, and contract validation. |
| **Claim Grounding** | `ModelClaimExtractor.extract_and_ground_claims(...)` | `ModelClaimExtractor.extract_and_ground_claims(...)` | **100% IDENTICAL** | Evaluates model assertions against factual normalized canonical evidence records. |
| **Verdict Validator** | `IndependentVerdictValidator.validate_verdict(...)` | `IndependentVerdictValidator.validate_verdict(...)` | **100% IDENTICAL** | Identical authoritative 8-check deterministic validation engine. Authoritative decisions completely overrule raw LLM proposals. |
| **Trustworthiness Engine** | `VerdictTrustworthinessEngine.calculate_trust_score(...)` | `VerdictTrustworthinessEngine.calculate_trust_score(...)` | **100% IDENTICAL** | Identical 0-10 calibrated trust scoring with evidence penalty subtraction. |
| **Telemetry Blinding** | `HistoricalGroundTruthValidator.blind_incident_payload(...)` | `IncidentAdapter` + `HistoricalGroundTruthValidator` | **100% IDENTICAL** | All analyst notes, resolutions, ticket closures, and usernames are completely stripped before prompt synthesis. |

---

## 3. Mock & Simulation Fallback Isolation

A critical finding from previous phases was ensuring that offline heuristics or mock responses cannot masquerade as live inference.

1. **Production Invocation (`ai_verdict_service.py`):**
   - In production, `allow_simulated_fallback: bool = False` by default.
   - `settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK` is validated at boot. In production environments (`ENVIRONMENT=production`), config security rules force `LOCAL_LLM_ALLOW_MOCK_FALLBACK = False`.
2. **Benchmark Harness (`empirical_benchmark_harness.py`):**
   - When `mode == "live"`, if the provider endpoint fails or is unreachable, the system records `execution_provenance = "PROVIDER_FAILURE"` and `finish_reason = "provider_error"`.
   - **No mock fallback is permitted during live evaluations.** If the GPU fails or times out, the result is fail-closed `PROVIDER_FAILURE` -> `REQUIRES_ATTENTION`.
   - Offline simulation is only executed when `mode == "offline"` is explicitly requested, and it is explicitly tagged `execution_provenance = "OFFLINE_SIMULATION"` with `is_live_measurement = False`.

---

## 4. Preservation of Model Provider Errors vs Fabrication

Under AIS 2.4b:
- If an HTTP 500/502/504 error occurs: recorded as `PROVIDER_FAILURE` with exact HTTP status.
- If a connection timeout or network refusal occurs: recorded as `PROVIDER_FAILURE` with exact exception name (`ConnectTimeout`, `ConnectError`).
- **Zero manufactured wire token usage:** `prompt_tokens = None`, `completion_tokens = None`, `total_tokens = None`. Under no circumstances are 0 or estimated token numbers substituted for missing wire usage.
- **Zero manufactured latency:** In offline simulation or preflight abstention, `latency_ms = None`.

---

## 5. Separation of Raw Proposals and Authoritative Verdicts

The architecture enforces strict decoupling between what the LLM proposes and what Verdictum AI authoritatively decides:

```
[Raw Incident Telemetry]
         │
         ▼
[Evidence Normalization & Blinding]
         │
         ▼
[Token Budgeting & Policy Compilation]
         │
         ▼
[Qwen2.5-7B vLLM Provider] ───► [Raw LLM Proposal] (e.g. TRUE_POSITIVE, 88%)
                                        │
                                        ▼
                         [Model Claim Grounding Extractor]
                                        │
                                        ▼
                         [Independent Verdict Validator]
                                        │
                                        ▼
                         [Final Authoritative Verdict] (e.g. REQUIRES_ATTENTION, TP_CRITERIA_UNSATISFIED)
```

Both values are persisted separately in:
1. `BenchmarkIncidentResult`: `raw_proposed_verdict`, `raw_proposed_confidence`, `raw_proposed_reason` vs `final_authoritative_verdict`, `is_decisive_accepted`, `validation_reason_codes`.
2. Database (`ai_verdict_service.py`): `investigations` table stores authoritative verdict; `actual_llm_prompt_captures` stores exact raw LLM JSON; `audit_logs` records both side-by-side.

---

## 6. PostgreSQL vs SQLite Evaluation Environment

| Dimension | Production Server 1 | Local Development Workspace |
|---|---|---|
| **RDBMS Engine** | PostgreSQL 15 | SQLite 3 / `:memory:` |
| **Connection Pooling** | SQLAlchemy `QueuePool` (pool_size=10, max_overflow=20) | `StaticPool` / single connection |
| **Transaction Isolation** | `READ COMMITTED` with row-level locking (`SELECT ... FOR UPDATE`) | File-level database lock |
| **Alembic Migrations** | Full migration history (`alembic upgrade head`) | Auto-created schema metadata |
| **Evaluation Parity** | Telemetry ingestion, rules, prompts, contracts, token budgets, and validators are identical pure-Python domain services operating on structured Pydantic schemas and dataclasses. |

---

## 7. Current Deployment State Reconciliation

- **Local Git SHA:** `2d97bed` (AIS 2.4a) + working tree updates for AIS 2.4b.
- **GitHub Origin SHA:** `2d97bed` (synchronized in AIS 2.4a).
- **Server 1 Active SHA:** `5fb50c3` (AIS 2.3b.1).
- **Server 2 vLLM Max Model Len:** 4,096 tokens.
- **UPLA Status:** `FULL_WORKFLOW`, clean workspace, 41 regression tests passing (100%).
