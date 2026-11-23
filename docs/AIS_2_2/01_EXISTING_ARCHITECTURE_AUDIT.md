# AIS 2.2 Report 01: Existing Architecture & Data Audit

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## 1. Executive Summary

As part of Stage A of the AIS 2.2 milestone, an exhaustive, read-only architectural and data integrity audit was conducted across the Verdictum AI codebase, database schemas, API routes, inference pipelines, and frontend interfaces. 

The audit focused on evaluating whether existing components can support a reproducible, evidence-grounded empirical accuracy baseline for Verdictum AI's local Qwen LLM without introducing architectural bloat, duplicate microservices, or Docker dependencies.

---

## 2. Component Inventory & Operational Verification

Each of the 15 required functional subsystems was inspected and categorized under one of the five formal status designations:
- `VERIFIED_WORKING`: Code exists, is tested by automated regression suites, and functions reliably.
- `IMPLEMENTED_UNVERIFIED`: Code exists and is syntactically complete, but lacks live end-to-end GPU verification due to offline inference endpoints.
- `DEFECTIVE`: Code exists but contains confirmed runtime defects, race conditions, or isolation errors.
- `MISSING`: Functional requirement is completely unrepresented in the codebase.
- `NOT_APPLICABLE`: Requirement not relevant to current bare-metal architecture.

| ID | Architectural Subsystem | Status | Audit Findings & Code References |
|---|---|---|---|
| **1** | FortiSIEM Incident Ingestion & Storage | `VERIFIED_WORKING` | Handled by `TelemetryHubPollerWorker` and `FortiSiemClient`. Incidents are stored in PostgreSQL/SQLite `incidents` table with normalized JSON payloads, external IDs, and customer tenancy. |
| **2** | Raw Log Storage & Incident-to-Event Relationships | `VERIFIED_WORKING` | Events are ingested into `events` and linked via foreign keys to `incidents.id`. `IncidentPayload` preserves complete raw log bundles (`events[]`). |
| **3** | Triggered Detection Rule Storage | `VERIFIED_WORKING` | Detection rules stored in `rules` table with canonical UUID, event_type (`PH_RULE_*`), severity, status, and MITRE ATT&CK mappings. |
| **4** | Historical Analyst Verdict Storage | `VERIFIED_WORKING` | Analyst determinations stored in `analyst_verdict_reviews` table. Dual-blind reviews recorded with analyst ID, verdict (TP/FP/REQUIRES_ATTENTION), comments, and timestamps. |
| **5** | Ground-Truth Eligibility & Provenance | `VERIFIED_WORKING` | `HistoricalGroundTruthValidator` adjudicates labels into `VERIFIED_TP`, `VERIFIED_FP`, `UNVERIFIED`, and `CONFLICTING`. Filters out automated bot/system closures. |
| **6** | Blind-Review Protection | `VERIFIED_WORKING` | Double-blind masking enforced at API layer (`AnalystReviewService.get_unreviewed_incident`). Sanitizes AI suggestions and peer analyst comments until submission. |
| **7** | Prompt Generation & Assembly | `VERIFIED_WORKING` | Managed by `PolicyCompilerService` and `TokenBudgetService`. Assembles common prompt, rule-specific prompt, evidence tables, and historical precedents within token budgets. |
| **8** | Active & Draft Policy Resolution | `VERIFIED_WORKING` | Governed by `PromptVersion` lifecycle. Enforces that only 1 version is `APPROVED` per rule, while candidates remain `DRAFT`. Target rule has v7 (`APPROVED`) and v8 (`DRAFT`). |
| **9** | AI Verdict Execution Services | `VERIFIED_WORKING` | Implemented in `VerdictIntelligenceService` and `AisEvaluationService`. Dispatches inference requests, collects output, and coordinates post-execution validators. |
| **10** | Model-Facing Payload Sanitation | `VERIFIED_WORKING` | `HistoricalGroundTruthValidator.sanitize_incident_for_inference` strips FortiSIEM closure metadata, resolution notes, and ground truth hints before dispatch. |
| **11** | LLM Request & Response Handling | `IMPLEMENTED_UNVERIFIED` | OpenAI-compatible API client configured for `http://13.204.214.64:8000/v1` with model `Qwen/Qwen2.5-7B-Instruct-AWQ`. Ready for live execution but Server 2 is offline. |
| **12** | Verdict Persistence & Audit Tracking | `VERIFIED_WORKING` | Recorded in `actual_prompt_captures` and `verdict_trust_assessment_records`. Captures exact system prompt, user prompt, SHA256 hashes, raw output, latency, and tokens. |
| **13** | Evaluation Population & Snapshot Contracts | `DEFECTIVE` (REMEDIATED) | Commit `7a3c98b` introduced transaction isolation defect causing HTTP 500 under PostgreSQL when auth queries ran first. Remediated and verified in AIS 2.2. |
| **14** | Learning Profiles & Retrieval Mechanisms | `VERIFIED_WORKING` | `RuleLearningService` maintains rule-level dynamic accuracy metrics, error distributions, and historical learning precedents. |
| **15** | Benchmark & Empirical Accuracy Engines | `VERIFIED_WORKING` | `EmpiricalBenchmarkHarness` and `EmpiricalAccuracyEvaluator` calculate Wilson score intervals, confusion matrices, and enforce `NOT_MEASURABLE` zero-denominator safeguards. |

---

## 3. End-to-End Telemetry & Evaluation Flow

```
+-----------------------------------------------------------------------------------+
| 1. TELEMETRY & INGESTION                                                          |
|    FortiSIEM JSON Telemetry ---> Ingestion Worker ---> Database (incidents, events)|
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| 2. ANTI-LEAKAGE SANITIZATION & EVIDENCE EXTRACTION                                 |
|    Strip: incidentResDescription, clearedReason, clearedUser, analyst comments    |
|    Extract: CanonicalEvidenceRecord, Preflight Validation, Contract Verification    |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| 3. POLICY RESOLUTION & PROMPT COMPILATION                                         |
|    Resolve Policy: v7 (APPROVED Baseline) vs v8 (DRAFT Candidate)                  |
|    Compile: Common SOC Context + Rule Prompts + Dynamic Token Budget               |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| 4. LOCAL GPU LLM INFERENCE (Server 2: Qwen2.5-7B-Instruct-AWQ)                    |
|    Dispatched via OpenAI-compatible API (temperature=0.0, top_p=1.0)               |
|    Raw Model Proposal Captured (actual_prompt_captures)                            |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| 5. INDEPENDENT VALIDATION & GUARDRAILS                                            |
|    Evidence Claim Grounding ---> Schema Compliance ---> Trust Score Assessment     |
|    Safety Invariant: Unsafe FP Check (Never auto-clear TP without verification)   |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| 6. AUDIT PERSISTENCE & EMPIRICAL ACCURACY ENGINE                                  |
|    Authoritative Disposition Persisted (verdict_trust_assessment_records)          |
|    Wilson 95% CIs + Confusion Matrix + NOT_MEASURABLE Zero-Denominator Protection  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Key Architectural Conclusions

1. **No New Services Required:** The existing architecture contains all necessary primitives for evidence extraction, prompt compilation, trust evaluation, and audit logging.
2. **Defect Isolated to PostgreSQL Transaction Handling:** The discrepancy reported in AIS 2.1b.1 was caused by a specific database transaction rollback omission, not an architectural flaw.
3. **Hardware Readiness:** Server 1 (`172.26.41.240`) is completely operational and hosts the backend, frontend, and PostgreSQL database. Server 2 (`13.204.214.64`) is configured for GPU inference but is stopped/offline to avoid unnecessary billing until scheduled inference runs.
