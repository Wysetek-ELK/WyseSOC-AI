# AIS 2.3b.1 — Root Cause Analysis & Runtime Evidence Audit

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.3b.1 (Wire Token Reservation & Semantic Verdict Grounding Integrity)  
**Date:** November 23, 2026  
**Status:** AUDITED & EMPIRICALLY VERIFIED  

---

## 1. Executive Summary

During the AIS 2.3b evaluation phase, empirical evidence captured from live GPU dispatches revealed critical discrepancies in wire token budgeting and claim verification:
1. Dispatched requests to Server 2 GPU (`Qwen/Qwen2.5-7B-Instruct-AWQ` on vLLM) registered **3,370 and 3,371 actual prompt tokens**, violating the mandated $\le 3,328$ wire prompt ceiling.
2. The remaining completion capacity was clamped to **725–726 tokens** by the vLLM runtime, falling short of the required **768-token completion reserve**.
3. A critical validator regression allowed the claim *"The executing binary is not signed"* to be marked as `GROUNDED` solely based on citation of `process.name = UltraViewer_Service.exe`.
4. Telemetry attribute `file.hash_sha256` was marked `PRESENT_VALID` in canonical evidence, while the model rationale hallucinated that the hash was missing without validator detection.
5. Safe preflight fallback abstentions were recorded in evaluation metrics as model-proposed `REQUIRES_ATTENTION` verdicts despite zero LLM inference taking place.

This audit details the verified root causes of all seven integrity discrepancies before code remediation.

---

## 2. Comprehensive Investigation of the Seven Runtime Discrepancies

### 2.1 Discrepancy 1: Actual Wire Prompt Tokens (3,370 & 3,371 vs 3,328 Ceiling)
- **Observed Behavior:** Dispatched live requests for CrowdStrike incidents `132438483` and `132527297` consumed 3,370 and 3,371 prompt tokens on the vLLM engine, exceeding the configured 3,328 limit by 42–43 tokens.
- **Root Cause:**
  1. The platform's internal token budget service relied on a generic `cl100k_base` estimation heuristic which under-calculated token lengths for structured JSON keys, technical file paths, and hexadecimal strings compared to Qwen2.5's vocabulary.
  2. The budgeting calculation omitted the physical wire encapsulation overhead: the Qwen chat template tags (`<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>\n<|im_start|>assistant\n`) totaling **61 tokens**, plus XML boundary tags `<UNTRUSTED_INCIDENT_DATA>...</UNTRUSTED_INCIDENT_DATA>` (~25 tokens).
  3. Consequently, a prompt budgeted internally at 3,253 tokens arrived on the wire at 3,370 tokens.

### 2.2 Discrepancy 2: Available Completion Capacity (725–726 vs 768 Reserve)
- **Observed Behavior:** Dispatched requests had only 725–726 tokens of available generation space instead of the mandated 768 tokens.
- **Root Cause:**
  - The hardware vLLM container on Server 2 was launched with `--max-model-len 4096`.
  - When prompt tokens reached 3,370 on the wire, the physical remaining headroom inside the 4,096-token context window was strictly:
    $$\text{Available Headroom} = 4096 - 3370 = 726 \text{ tokens}$$
  - Because prompt tokens exceeded 3,328, the 768 completion reserve was compromised.

### 2.3 Discrepancy 3: Local Tokenizer vs Qwen2.5 Chat-Template Calibration
- **Observed Behavior:** Token counts produced by the local tokenizer differed from vLLM usage by up to 45 tokens.
- **Root Cause:**
  - The local `ModelTokenizerService` lacked direct calibration against the Qwen2.5 ChatML template format. It counted user and system text as raw concatenations, ignoring the specific BOS/EOS tokens, role headers, and newline separators injected by vLLM's Jinja chat template.
  - Verification with the calibrated BPE subword tokenizer demonstrated that when ChatML delimiters (+61 tokens) are factored in, local counts match vLLM's tokenizer exactly to within $\pm 1$ token.

### 2.4 Discrepancy 4: Provider-Side Max Tokens Clamping
- **Observed Behavior:** When a client requested `max_tokens=768` with a prompt of 3,370 tokens, vLLM did not reject the request with HTTP 400; instead, it silently clamped `max_tokens` to `4096 - 3370 = 726`.
- **Root Cause:**
  - Standard vLLM OpenAI-compatible API servers dynamically adjust `max_tokens = min(requested_max_tokens, max_model_len - prompt_tokens)` to avoid immediate 400 errors.
  - While this prevented crash loops, it silently violated the platform invariant that 768 tokens of completion headroom must be guaranteed.

### 2.5 Discrepancy 5: False Grounding of "Executing binary is not signed" on `process.name`
- **Observed Behavior:** In Incident `132527297`, the model generated the claim *"The executing binary is not signed."* citing evidence ID for `process.name` (`UltraViewer_Service.exe`). The validator marked this claim as `GROUNDED` (`grounding_status = "GROUNDED"`).
- **Root Cause:**
  - In `ModelClaimExtractor._ground_claims()`, citation verification performed purely string/identifier matching: it checked if the cited evidence ID existed and whether the field name or asserted value (`"UltraViewer_Service.exe"`) matched the telemetry record.
  - The extractor completely ignored the **claim text predicate** (`"not signed"`). The telemetry record contained only the binary name, with zero digital signature verification or certificate status.
  - This allowed the model to assert an unverified negative forensic property ("not signed") while citing an unrelated factual field ("process name").

### 2.6 Discrepancy 6: Telemetry SHA256 Marked PRESENT_VALID While Rationale Claimed Missing
- **Observed Behavior:** Telemetry for `132438483` contained canonical record `file.hash_sha256 = "10ff43f2d4a991c83caefce1c4442fa95258d0d93f168dde339f52322aa371e9"` marked `PRESENT_VALID`. However, the model reasoning asserted: *"Missing process.parent_command_line and file.hash_sha256. Additional evidence is required..."* The validator accepted this without detecting a contradiction.
- **Root Cause:**
  - The model hallucinated that the hash was missing because `events[0].attributes` was verbose and CrowdStrike telemetry nested the hash under `"SHA256 Hash"`.
  - The validator lacked a cross-examination step between the model's natural language `reason` string and the preflight `field_validation_status`. When a model explicitly justifies its verdict by alleging that a field is absent, but canonical telemetry proves that field is present and valid, an `EVIDENCE_CONTRADICTION` must be raised.

### 2.7 Discrepancy 7: Preflight Abstentions Represented as Model Verdicts
- **Observed Behavior:** The 3 Prisma SASE incidents (`132499009`, `132499023`, `132499745`) aborted at preflight due to context overflow (>6,000 tokens). In benchmark reporting, these were classified under `model_proposed_attention_count` as model-proposed `REQUIRES_ATTENTION`.
- **Root Cause:**
  - `verdict_pipeline.py` early exits populated `proposed_verdict: "REQUIRES_ATTENTION"` by default.
  - This conflated safe system-level preflight abstentions with model-generated inference outputs, distorting empirical evaluation metrics.

---

## 3. Remediation Matrix

| Defect # | Discrepancy | Root Cause | Target Module | Resolution Strategy |
| :---: | :--- | :--- | :--- | :--- |
| **D1 & D3** | Wire tokens exceeded 3,328 cap | ChatML template omitted; BPE tokenizer not calibrated | `tokenizer_service.py`, `token_budget_service.py` | Add `count_wire_prompt_tokens` with +61 template overhead and exact ChatML framing. |
| **D2 & D4** | Completion capacity clamped to < 768 | Over-budget prompts reached vLLM | `openai_compatible.py`, `token_budget_service.py` | Enforce 3,328 prompt cap at budget time; pre-dispatch guard blocks > 3,328 with `CONTEXT_WINDOW_EXCEEDED`. |
| **D5** | Unsigned binary claim grounded on filename | Extractor only checked value matching, not predicate | `model_claim_extractor.py`, `independent_verdict_validator.py` | Implement `verify_semantic_predicate`: validate digital signature, reputation, and authorization predicates. |
| **D6** | SHA256 contradiction uncaught | Validator did not cross-examine negative assertions | `independent_verdict_validator.py` | Add Check 4e: regex cross-examination of model reasoning against canonical evidence status. |
| **D7** | Preflight fallback marked as model verdict | Pipeline initialized `proposed_verdict` to attention | `verdict_pipeline.py`, `empirical_benchmark_harness.py` | Set `proposed_verdict: None` for preflight exits; separate dispatched vs abstained metrics. |

---

## 4. Conclusion

All seven runtime integrity discrepancies have been traced to concrete implementation defects in token accounting, claim verification, and lifecycle classification. The remediations defined in Stages 2 through 5 directly resolve each issue without modifying system architecture, database schemas, or detection policies.
