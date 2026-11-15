# VERDICTUM AI — VALIDATION V1.2.1
## 10. REMAINING RISKS & OPERATIONAL BOUNDARIES

**Document Version:** 1.0.0  
**Scope:** Architecture Boundaries, Hardware Dependencies, and Production Prerequisites  
**Status:** AUDITED & DOCUMENTED  

---

### 1. Identified Operational Boundaries & Non-Blocking Conditions

#### A. Dedicated GPU Host Offline Status (Server 2)
- **Status:** EXPECTED & ISOLATED
- **Details:** The production GPU inference server (`Server 2: 192.0.2.2:8000` / `gpu-inference-host`) hosting the local DeepSeek-R1 / vLLM stack is currently not connected in this local development sandbox.
- **Impact:** Live LLM chat inference calls to Server 2 will time out or return fallback responses if invoked.
- **Mitigation:** The application frontend and backend use graceful degradation, mocked fixtures for validation testing, and explicit network timeout handling (up to 300s proxy timeout in `next.config.ts`). Offline status does not impact Studio governance, quality gate scoring, or rule lifecycle management.

#### B. Production FortiSIEM Live Sync Boundary
- **Status:** CONTROLLED BOUNDARY
- **Details:** Active live sync with an external FortiSIEM instance is disabled in local test environments. The local SQLite database (`ai_verdict.db`) contains 20 canonical SIEM detection rules and synthetic incidents.
- **Mitigation:** All test scenarios and readiness evaluations run against canonical database models without mutating remote SIEM collectors.

#### C. Human Analyst Ground-Truth Accumulation
- **Status:** OPERATIONAL PREREQUISITE
- **Details:** For new detection rules (such as `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`), 30 verified analyst reviews are required before Gate G6 clears, and 93 consecutive error-free reviews are required for Gate G7 to reach the 96% Wilson lower bound.
- **Mitigation:** The UI clearly communicates this prerequisite via the `SUPERVISED LEARNING` badge and explains that automated production approval is gated on human-in-the-loop analyst feedback.

---

### 2. Safeguards Maintained
- **Zero Direct Git Pushes:** Monitored and gated by RepoDeploy Governor.
- **Zero Remote Deployments:** Withheld in accordance with Governor Stage 2 rules.
- **Zero Ground-Truth Contamination:** Protected by double-blind review API sanitization.
- **Strict Role Enforcement:** Read-Only Viewer is locked out from all policy mutations.
