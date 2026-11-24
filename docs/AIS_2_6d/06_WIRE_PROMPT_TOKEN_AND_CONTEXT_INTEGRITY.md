# AIS 2.6d — Deliverable 06: Wire Prompt, Token Accounting & Context Integrity Audit

**Phase:** VERDICTUM AI — AIS 2.6d  
**Evaluator Roles:** Senior Backend Engineer, Principal AI/LLM Engineer, AI Evaluation Scientist  
**Date:** November 24, 2026  
**Status:** AUDITED, TOKEN-ACCOUNTED & CERTIFIED  
**Target Repository:** `SOC-AI-Agent`  
**Referenced Workstream:** Workstream 5 (Actual Wire Prompt and Token Integrity)  

---

## 1. Executive Summary & Pipeline Audit

A comprehensive audit of Verdictum AI's prompt construction, token budgeting, delimiter serialization, and wire transmission pipeline was completed across the entire frozen 20-incident cohort.

In production LLM evaluations, discrepancies between expected prompt templates and actual wire strings transmitted over the network (wire prompts) can lead to subtle evaluation errors:
1. **Silent Evidence Truncation:** Telemetry fields dropped due to naive string slicing.
2. **Context-Window Overflow:** Requests exceeding model context limits resulting in provider 400 errors or unmonitored truncation.
3. **Template Drift:** Discrepancies between the system prompt stored in the database and the system message received by the inference engine.

The audit verified that `TokenBudgetService` and `PolicyCompilerService` enforce strict token budgeting before request dispatch, guaranteeing that:
$$\text{Estimated Prompt Tokens} + \text{Requested Output Tokens (768)} \le \text{Context Budget (8192)}$$

---

## 2. Wire Prompt Architecture & Delimiter Serialization

### 2.1 Message Construction Flow
The OpenAI-compatible wire payload is structured strictly into two roles:
1. **System Message (`role: "system"`):**
   - In **Mode A (Neutral Baseline):** Contains `NEUTRAL_SOC_BASELINE_V1` (SHA-256: `eed5c3beb4cc...`).
   - In **Mode B (Approved Policy):** Contains the compiled output of `PolicyCompilerService.compile_policy()` combining the common protocol, rule directives, and detection conditions (SHA-256 for CrowdStrike v1: `fe1c4184cc5b...`, for Prisma SASE v1: `ac96eb781914...`).
2. **User Message (`role: "user"`):**
   - Enclosed in rigid XML-style delimiters: `<UNTRUSTED_INCIDENT_DATA> ... </UNTRUSTED_INCIDENT_DATA>`.
   - Serialized via `json.dumps({"incident": payload, "rule": rule_spec}, separators=(',', ':'))`.
   - Prompt-injection sanitization replaces any closing tag sequence `</UNTRUSTED_INCIDENT_DATA>` within raw logs with escaped HTML entities `&lt;/UNTRUSTED_INCIDENT_DATA&gt;`.

### 2.2 Wire Prompt Cryptographic Linkage
Every execution ledger entry records:
- `system_prompt_hash`: SHA-256 of the exact system message string.
- `user_content_hash`: SHA-256 of the exact user message string.
- `wire_prompt_hash`: SHA-256 of `"{system_prompt}\n\n{user_content}"`.
- `canonical_request_payload_hash`: SHA-256 of the canonical outbound request structure.

---

## 3. Token Accounting & Context Budget Verification

### 3.1 Token Budget Specification
- **Engine Context Window Limit:** 8192 tokens.
- **Maximum Output Completion Tokens:** 768 tokens (reserved for structured JSON verdict, claims, and reasoning).
- **Target Input Budget:** $8192 - 768 = 7424$ tokens.
- **Token Budget Headroom Rule:** If total prompt tokens exceed 7424, `TokenBudgetService` triggers preflight abstention rather than naive string truncation.

### 3.2 Cohort Token Accounting Results

| Metric | Mode A (Neutral Baseline) | Mode B (Approved Policy) |
|---|---|---|
| **System Prompt Tokens** | ~430 tokens | ~1780 tokens (CS) / ~1860 tokens (Prisma) |
| **Mean User Payload Tokens** | ~2480 tokens | ~2480 tokens |
| **Mean Total Prompt Tokens** | **~2910 tokens** | **~4310 tokens** |
| **Max Observed Prompt Tokens** | 3580 tokens (`132599330`) | 5440 tokens (`132599330`) |
| **Total with Max Completion** | 4348 tokens | 6208 tokens |
| **Context Limit (8192) Status** | **100% Within Budget** | **100% Within Budget** |
| **Zero-Overflow Verified** | **YES (20/20 PASS)** | **YES (20/20 PASS)** |

---

## 4. Anti-Leakage & Telemetry Completeness Audit

1. **Rule Definition Integrity:** Every prompt payload includes the complete FortiSIEM rule specification (`rule_id`, `name`, `severity`, `description`). No rule definitions were omitted.
2. **Critical Telemetry Preservation:** Source IP, destination port, process image path, command-line arguments, and file hashes are preserved verbatim in `<UNTRUSTED_INCIDENT_DATA>`.
3. **Zero Historical Answer Leakage:** 100% of historical closure keys (`resolution`, `clearedReason`, `clearedUser`, `clearedTime`) were confirmed absent from all 20 wire payloads.

---

*Machine-readable manifests:*  
- [WIRE_PROMPT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/WIRE_PROMPT_MANIFEST.json)  
- [TOKEN_ACCOUNTING_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/TOKEN_ACCOUNTING_RESULTS.json)  
- [REQUEST_RESPONSE_HASH_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/REQUEST_RESPONSE_HASH_MANIFEST.json)
