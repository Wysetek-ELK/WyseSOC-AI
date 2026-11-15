# Operational Considerations & Remaining Risks

**Document:** `08_REMAINING_RISKS.md`  
**Validation Phase:** Verdictum AI — Validation V1.2  
**Evaluator:** SOC Platform Architect, Security Governance Auditor  
**Date:** November 15, 2026  

---

## 1. Executive Summary

While Validation V1.2 successfully repaired all known UI capture defects, resolved production status inconsistencies, enforced strict RBAC, and validated 0px overflow across all viewports, real-world deployment of autonomous SOC platforms introduces specific operational considerations.

This document identifies remaining technical and operational risks, assesses their impact, and establishes clear mitigation controls.

---

## 2. Risk Assessment Matrix

| Risk ID | Risk Description | Likelihood | Impact | Severity | Mitigation Strategy |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **RSK-01** | **Live FortiSIEM Connectivity Jitter:** Latency or intermittent timeouts when polling live FortiSIEM Supervisor REST APIs. | Medium | Medium | **MODERATE** | Poller utilizes exponential backoff with circuit breaker pattern and cached telemetry fallback. |
| **RSK-02** | **Local LLM Memory & Latency Under Burst:** High alert burst may queue inference jobs on Server 2 (local GPU). | Low | High | **MODERATE** | Queued verdict backlog monitoring in Telemetry Hub; auto-throttling to heuristic triage if inference queue exceeds threshold. |
| **RSK-03** | **Database Schema Migration:** Production environments migrating from SQLite to PostgreSQL must preserve existing `policy_version_records`. | Low | High | **MODERATE** | Alembic migration scripts tested and validated with idempotent version indexing. |
| **RSK-04** | **Analyst Adjudication Drift:** Insufficient analyst reviews leading to uncalibrated empirical thresholds (G5). | Medium | Medium | **MODERATE** | Stage 4 enforces a minimum of 30 double-blind analyst reviews before G5 pass is granted. |
| **RSK-05** | **Browser Cache Retention:** Stale local client bundles retaining old token caching or navigation state. | Low | Low | **LOW** | Next.js build hashes static assets; API auth automatically clears stale tokens on 401. |

---

## 3. Detailed Operational Guidance

### 3.1 Live FortiSIEM Integration Safeguards
- In test environments, Verdictum AI utilizes simulated event streams and synthetic rule catalogs. When deploying to live FortiSIEM:
  1. Confirm FortiSIEM credentials (`FORTISIEM_HOST`, `FORTISIEM_USER`, `FORTISIEM_PASSWORD`) are configured via secure environment variables.
  2. Verify that the continuous poller runs on a dedicated worker thread with timeout guards (`timeout=15s`).
  3. Ensure that SIEM deployment status (`rule.status`) is synced bidirectionally without overwriting local policy version governance.

### 3.2 Server 2 (Local LLM) Inference Governance
- When local LLM is offline or experiencing heavy VRAM utilization:
  - Telemetry Hub surfaces the `LLM Offline / Mock Active` warning banner.
  - The platform automatically falls back to simulated inference or flags alerts as `REQUIRES_ATTENTION` for immediate human review.
  - No autonomous true positive / false positive verdict is permanently committed to FortiSIEM without model execution provenance.

### 3.3 Rule Learning & Drift Monitoring
- Monitored rules operate with continuous drift detection:
  - If a rule's rolling false positive rate exceeds 15% over a 7-day window, a drift event (`POLICY_DRIFT_WARNING`) is recorded.
  - The rule's operational status transitions from `ACTIVE` to `NEEDS_ACTION` or `SUSPENDED`.
  - SOC Administrators receive an immediate notification in Agent Mission Control to trigger re-simulation.

---

## 4. Governance Sign-Off

All identified risks have established mitigations and monitoring telemetry. No unmitigated critical or high-severity vulnerabilities remain in the platform codebase.
