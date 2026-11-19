# 01 — Existing System & Rule Audit
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Logical Rule ID / Event Type:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`  
**Date of Audit:** November 19, 2026  
**Architecture:** Verdictum AI AIS 2.0 V8.3a  

---

## 1. Executive Summary & Audit Scope

This audit establishes the baseline architectural state, operational configuration, and authoritative rule identity for onboarding the FortiSIEM correlation rule **`Website access policy violation: Same Source and Destination`** into Verdictum AI AIS 2.0 V8.3a. 

The evaluation accounts for the administrator's recent purge of historical FortiSIEM incidents. All evaluations are performed against the fresh post-purge telemetry dataset without carrying forward invalid historical assumptions, manufacturing missing telemetry, or fabricating unverified ground-truth labels.

---

## 2. Platform Architecture & Infrastructure Topology

The production environment operates under a dual-server distributed architecture with air-gapped GPU inference and strict governance:

| Component | Host / IP | Role & Software Stack | State / Governance Mode |
| :--- | :--- | :--- | :--- |
| **Server 1: Verdictum Core** | `172.26.41.240` | - Ubuntu Linux (Non-Docker systemd deployment under `/opt/wysesoc-ai`)<br>- Python 3.13 FastAPI backend on port `8000`<br>- Next.js 14 frontend on port `3000`<br>- Nginx reverse proxy on port `80`<br>- PostgreSQL relational database & audit logs<br>- Redis 7 & Celery asynchronous task queues | **ONLINE & OPERATIONAL**<br>UPLA Active Mode: `FULL_WORKFLOW`<br>Rule Governance: `ADVISORY_ANALYST_REVIEW_REQUIRED` |
| **Server 2: Verdictum Cortex** | `13.204.214.64` (port `8000`) | - Dedicated AWS GPU host (NVIDIA A10G/vLLM)<br>- Local Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`<br>- Max Context: `4,096` tokens<br>- Max Completion Budget: `768` tokens<br>- Provider Type: `OPENAI_COMPATIBLE` | **ONLINE & OPERATIONAL**<br>Health Check: HTTP 200 (68ms roundtrip latency)<br>Model Identifier: `Qwen/Qwen2.5-7B-Instruct-AWQ` |
| **SIEM Source: FortiSIEM Supervisor** | `https://172.26.26.31` | - FortiSIEM 6.x/7.x Cluster Supervisor<br>- Auth: `super/test`<br>- Ingestion: Continuous Pull & Sync API<br>- Automated write-back / incident closure: `DISABLED` | **ONLINE & SYNCHRONIZING**<br>Auto-closure strictly blocked under safety guardrails |

---

## 3. Authoritative Rule Identity & Registry Audit

The target rule identity was verified against the authoritative FortiSIEM rule definitions and the Verdictum AI PostgreSQL registry:

- **Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`
- **Rule Name:** `Website access policy violation: Same Source and Destination`
- **Event Type / Logical Rule ID:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
- **Rule Severity:** `MEDIUM` (Severity Code: 5)
- **Rule Status:** `ACTIVE` (FortiSIEM Rule Active, Enabled: true)
- **Category:** `Web Access Policy / Compliance`
- **Detection Archetype:** `POLICY_VIOLATION` (Enterprise Security Policy Violation)
- **Active Approved Policy Version:** Version 2 (`ccb9dffa-e29e-49b6-b945-4359829272b6`, Status: `APPROVED`)
- **Candidate Draft Policy Version:** Version 3 (`6559b1e7-55ac-4f15-8699-aabf251f997a`, Status: `DRAFT`)
- **Authoritative Provenance:** `AUTHORITATIVE_XML_IMPORT` (Verified XML imported via `/api/rules/7bd13e89-0828-48e6-8cf5-f3cbf12d438c/import-definition`)
- **Rule Drift Status:** Drift acknowledged; `drift_detected: false`, `is_definition_synced: true`.

---

## 4. Sibling Rule Decoupling & Isolation Guarantee

The audit verified complete isolation from all sibling rules:

- **Sibling Rule:** `Heavy TCP Host Scan On Fixed Port`
  - UUID: `40498741-ee6b-4a71-9101-0d6d3f77154c`
  - Event Type: `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`
  - Archetype: `NETWORK_SCAN`
  - Active Policy: **Version 7 APPROVED** (`STATUS: APPROVED`)
  - Ground Truth & Learning Records: **Completely preserved and unaffected**
  - Verification: Queried `/api/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c`; confirmed Version 7 APPROVED remains active, lifecycle stage `LEARNING`, zero interference.

---

## 5. Subsystem Component Readiness

| Subsystem | Audit Status | Key Operational Capabilities Verified |
| :--- | :--- | :--- |
| **EvidenceContractService** | **PASS** | Dynamic contract mapping for `POLICY_VIOLATION`; validates core and conditional telemetry fields. |
| **PolicyCompilerService** | **PASS** | 9-section AIS prompt compilation; enforces safety directives, anti-injection, and EV-* evidence bindings. |
| **TokenBudgetService** | **PASS** | Strict context management: 4,096 max context, 768 completion budget, zero token truncation. |
| **EvidenceCompactionService** | **PASS** | Deduplication, sliding window compaction, and canonical EV-ID indexing. |
| **VerdictPipeline** | **PASS** | End-to-end orchestration from raw telemetry ingestion to governed verdict output. |
| **IndependentVerdictValidator** | **PASS** | Deterministic check engine enforcing grounding ratios, evidence completeness, and decision criteria. |
| **ReasoningIntegrityEngine** | **PASS** | Cross-field consistency, loopback claim rejection on distinct external IPs, firewall action validation. |
| **ConfidenceNormalizer** | **PASS** | Strict capping of uncalibrated trust scores to $\le 6/10$; suppresses decisive automation on fresh datasets. |
| **AnalystReviewService** | **PASS** | Double-blind masking (`is_blind_mode: true`), independent determination recording, agreement tracking. |
| **RuleLearningService** | **PASS** | Lifecycle tracking, confusion matrix calculation, Wilson lower-bound accuracy, Gate G8 evaluation. |
| **EmpiricalBenchmarkHarness** | **PASS** | Batch evaluation runner against live local GPU inference without synthetic shortcuts. |
| **UPLA Governance Engine** | **PASS** | `FULL_WORKFLOW` mode active, Gate 1 & Gate 2 human approval gates strictly enforced. |
