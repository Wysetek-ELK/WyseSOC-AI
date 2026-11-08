# AI Verdict — Phase 1: Ground-Truth Isolation & Blind-Review Sanitization

**Requirement:** REQ-04  
**Audit Finding:** AV-006 (Ground-Truth Leakage in Blind Review Mode)  
**Status:** **VERIFIED & IMPLEMENTED**  

---

### 1. Threat Model & Vulnerability Analysis

In the pre-Phase 1 audit baseline:
- The Blind Review feature (`GET /api/incidents/{id}?blind_review=true`) is designed to evaluate analyst accuracy and test LLM inference without confirmation bias.
- While the previous implementation removed top-level `ground_truth` and `analyst_verdict` keys from the incident object, it left `raw_payload` and `events[].attributes` untouched.
- If the original SIEM JSON, FortiSIEM incident export, or CSV upload contained nested keys such as `raw_payload.ground_truth`, `raw_payload.analyst_verdict`, or `events[0].attributes["expected_verdict"]`, these keys remained visible in the API response.
- Any frontend component, automated benchmark, or evaluation script consuming the response was susceptible to data leakage and evaluation bias.

---

### 2. Architecture of Implemented Solution

```mermaid
flowchart TD
    Request[GET /api/incidents/{id}?blind_review=true] --> FetchIncident[Fetch Incident & Linked Events from DB]
    FetchIncident --> CheckParam{blind_review == True?}
    CheckParam -- No --> ReturnFull[Return Standard Payload]
    CheckParam -- Yes --> SanitizeTop[Strip Top-Level ground_truth & analyst_verdict]
    SanitizeTop --> RecurseRaw[Recursively Sanitize raw_payload]
    RecurseRaw --> RecurseEvents[Recursively Sanitize Each Event attributes]
    RecurseEvents --> CheckLeakage{Any FORBIDDEN_GROUND_TRUTH_KEYS Remaining?}
    CheckLeakage -- Found --> DeleteKey[Delete Matching Key at Any Nesting Level]
    CheckLeakage -- Clean --> ReturnBlind[Return Sanitized Blind Review Payload]
```

---

### 3. Source Code Modifications

#### `backend/app/services/incident_service.py`
```python
FORBIDDEN_GROUND_TRUTH_KEYS = {
    "ground_truth",
    "analyst_verdict",
    "target_verdict",
    "true_verdict",
    "actual_verdict",
    "ground_truth_label",
    "analyst_label",
    "expected_verdict",
    "historical_verdict",
    "incident_ground_truth",
}

def sanitize_blind_review_payload(data: Any) -> Any:
    """
    Recursively purges ground-truth labels and analyst verdicts from any nested data structure.
    Handles nested dicts, lists, and primitives safely.
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            norm_k = str(k).strip().lower().replace("-", "_").replace(" ", "_")
            if norm_k in FORBIDDEN_GROUND_TRUTH_KEYS or any(fgk in norm_k for fgk in ("ground_truth", "analyst_verdict")):
                continue
            cleaned[k] = sanitize_blind_review_payload(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_blind_review_payload(item) for item in data]
    return data
```

In `IncidentService.get_incident()`:
```python
if blind_review:
    # 1. Strip top-level ground truth and analyst verdict
    inc_dict["ground_truth"] = None
    inc_dict["analyst_verdict"] = None

    # 2. Recursively sanitize raw_payload
    if inc_dict.get("raw_payload"):
        inc_dict["raw_payload"] = sanitize_blind_review_payload(inc_dict["raw_payload"])

    # 3. Recursively sanitize attributes on all events
    if inc_dict.get("events"):
        for evt in inc_dict["events"]:
            if isinstance(evt, dict) and evt.get("attributes"):
                evt["attributes"] = sanitize_blind_review_payload(evt["attributes"])
```

---

### 4. Verification & Testing

Tests implemented in `backend/tests/test_phase1_security_controls.py`:
1. `test_req04_sanitize_blind_review_payload_recursive`:
   - Creates deeply nested structures (e.g. `{"outer": {"nested": {"ground_truth": "TRUE_POSITIVE"}}, "events": [{"analyst_verdict": "FALSE_POSITIVE"}]}`).
   - Runs `sanitize_blind_review_payload(payload)`.
   - Asserts that all nested ground-truth keys are completely removed while legitimate fields (`source_ip`, `event_type`) are preserved.
2. `test_req04_blind_review_endpoint_ground_truth_isolation`:
   - Ingests an incident with ground-truth keys stored inside `raw_payload` and inside an event's `attributes`.
   - Requests `GET /api/incidents/{id}?blind_review=true`.
   - Serializes the entire JSON response to text.
   - Asserts that neither `"analyst_verdict"` nor `"ground_truth"` appear in the output.

