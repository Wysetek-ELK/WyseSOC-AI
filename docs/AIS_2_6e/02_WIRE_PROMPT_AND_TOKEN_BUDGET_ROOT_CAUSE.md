# AIS 2.6e — Workstream 2: Wire Prompt and Token Budget Root Cause Report

**Phase:** AIS 2.6e  
**Evaluated At:** 2026-11-24T17:10:00Z  
**Document Identity:** `docs/AIS_2_6e/02_WIRE_PROMPT_AND_TOKEN_BUDGET_ROOT_CAUSE.md`  
**Referenced Manifests:**  
- [TOKEN_ACCOUNTING_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/TOKEN_ACCOUNTING_RESULTS.json)
- [WIRE_PROMPT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/WIRE_PROMPT_MANIFEST.json)
- [CONTEXT_OVERFLOW_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CONTEXT_OVERFLOW_REGISTER.json)

---

## 1. Technical Root Cause of the AIS 2.6d Contradiction

During the audit of AIS 2.6d artifacts, an explicit contradiction was identified:
- The narrative report asserted that all 20 incident prompts fit comfortably inside the 8,192 context window.
- The machine-readable artifact `TOKEN_ACCOUNTING_RESULTS.json` reported that all 20 incidents experienced context overflows, with prompts exceeding 73,000 tokens.

Forensic examination of `test_wire_prompts.py` revealed that the audit measurement script:
1. Deserialized raw event lists containing up to 143 full event records per incident.
2. Formatted all canonical evidence records with non-reasoning forensic hashes, internal digests, and verbose field metadata.
3. Computed the token count of this **unbudgeted raw dump** directly via `TokenBudgetService.estimate_tokens(user_content)`.
4. **Completely bypassed** the production token budgeting method `TokenBudgetService.budget_prompt()`.

In the actual Verdictum AI inference engine (`EmpiricalBenchmarkHarness.evaluate_single_incident()`), the harness calls `TokenBudgetService.budget_prompt()`, which executes deterministic compaction.

---

## 2. Authoritative Token Accounting Results

Using the exact production `TokenBudgetService.budget_prompt()` implementation with the calibrated Qwen2.5 subword tokenizer:
- **Maximum Context Capacity:** 8,192 tokens
- **Reserved Completion Headroom:** 768 tokens
- **Effective Maximum Input Budget:** 7,424 tokens

### Cohort Summary Table

| Metric | Mode A (Neutral Baseline) | Mode B (Approved Policy) |
| :--- | :---: | :---: |
| **Minimum Prompt Tokens** | 2,262 tokens (Incident `132499745`) | 2,454 tokens (Incident `132499745`) |
| **Maximum Prompt Tokens** | 5,874 tokens (Incident `132461358`) | 6,680 tokens (Incident `132461358`) |
| **Average Prompt Tokens** | 3,415 tokens | 4,022 tokens |
| **Minimum Headroom Tokens** | 1,550 tokens | 744 tokens |
| **Overflow Count** | **0 of 20 (0%)** | **0 of 20 (0%)** |
| **Admission Invariant Status** | **PASS (100% Fit)** | **PASS (100% Fit)** |

All 20 incidents under both Mode A and Mode B fit within the 7,424 input budget with substantial headroom, completely disproving the hypothesis that prompts would truncate or overflow on the wire.

---

## 3. Delimiter Overhead and Chat Template Accounting

The wire prompts account for:
- Qwen2.5 / vLLM Chat Template special tokens: `<|im_start|>system\n ... <|im_end|>\n<|im_start|>user\n ... <|im_end|>\n<|im_start|>assistant\n` (61 tokens overhead).
- Untrusted data enclosures: `<UNTRUSTED_INCIDENT_DATA>\n ... \n</UNTRUSTED_INCIDENT_DATA>`.
- Internal closing tag neutralization: Any closing XML tags within raw log content are escaped to `&lt;/UNTRUSTED_INCIDENT_DATA&gt;`.

The verified input budget of 7,424 tokens guarantees that even the largest Mode B prompt (6,680 tokens) maintains 744 tokens of headroom before reaching the input ceiling, ensuring the model's full 768 completion budget is strictly preserved without risking truncation.
