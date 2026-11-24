# 03 — Token Budget and Raw Evidence Integrity

## 1. Architectural Invariant

$$\text{actual\_wire\_prompt\_tokens} + \text{reserved\_completion\_tokens} \le \text{active\_max\_model\_len}$$

Under the verified 4,096-token runtime configuration:
$$\text{actual\_wire\_prompt\_tokens} + 768 \le 4096 \implies \text{actual\_wire\_prompt\_tokens} \le 3328$$

---

## 2. End-to-End Pipeline Accounting

The pipeline follows six deterministic stages:
$$\text{FortiSIEM Raw Logs} \longrightarrow \text{Canonical Evidence} \longrightarrow \text{Policy Compiler} \longrightarrow \text{Prompt Builder} \longrightarrow \text{Token Budgeting} \longrightarrow \text{Provider Request}$$

### CrowdStrike Rule Cohort (10 Incidents)
- Compiled System Prompt: ~2,480 tokens
- Model-Facing Incident Telemetry: ~860 tokens
- Wire Prompt Tokens (vLLM Tokenizer): 3,347 – 3,418 tokens
- Provider Completion Tokens: 396 – 539 tokens
- Status: **PASSED ADMISSION CONTROL** $\longrightarrow$ Dispatched to Live GPU Inference.

### Prisma SASE Rule Cohort (10 Incidents)
- Compiled System Prompt (Approved Version): ~2,709 tokens
- Model-Facing Incident Telemetry: ~850 – 1,038 tokens
- Wire Prompt Tokens: 3,549 – 3,747 tokens
- Available Input Budget: 3,328 tokens
- Status: **HALTED BY TOKEN_BUDGET_GUARD** $\longrightarrow$ Explicit Preflight Abstention (`CONTEXT_WINDOW_EXCEEDED`).

---

## 3. Strict Evidence Preservation & No Naive Truncation

`TokenBudgetService` strictly refused to naively drop critical security fields (e.g. process arguments, hashes, URLs, or network destinations) to force fit the prompt into 3,328 tokens. 

Preserved fields in all evaluation payloads:
- Process name, command line, parent process lineage
- File hashes (SHA-256, MD5)
- Source and destination IP addresses, ports, protocols
- Security actions (Blocked, Allowed, Quarantined)
- User identity, endpoint hostnames
- Event timestamps and rule condition thresholds

When telemetry cannot fit within context limits without dropping mandatory evidence, the system generates an explicit preflight abstention with `validation_status: CONTEXT_WINDOW_EXCEEDED` and `execution_provenance: TOKEN_BUDGET_GUARD`.
