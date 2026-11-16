# VERDICTUM AI — VALIDATION V1.2.3: REMAINING RISKS & OPERATIONAL CONTROLS

## 1. Risk Matrix Overview

Following the successful deployment and remote validation of Verdictum AI Server 1 under commit `17bed13`, this document outlines the remaining operational risks, their architectural mitigations, and the recommended SOC workflows.

| Risk ID | Severity | Category | Risk Description | Current Mitigation | Permanent Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-123-01** | **MEDIUM** | Infrastructure | **GPU Server 2 (Verdictum Cortex) Offline**<br/>The dedicated LLM worker host (`13.***.***.64:8000`) is currently unreachable. | System fails safe: API health accurately reports `degraded`, circuit breaker is closed, and manual L1 triage is 100% operational. | Restore GPU VM instance, verify vLLM / AWQ container startup, and re-probe endpoint. |
| **RSK-123-02** | **LOW** | Policy Governance | **Quality Gate G1 Incomplete**<br/>`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` rule definition lacks authoritative FortiSIEM correlation thresholds. | G1 fails closed (Score: 0/10), blocking policy promotion to production until authoritative parameters are supplied. | Ingest full FortiSIEM XML/JSON rule definitions containing packet thresholds and time-window conditions. |
| **RSK-123-03** | **LOW** | Machine Learning | **Quality Gate G8 Insufficient Ground Truth**<br/>Rule has 0 verified human analyst ground-truth cases (minimum 5 required for G8 simulation). | G8 returns `WARNING` (0/15 points), keeping total score at 77.0 and preventing policy promotion. | SOC analysts review historical incidents in Analyst Review & Learning Workbench to establish baseline ground truth. |
| **RSK-123-04** | **LOW** | Availability | **Single-Instance Server 1 VM**<br/>Verdictum Core runs on a single Azure VM instance (`20.***.***.138`). | Automated systemd service restart (`ai-verdict-backend.service`), local PostgreSQL connection pooling, and low resource overhead (CPU: 0.4%, RAM: 24.7%). | Implement multi-AZ auto-scaling or active-passive replica architecture during enterprise scaling phase. |

---

## 2. In-Depth Operational Risk Analysis

### 2.1 GPU Server 2 Offline (RSK-123-01)
- **Technical Context**: The health probe against Server 1 reveals `local_llm.status = "offline"` and `current_s2_health = "OFFLINE"`.
- **System Impact**:
  - Live incident triage cannot generate real-time AI reasoning verdicts.
  - Incident queue continues to accumulate FortiSIEM telemetry without data loss.
  - UI accurately shows "AI Engine Offline" rather than displaying hallucinated verdicts.
- **Fail-Safe Mechanism**: The platform gracefully degrades to standard human SOC triage without hanging or throwing unhandled 500 errors.

### 2.2 Authoritative SIEM Detection Logic (RSK-123-02)
- **Technical Context**: Live FortiSIEM rule sync captured runtime event metadata (`incidentCount: 161`) rather than the underlying SIEM aggregation filter (e.g., `TCP SYN count > 100 within 60s to distinct host IPs`).
- **Safety Impact**:
  - Without the authoritative threshold, the AI policy cannot establish exact True Positive bounds.
  - Quality Gate G1 strictly flags: `RULE_DEFINITION_INCOMPLETE: Rule lacks authoritative SIEM detection logic`.
- **Action Plan for L1 Engineers**: The L1 engineer is guided by `blocking_requirements` to manually upload or link the authoritative rule XML.

### 2.3 Ground Truth Volume & Empirical Validation (RSK-123-03)
- **Technical Context**: Quality Gate G8 evaluates statistical empirical performance on past cases. It mandates:
  - Minimum 5 verified cases for pilot evaluation.
  - Recommended 30 verified cases for production promotion.
- **Current State**: Evaluated cases: 69; Verified ground-truth cases: 0.
- **Action Plan**:
  1. Open Analyst Review Workbench.
  2. Perform blind triage on 5+ unreviewed incidents for `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`.
  3. Submit analyst verdicts.
  4. Trigger G8 re-evaluation in Agent Intelligence Studio 2.0.

---

## 3. Operational Sign-Off Recommendation

None of the identified remaining risks constitute a security vulnerability, data leakage vector, or deployment blocker. The system's fail-closed governance ensures that unready policies cannot be promoted and offline inference engines are transparently surfaced to operators.
