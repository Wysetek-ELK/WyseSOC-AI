# Verdictum AI — Functional Requirements Specification

**Document:** `02_FUNCTIONAL_REQUIREMENTS.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** Functional Requirements for Rule Learning, Feedback, and Production Automation  
**Status:** DRAFTED & VERIFIED  

---

## 1. Overview & Traceability Structure

This document outlines the end-to-end functional requirements for transforming Verdictum AI into a Rule-Based, Human-Verified, Continuously Evaluated SOC AI Verdict Platform. Each requirement includes:
- **Requirement ID**: Unique, hierarchical identifier.
- **Priority**: P0 (Must have / Critical), P1 (High / Essential), P2 (Medium / Recommended).
- **Module**: AI Verdict Engine (A), Analyst Feedback Engine (B), Rule Learning & Evaluation (C), Production Governance (D).
- **Dependencies**: Prerequisites for implementation.
- **Description & Acceptance Criteria**: Measurable operational standards.

---

## 2. Detailed Functional Requirements

### 2.1 Incident Ingestion & Evidence Normalization (Module A)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-ING-01** | P0 | Heterogeneous Ingestion | System shall ingest incident headers and nested raw events via REST API and SIEM webhooks. | Ingestion parses top-level attributes (`incidentSrc`, `incidentTarget`, `incidentRptDevName`) and raw syslog strings without dropping vendor attributes. |
| **REQ-ING-02** | P0 | Canonical Normalization | System shall normalize raw vendor telemetry and syslog key-value tokens into `CanonicalEvidenceRecord`. | All forensic keys (`srcip`, `dstip`, `catdesc`, `url`, `action`) map deterministically to canonical paths with provenance tracking (`DIRECT`, `ALIASED`, `KEY_VALUE_EXTRACTED`). |
| **REQ-ING-03** | P0 | Isolation of Closure Metadata | Historical FortiSIEM resolution, cleared user, cleared time, and ML comments shall be stored in `historical_ground_truth` and excluded from model inference payloads. | Payload sanitizer recursively removes 100% of closure/resolution keys prior to prompt compilation. |
| **REQ-ING-04** | P1 | Event De-duplication | Compaction service shall deduplicate identical syslog messages while preserving time windows and occurrence counts. | Reduces repetitive event volume by up to 80% while retaining first-seen/last-seen timestamps and unique forensic attributes. |

---

### 2.2 Rule Identification & Prompt Compilation (Module A)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-RULE-01** | P0 | Stable Rule Identity | Each detection rule shall possess a stable, canonical identity (`rule_id`) independent of mutable display names. | Rule lookup resolves by canonical ID, linking cleanly to tenant scope and detection archetype. |
| **REQ-RULE-02** | P0 | Archetype Contract Mapping | System shall resolve detection rules to standard archetypes (`POLICY_VIOLATION`, `EXTERNAL_ATTACK`, etc.) and enforce mandatory vs conditional evidence contracts. | Firewall perimeter drops correctly treat `http.method` as conditional, avoiding false evidence-missing flags. |
| **REQ-RULE-03** | P0 | Versioned Prompt Templates | Agent Intelligence Studio 2.0 shall maintain versioned prompt templates (`PromptVersion`) with immutable audit trails. | Every prompt revision generates a new sequential version number with author ID, change summary, and quality score. |
| **REQ-RULE-04** | P0 | Token Budgeting & Clamping | Prompt compiler shall enforce strict token budgets (system prompt, policy constraints, telemetry table, output reserve) within model context bounds. | Never truncates mandatory directives; safely fails closed with `REQUIRES_ATTENTION` if budget cannot accommodate mandatory telemetry. |

---

### 2.3 LLM Inference & Evidence Validation (Module A)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-VERD-01** | P0 | Structured Tri-Verdict Output | LLM shall output a structured JSON verdict restricted to: `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ATTENTION`. | Output conforms strictly to `StructuredModelVerdict` schema with supporting evidence IDs and specific claims. |
| **REQ-VERD-02** | P0 | Independent Claim Verification | System shall verify every LLM assertion against canonical evidence values using type-aware comparisons (IP, integer, string, URL). | Any ungrounded claim or value mismatch triggers `EVIDENCE_VALUE_MISMATCH` and prevents automated validation. |
| **REQ-VERD-03** | P0 | Contradiction Guardrails | System shall check for logical contradictions (e.g., claiming internal loopback on public IP traffic, claiming authorization without approved ticket). | Contradiction drops verdict confidence to 0% and forces effective verdict to `REQUIRES_ATTENTION`. |
| **REQ-VERD-04** | P1 | Trust Score Calculation | System shall compute a deterministic 1–10 ordinal trust score based on evidence sufficiency, claim grounding, and calibration history. | Uncalibrated rules or insufficient evidence cap trust score at maximum 6/10. |

---

### 2.4 Analyst Review & Ground Truth Verification (Module B)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-REV-01** | P0 | Independent Review Interface | Analyst interface shall support independent TP, FP, or Insufficient Evidence determinations. | Analyst can review raw evidence and record a determination without AI bias when double-blind mode is enabled. |
| **REQ-REV-02** | P0 | Blind Review Reveal | System shall reveal the AI verdict and comparison only after the analyst submits their independent review. | Compares analyst verdict vs AI verdict; logs outcome as `AGREEMENT_TP`, `AGREEMENT_FP`, `FALSE_POSITIVE_OVERRIDE`, `MISSED_TRUE_POSITIVE`, or `UNRESOLVED`. |
| **REQ-REV-03** | P0 | Verified Ground Truth Store | Verified analyst reviews shall be persisted into an immutable ground truth store (`VerifiedGroundTruth` / `LearningRecord`). | Distinguishes human-verified labels from historical ML-generated resolutions; records reviewer ID, rationale, and timestamp. |
| **REQ-REV-04** | P1 | Senior Analyst Adjudication | Disputed or contradictory reviews shall be routed to Senior Analysts / SOC Managers for final binding adjudication. | L2 adjudication resolves disputes, updating the verified label while preserving the initial reviewer's audit trail. |
| **REQ-REV-05** | P1 | Audit Log Immutability | Prior analyst feedback records shall be append-only; silent overwrites are strictly prohibited. | Updates append new revision records with timestamps and author references, maintaining complete forensic provenance. |

---

### 2.5 Rule Learning & Accuracy Measurement (Module C)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-LRN-01** | P0 | Rule Learning Profile | System shall maintain a dedicated `RuleLearningProfile` for each detection rule, tracking reviewed incidents, TP/FP counts, and error categories. | Aggregates verified metrics per rule and tenant without cross-tenant bleed. |
| **REQ-LRN-02** | P0 | Statistical Accuracy Engine | System shall calculate empirical accuracy, TP recall, FP prediction precision, FP recall, confusion matrices, and Wilson score confidence intervals. | FP precision metric reflects true probability of correct FP classification with 95% lower confidence bound. |
| **REQ-LRN-03** | P0 | Minimum Sample Requirements | System shall require minimum verified sample thresholds (e.g., 30 verified cases, with both TP and FP representation) before qualifying a rule for pilot. | Rules with <30 verified cases or zero FP examples display `INSUFFICIENT_VERIFIED_DATA`. |
| **REQ-LRN-04** | P1 | Prompt Candidate Optimization | System shall use verified analyst feedback to recommend prompt improvements and evaluate candidate prompts against holdout datasets. | Candidate prompts can be tested in historical replay without altering active production prompts. |
| **REQ-LRN-05** | P1 | Error Categorization | System shall classify AI errors into structured categories (`HALLUCINATION`, `CONTRADICTION`, `INSUFFICIENT_EVIDENCE_MISSED`, `CONTEXT_OVERFLOW`, `THRESHOLD_MISINTERPRETATION`). | Errors provide actionable feedback for targeted prompt refinement. |

---

### 2.6 Simulation Lab Modernization (Module C)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-SIM-01** | P0 | Granular Funnel Diagnostics | Simulation Lab shall surface full funnel diagnostics: total scanned, ML-excluded, missing-telemetry, verified available, and evaluated. | Resolves the prior opaque `INSUFFICIENT_DATA` issue by explicitly showing why cases were excluded and what is needed for eligibility. |
| **REQ-SIM-02** | P0 | Replay & Mock Support | System shall support offline simulation replay using stored AI predictions or deterministic mock providers when external services are offline. | Simulation distinguishes `REAL_LOCAL_LLM` inference from `REPLAY` and `MOCK` with explicit execution badges. |
| **REQ-SIM-03** | P1 | Regression Detection | Simulation Lab shall compare candidate prompt performance against baseline runs, highlighting any regressions in TP recall or FP precision. | Automated regression alert flags any candidate prompt that misses a previously caught True Positive. |

---

### 2.7 Production Governance & Controlled Automation (Module D)

| Req ID | Priority | Name | Description | Acceptance Criteria |
|---|---|---|---|---|
| **REQ-GOV-01** | P0 | Rule Lifecycle State Machine | System shall enforce strict rule state transitions: `LEARNING` $\to$ `VALIDATION` $\to$ `SUPERVISED_PILOT` $\to$ `CONTROLLED_PRODUCTION` $\to$ `MONITORING`. | State transitions require minimum verified sample coverage and explicit role-based approval. |
| **REQ-GOV-02** | P0 | Controlled Automatic FP Closure | Automatic incident closure shall be restricted to rules in `CONTROLLED_PRODUCTION` with validated FP verdict, high confidence, and explicit SOC manager sign-off. | Auto-closure is disabled by default; requires active production authorization and matching tenant scope. |
| **REQ-GOV-03** | P0 | True Positive Escalation | Verified True Positive incidents shall remain open and be escalated to the active SOC analyst queue with alert notifications. | Never automatically closes or clears True Positive security incidents. |
| **REQ-GOV-04** | P0 | Multi-Gate Safety Checks | Pre-closure check shall verify: incident not actively investigated by human, evidence unchanged, no active dispute, and SIEM write-back confirmed. | Any safety gate failure aborts closure, logs audit warning, and preserves incident in analyst queue. |
| **REQ-GOV-05** | P0 | Automatic Suspension & Rollback | System shall automatically suspend a rule's production status and revert to `LEARNING` if a critical misclassification (missed TP) or precision drop is detected. | Suspension triggers immediate alert and disables auto-closure permissions instantaneously. |
| **REQ-GOV-06** | P0 | One-Click Emergency Disable | Platform administrator shall have immediate access to a global emergency kill-switch (`AUTOMATION_ENABLED=false`) disabling all automated closures. | Disables all writeback actions across all tenants within <100 milliseconds. |

---

## 3. Summary of Operational Modes

| Operational Mode | Ingestion & Norm | AI Verdict Generation | Evidence Validation | Analyst Review | Automatic FP Closure | TP Escalation |
|---|---|---|---|---|---|---|
| **LEARNING** | Active | Active | Active | Mandatory (100%) | **BLOCKED** | Manual Queue |
| **VALIDATION** | Active | Active | Active | Mandatory (100%) | **BLOCKED** | Manual Queue |
| **SUPERVISED_PILOT** | Active | Active | Active | Mandatory Sign-off | **BLOCKED** (Analyst confirms) | Priority Queue |
| **CONTROLLED_PRODUCTION** | Active | Active | Active | Random Audit Sample (10%) | **ENABLED** (Gated FP only) | Immediate Escalation |
| **SUSPENDED** | Active | Active | Active | Mandatory (100%) | **BLOCKED** | Manual Queue |

