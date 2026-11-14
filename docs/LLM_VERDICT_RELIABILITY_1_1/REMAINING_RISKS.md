# Verdictum AI — LLM Verdict Reliability 1.1: Remaining Risks

**Status:** Architecture-Preserving Reliability Improvements Implemented  
**Date:** 2026-11-14  

This document outlines the remaining operational, algorithmic, and infrastructure risks following the implementation of the LLM Verdict Reliability 1.1 enhancements.

---

### 1. Empirical Accuracy vs. Offline Synthetic Validation
- **Risk Description:** All verification in this release was conducted using deterministic regression test suites, synthetic telemetry, and unit fixtures without live GPU hardware.
- **Impact:** While the deterministic safety gates (claim grounding, contradiction detection, affirmative authorization checks, and fail-closed abstentions) are 100% verified, the actual **empirical accuracy, precision, and recall** of the local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) on live, ambiguous enterprise incidents cannot be claimed without empirical benchmarking against verified, human analyst-labeled historical datasets.
- **Mitigation & Future Work:**
  - Execute Phase 9 empirical benchmarking on Server 2 GPU hardware against the certified 1,000-incident analyst ground-truth dataset.
  - Compute calibration curves (Brier score, ECE) before elevating rules from `UNCALIBRATED` (capped at 6/10 trust) to `CALIBRATED`.

---

### 2. Static Context Window Fallback on Server 2 Disconnection
- **Risk Description:** If `LLMConfigService.get_or_probe_verified_max_model_len()` fails to reach the `/v1/models` endpoint during engine startup, it falls back to `LOCAL_LLM_CONTEXT_BUDGET` (default: 16,384 tokens).
- **Impact:** If the underlying vLLM / Ollama instance on Server 2 was launched with `--max-model-len 8192` or `4096`, large prompts budgeted under the 16k assumption will trigger HTTP 400 Context Window Exceeded errors, causing the circuit breaker to trip to `OPEN`.
- **Mitigation & Future Work:**
  - Enforce strict server startup orchestration where the inference engine configuration is checked during system boot.
  - Implement a conservative fallback default (e.g., 8,192 tokens) when dynamic capability probing fails.

---

### 3. Single-Pass Inference Bias & Zero Feedback Loop
- **Risk Description:** The local LLM receives only one opportunity to evaluate an incident. There is no multi-turn dialogue or self-reflection step.
- **Impact:** If the LLM produces a correct verdict with three accurate grounded claims but includes one minor ungrounded assertion or hallucinated IP in its supporting claims list, Check 3 / G3 immediately rejects the decisive verdict and forces a downgrade to `REQUIRES_ATTENTION`.
- **Mitigation & Future Work:**
  - In a future phase, evaluate a constrained two-turn reflection loop where the deterministic validator returns claim grounding feedback to the LLM for self-correction before final disposition.

---

### 4. Extreme Telemetry Volume and Pruning Tradeoffs
- **Risk Description:** Incidents generated from noisy SIEM correlation rules may contain hundreds or thousands of raw events and megabytes of script logs.
- **Impact:** While `build_model_facing_payload()` now retains up to 20 events and 4,096-character command lines, incidents exceeding the model's context capacity will have secondary events pruned (P5) or historical precedents stripped (P7) by `TokenBudgetService`. If the mandatory core (P1–P4) alone exceeds the budget, the system safely abstains with `CONTEXT_WINDOW_EXCEEDED`.
- **Mitigation & Future Work:**
  - Expand `EvidenceCompactionService` to support AST-aware script summarization for multi-megabyte PowerShell/Bash scripts.
  - Implement intelligent event deduplication at SIEM ingestion time.

---

### 5. Dependency on Approved Evidence Contracts
- **Risk Description:** The deterministic validator strictly abstains (`EVIDENCE_CONTRACT_UNVERIFIED`) if the rule's Evidence Contract is in `DRAFT`, `PENDING_REVIEW`, or `REJECTED` status.
- **Impact:** Uncertified rules cannot produce automated decisive verdicts, requiring Level-2 SOC analysts to review and approve contracts in Agent Intelligence Studio before automation can take effect.
- **Mitigation & Future Work:**
  - Continue analyst contract approval workflows through Agent Intelligence Studio (AIS).

---
*Document completed for LLM Verdict Reliability 1.1 release.*
