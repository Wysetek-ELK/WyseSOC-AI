# 04 — Confidence Normalization & Scale Validation Specification

**Module:** `backend/app/services/confidence_normalizer.py`  
**Integration:** `backend/app/services/model_provider/openai_compatible.py`, `backend/app/services/independent_verdict_validator.py`  
**Status:** Deployed and Validated Live on Server 1  

---

## 1. Context & Motivation

In previous iterations, the local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) frequently emitted confidence as a decimal fraction between `0.0` and `1.0` (such as `0.9` or `0.95`). However:
1. The enterprise schema defined confidence as `0.0` to `100.0`.
2. A raw number `0.9` without scale metadata is mathematically ambiguous: does it indicate a confidence of `0.9%` (an extremely tentative assessment) or `90.0%` (a high-certainty assessment)?
3. Silently multiplying decimal numbers by `100` can create false certainty and mask model non-compliance with the prompt contract.

AIS 2.0 V8.2 introduces the **`ConfidenceNormalizer`** to enforce mathematical rigor, explicit scale declarations, and auditability.

---

## 2. Confidence Normalization Contract

```mermaid
flowchart TD
    A["Raw Model Confidence Output"] --> B["ConfidenceNormalizer"]
    B --> C{"Is None / Empty?"}
    C -->|Yes| D["Set to 0.0%\nScale: NOT_SPECIFIED"]
    C -->|No| E{"Check Bounds & Types"}
    E -->|NaN / Inf / Negative / >100| F["Reject as INVALID_CONFIDENCE\nScale: INVALID\nNormalized: 0.0%"]
    E -->|Valid Number| G{"Is Value == 0.0?"}
    G -->|Yes| H["Set to 0.0%\nScale: ZERO"]
    G -->|No| I{"Is Value in (0.0, 1.0]?"}
    I -->|Yes| J{"Is confidence_scale declared?"}
    J -->|Declared PROBABILITY_0_1| K["Multiply by 100.0\nScale: PROBABILITY_0_1\nValid: True"]
    J -->|Declared PERCENT_0_100| L["Keep as 0.X%\nScale: PERCENT_0_100\nValid: True"]
    J -->|Undeclared / None| M["REJECT as AMBIGUOUS_SCALE_REJECTED\nValid: False\nNormalized: 0.0%"]
    I -->|No (Value > 1.0 and <= 100.0)| N["Scale: PERCENT_0_100\nValid: True\nNormalized: Value%"]
```

### Scale Specifications:
- **`PERCENT_0_100`:** Value is an explicit percentage between `0.0` and `100.0`.
- **`PROBABILITY_0_1`:** Value is a mathematical probability between `0.0` and `1.0`, converted to percentage by `val * 100.0`.
- **`AMBIGUOUS_SCALE_REJECTED`:** Value is in `(0.0, 1.0]` without an explicit `confidence_scale` attribute in the model's JSON response.

---

## 3. Policy Compiler Section 11 Contract Hardening

To ensure the model complies with scale requirements, Section 11 of the compiled prompt was updated in `policy_compiler_service.py`:

```json
{
  "incident_id": "string",
  "rule_id": "string",
  "verdict": "TRUE_POSITIVE | FALSE_POSITIVE | REQUIRES_ATTENTION",
  "confidence": 0.0 to 100.0,
  "confidence_scale": "PERCENT_0_100",
  "reason": "Clear 1-3 sentence factual justification grounded in evidence...",
  ...
}
```

---

## 4. Live Verification in V8.2 Real GPU Benchmark

During the full 6-incident evaluation on Server 1 (`run_id = 2074b011-9fe8-46fb-9937-ff5ead18fc61`):
- In **`#176011`**, the model returned:
  ```json
  "confidence": 95.0,
  "confidence_scale": "PERCENT_0_100"
  ```
  `ConfidenceNormalizer` validated this cleanly:
  - `normalized_percent`: `95.0`
  - `confidence_scale`: `"PERCENT_0_100"`
  - `is_valid`: `True`
  - `validation_error`: `None`
- In **`#176122`** and **`#167157`** (abstentions), the model cleanly emitted:
  ```json
  "confidence": 0.0,
  "confidence_scale": "PERCENT_0_100"
  ```
  Validated cleanly as `0.0%`.

---

## 5. Decoupling from Empirical Ground Truth

> [!IMPORTANT]
> A high model confidence (e.g. `95.0%`) represents the **model's subjective certainty**, NOT verified empirical accuracy.
> In `#176011`, the model asserted `95.0%` confidence on an invalid `TRUE_POSITIVE` proposal that was rejected by `ReasoningIntegrityEngine`.
> AIS 2.0 strictly maintains this architectural firewall: model confidence is recorded for calibration audit trails, but is NEVER used as a proxy for empirical ground-truth accuracy.
