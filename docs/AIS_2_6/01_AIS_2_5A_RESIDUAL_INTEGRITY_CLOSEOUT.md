# 01 — AIS 2.5a Residual Integrity Closeout Report

## Executive Summary

This report documents the definitive forensic investigation and empirical resolution of all residual integrity discrepancies identified in AIS 2.5a. Under AIS 2.6, all token-budget admission invariants, execution provenance normalizations, historical SIEM resolution mappings, cluster counting contradictions, and validator abstention contradiction statuses have been fully reconciled and cryptographically bound to deployed commit `71bf3ba2969e3082c9e2d6b522abdaaef2613c80`.

---

## 1. Token-Budget Invariant Violation Investigation (Stage 1.1)

### 1.1 The Anomaly
In AIS 2.5a, Server 2 was operating with `--max-model-len 4096` and a mandatory reserved completion budget of `768 tokens`. The theoretical and enforced maximum input prompt budget was:
$$	ext{Available Input Budget} = 4096 - 768 = 3328 	ext{ tokens}$$

However, ten live CrowdStrike provider prompts were reported to have consumed between `3,347` and `3,418` wire tokens at the vLLM provider, while preflight admission was erroneously recorded as successful.

### 1.2 Root Cause Analysis
Forensic audit of `empirical_benchmark_harness.py` revealed that `evaluate_single_incident` had a default argument:
```python
max_context_tokens: int = 8192
```
When benchmark incidents were evaluated without explicitly overriding `max_context_tokens=4096`, `TokenBudgetService.budget_prompt` budgeted for an 8,192 context window:
$$	ext{Budgeted Prompt Limit} = 8192 - 768 = 7424 	ext{ tokens}$$
Consequently, prompts containing 3,347–3,418 tokens were admitted because $3418 \le 7424$. When these prompts reached the physical vLLM server on Server 2 (which had `--max-model-len 4096`), vLLM processed the prompt (since $3418 < 4096$), but the effective completion headroom was compressed from 768 tokens down to 678 tokens ($4096 - 3418 = 678$), violating the completion reserve invariant.

### 1.3 Resolution & Invariant Enforcement
Under AIS 2.6, the benchmark harness and production pipeline strictly bind `max_context_tokens` to the verified active runtime configuration (`4096 tokens`):
$$	ext{actual\_wire\_prompt\_tokens} + 	ext{reserved\_completion\_tokens} \le 	ext{active\_max\_model\_len}$$
$$	ext{actual\_wire\_prompt\_tokens} + 768 \le 4096 \implies 	ext{actual\_wire\_prompt\_tokens} \le 3328$$

Any prompt whose wire tokens exceed 3,328 tokens is intercepted at preflight with reason code `TOKEN_BUDGET_GUARD` / `CONTEXT_WINDOW_EXCEEDED` and routed to analyst attention without GPU dispatch.

---

## 2. Execution Provenance Normalization (Stage 1.2)

### 2.1 The Misclassification
In AIS 2.5a, execution provenance was fragmented into ad-hoc labels including `TOKEN_BUDGET_GUARD`, `POLICY_GUARD`, `PREFLIGHT_GUARD`, and `LIVE_PROVIDER`. Furthermore, the 36,518 preflight-evaluated tokens across 10 Prisma SASE incidents were conflated with live GPU token consumption, falsely suggesting 74,853 GPU tokens were billed.

### 2.2 Normalized Provenance Standard
AIS 2.6 enforces the strict four-tier execution provenance taxonomy:
1. `LIVE_PROVIDER`: Genuine inference dispatched over network socket to active LLM engine.
2. `OFFLINE_SIMULATION`: Deterministic offline execution for environments without GPU access.
3. `PREFLIGHT_ABSTENTION`: Intercepted prior to inference by policy, contract, or token budget guards.
4. `PROVIDER_FAILURE`: Network timeout, HTTP 5xx, or provider infrastructure failure.

`TOKEN_BUDGET_GUARD` is now recorded as a **reason code**, not an execution provenance.

### 2.3 Strict Accounting Separation
| Metric Category | Prompt Tokens | Completion Tokens | Total Billed Tokens | Notes |
|---|---|---|---|---|
| **Live GPU Consumption** (`LIVE_PROVIDER`) | 33,702 | 4,633 | **38,335** | 10 CrowdStrike incidents |
| **Preflight Interceptions** (`PREFLIGHT_ABSTENTION`) | 0 | 0 | **0** | 10 Prisma SASE incidents |
| **Preflight Estimated Input Demand** | 36,518 | 0 | 36,518 | Intercepted in ~450ms |
| **Combined Accounting Ledger** | 33,702 | 4,633 | **38,335 (Actual GPU)** | Zero token conflation |

---

## 3. Historical Evidence Reconciliation (Stage 1.3)

### 3.1 Incident 132474210 SIEM Resolution
- **Prior Error**: Previous reports replaced the authentic SIEM resolution with generic `Operational Closed`.
- **Authoritative SIEM Audit**: Inspection of raw event export in `fixtures/Incident json.zip` confirms:
  - `resolution`: `"False Positive"`
  - `clearedReason`: `"legitimate activity, nothing suspicious observed."`
  - `clearedUser`: `"security_analyst_3"`
- **Reconciliation**: Manifest updated to accurately record original SIEM resolution as `False Positive` while retaining `PROVISIONAL_UNVERIFIED` for independent human certification.

### 3.2 Telemetry Cluster Counting Reconciliation
- **Prior Error**: Contradictory reports claimed both 7 and 10 clustered incidents.
- **Reconciled Audit**:
  - **Cluster 1** (`CrowdStrike: UltraViewer on DESKTOP-E0G2R49`): 5 incidents (`132438483`, `132439932`, `132441815`, `132461358`, `132461368`)
  - **Cluster 2** (`CrowdStrike: UltraViewer on TSI-IT-002-95`): 2 incidents (`132501348`, `132527297`)
  - **Cluster 3** (`Prisma SASE: surveysensum.com on 10.66.19.16`): 3 incidents (`132599145`, `132599146`, `132599330`)
  - **Total Clustered Incidents**: exactly **10 incidents** across **3 clusters**.
  - **Independent Incidents**: exactly **10 incidents**.
  - **Total Benchmark Cohort**: $10 + 10 = 20$ incidents.

### 3.3 Contradictory Reasoning on Safe Abstentions
- **Prior Error**: When the model proposed `REQUIRES_ATTENTION` but its reasoning contained `EVIDENCE_CONTRADICTION` or `REASONING_CONTRADICTION`, the validator marked the record as `VALIDATED`.
- **Validator Correction**: Lines 915–925 of `independent_verdict_validator.py` updated to assign `validation_status = "ABSTENTION_WITH_CONTRADICTION"`. A safe final abstention is no longer declared soundly validated if its underlying reasoning exhibits internal contradictions.
