# VERDICTUM AI — PHASE 3
# 05. Intelligent Diagnostics & Error Mapping Specification

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Engine Implementation:** `frontend/src/lib/diagnostics.ts`  

---

## 1. Engine Architecture

The Intelligent Diagnostic Engine (`diagnostics.ts`) addresses three major operational friction points identified during the Phase 3 audit:
1. **Scattered Warnings:** The same error code (e.g. `G1_RULE_DEFINITION_INCOMPLETE`) was presented in up to 5 disparate UI components.
2. **Cryptic Technical Jargon:** Error strings like `HTTP 422 Unprocessable Entity` or raw validation arrays failed to explain *what* failed or *how* to fix it.
3. **Misleading Statistical Zeroes:** Zero empirical reviews displayed as `0% Accuracy` with a red failure badge.

---

## 2. Issue Prioritization & Severity Hierarchy

The diagnostic engine extracts and prioritizes all system issues using a 6-tier operational weight hierarchy:

| Tier | Category | Priority Weight | Description |
|---|---|---|---|
| **Tier 1** | Security / Kill-Switch | 100 | Emergency automation shut-off, ungrounded hallucination spikes |
| **Tier 2** | System / Infrastructure | 90 | Server 2 vLLM node offline, network communication timeouts |
| **Tier 3** | Rule Definition Gaps | 85 | Missing FortiSIEM correlation conditions, unverified thresholds (G1) |
| **Tier 4** | Evidence Telemetry Gaps | 80 | Missing mandatory canonical fields (G2), unmapped attributes |
| **Tier 5** | Accuracy & Review Gaps | 70 | Zero verified reviews, sample size below pilot threshold (<30) |
| **Tier 6** | Governance / Eligibility | 60 | Unfulfilled criteria blocking production promotion (G8) |

Identical root causes are automatically deduplicated into a single card while preserving distinct error causes.

---

## 3. Technical Error Mapping Dictionary

The engine translates low-level backend validation codes into clear, actionable operational summaries:

### 3.1 Rule Definition Incomplete (Gate G1)
- **Raw Code:** `G1_RULE_DEFINITION_INCOMPLETE` / `RULE_DEFINITION_INCOMPLETE`
- **Plain-Language Title:** Detection Rule Definition Missing
- **Cause:** Authoritative FortiSIEM correlation logic and event count thresholds have not been imported or verified.
- **Missing Elements:** Verified detection rule conditions and event thresholds.
- **Operational Impact:** Policy remains a provisional draft; production approval is hard-blocked.
- **Next Action:** Review the original FortiSIEM detection rule in SIEM Semantics or re-import definitions.
- **Target Navigation:** `advanced` -> `intelligence`

### 3.2 Evidence Telemetry Incomplete (Gate G2)
- **Raw Code:** `G2_MANDATORY_FIELDS_MISSING` / `MISSING_EVIDENCE_FIELDS`
- **Plain-Language Title:** Mandatory Evidence Telemetry Missing
- **Cause:** Ingested incidents lack required canonical telemetry fields defined in the Evidence Contract.
- **Missing Elements:** Listed missing fields (e.g. `processName`, `sourceIp`, `user`).
- **Operational Impact:** AI verdict triage cannot ground claims reliably; automated closure is disabled.
- **Next Action:** Check FortiSIEM attribute mapping or expand the evidence contract.
- **Target Navigation:** `advanced` -> `contract`

### 3.3 AI Accuracy Not Verified (Gate G8)
- **Raw Code:** `INSUFFICIENT_GROUND_TRUTH_SAMPLES` / `ZERO_VERIFIED_REVIEWS`
- **Plain-Language Title:** AI Accuracy Not Verified — Analyst Reviews Required
- **Cause:** No independently verified analyst TP/FP reviews have been recorded for this detection rule.
- **Missing Elements:** Ground truth evaluation dataset (target: 30 for pilot, 100 for production).
- **Operational Impact:** Empirical accuracy cannot be calculated (displayed as N/A); automated actions disabled.
- **Next Action:** Perform independent double-blind reviews on pending incidents in Analyst Review tab.
- **Target Navigation:** `learning`

### 3.4 Inference Provider Offline
- **Raw Code:** `LLM_PROVIDER_OFFLINE` / `ENDPOINT_UNREACHABLE`
- **Plain-Language Title:** Local Inference Engine Offline
- **Cause:** Server 2 vLLM inference node is currently unreachable.
- **Missing Elements:** Active connection to Qwen 2.5 7B inference endpoint.
- **Operational Impact:** System running on deterministic heuristic fallback; live LLM generation paused.
- **Next Action:** Verify Server 2 inference node status or check network connectivity.
- **Target Navigation:** `overview`

---

## 4. HTTP Error Sanitization (`formatHttpError`)

The `formatHttpError` helper intercepts Axios/fetch exceptions and prevents raw stack traces or JSON blobs from reaching the user:
- **HTTP 422:** Extracts field locations and human messages (e.g. `body.policy_contract: Field required`) and marks `isRetryable = false`.
- **HTTP 403:** Displays *"Permission Required: Your current account role does not possess authorization to execute this operational action."*
- **HTTP 500:** Displays *"Server Internal Error: The backend service encountered an unexpected condition. State has not been corrupted."* and marks `isRetryable = true`.
- **Network Timeout:** Displays clean communication failure notification with request ID if available.
