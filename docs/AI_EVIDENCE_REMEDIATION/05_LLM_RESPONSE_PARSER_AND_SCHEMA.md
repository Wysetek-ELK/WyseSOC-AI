# WyseSOC AI — LLM Response Parser and Schema Audit

**Document:** `05_LLM_RESPONSE_PARSER_AND_SCHEMA.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Affected Components:** `ModelClaimExtractor` (`backend/app/services/model_claim_extractor.py`), `VerdictPipeline` (`backend/app/services/verdict_pipeline.py`)  
**Status:** IMPLEMENTED, TESTED & VERIFIED  

---

## 1. Audit Findings

Server 2 serves `Qwen/Qwen2.5-7B-Instruct-AWQ` via vLLM with JSON mode enabled (`response_format={"type": "json_object"}`). The audit evaluated the schema contract, parsing mechanisms, and claim extraction:

1. **Structured Output Contract:**
   The model must return a JSON object containing:
   - `verdict`: Final determination (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`).
   - `proposed_verdict`: Model's initial hypothesis before independent validation gating.
   - `confidence`: Numerical score between `0.0` and `1.0`.
   - `reason`: Detailed analytical rationale justifying the decision.
   - `supporting_evidence`: List of specific telemetry claims citing evidence IDs (`EV-...`).
   - `analyst_questions`: Recommended follow-up questions for SOC analysts.

2. **Parser Vulnerabilities Identified:**
   - **Markdown Code Block Wrapping:** Certain vLLM configurations wrapped JSON output in markdown formatting (````json ... ````). Direct JSON decoding raised exceptions unless stripped.
   - **Claim Extraction Fragility:** Model reasoning containing statements such as `"The source IP is 192.0.2.48"` was evaluated by string exact-matching. If the evidence recorded `"192.0.2.48/32"` or if whitespace differed, the claim was flagged as ungrounded.
   - **Mismatched Evidence ID Citations:** In Incident #176061, the model cited `EV-176061-TOP-event_timestamp` when asserting an IP address equality claim, causing `EVIDENCE_VALUE_MISMATCH`.

---

## 2. Implemented Remediation

### 2.1 Robust JSON Extraction & Markdown Sanitization
In `VerdictPipeline._parse_llm_response`:
```python
def extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Fallback regex extraction for embedded JSON objects
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise exc
```

### 2.2 Model Claim Extraction Subsystem
`ModelClaimExtractor` parses claims from both `reason` and `supporting_evidence`:
1. **Identifier Matching:** Extracts cited evidence identifiers matching `r'EV-[A-Za-z0-9_\-\.]+'`.
2. **Entity Extraction:** Extracts IP addresses, URLs, HTTP status codes, web categories, and actions using dedicated regex extractors.
3. **Evidence Linkage:** Pairs asserted values with observed values from the canonical evidence store.
4. **Diagnostic Error Categorization:** When a claim cites an evidence ID corresponding to a different field type (e.g. citing an event timestamp for an IP address), the extractor specifically flags `FIELD_TYPE_MISMATCH` rather than a generic mismatch.

### 2.3 Safe Abstention on Malformed Output
If the LLM returns unparseable or incomplete JSON, the pipeline catches the error gracefully:
- Fallback verdict: `REQUIRES_ATTENTION`
- Confidence: `0.0%`
- Reason code: `MALFORMED_LLM_RESPONSE`
- Disposition: Preserves incident safety and routes to analyst review.

---

## 3. Automated Test Verification

| Test ID | Scenario | Verification Method | Status |
|---|---|---|---|
| **T08** | Valid evidence and model response | Grounded claims citing valid evidence IDs | PASS |
| **T09** | Hallucinated model evidence | Model cites non-existent IP `203.0.113.99` $\to$ Rejected with `CLAIM_UNGROUNDED` | PASS |
| **T10** | Value mismatch detection | Model asserts IP `192.0.2.2` when source is `192.0.2.1` $\to$ Flagged `EVIDENCE_VALUE_MISMATCH` | PASS |
| **T19** | Malformed LLM JSON response | Incomplete and markdown-wrapped responses $\to$ Handled safely without crash | PASS |
