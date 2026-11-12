# WyseSOC AI — Evidence Validation Engine Fix

**Document:** `06_EVIDENCE_VALIDATION_ENGINE_FIX.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Affected Components:** `ModelClaimExtractor` (`backend/app/services/model_claim_extractor.py`), `EvidencePreflightValidator` (`backend/app/services/evidence_preflight_validator.py`), `IndependentVerdictValidator` (`backend/app/services/independent_verdict_validator.py`)  
**Status:** IMPLEMENTED, TESTED & VERIFIED  

---

## 1. Audit Findings and Deficiencies

The validation engine serves as the core trustworthiness barrier between the generative LLM and operational SOC decisions. The audit uncovered three primary validation defects:

1. **Primitive String Comparison for Structured Telemetry:**
   Evidence values were evaluated using strict Python string equality (`str(asserted).strip() == str(observed).strip()`). This caused spurious validation rejections:
   - Integer status codes (`200`) failed to match string status codes (`"200"`).
   - Equivalent IP addresses with CIDR notations or IPv4-mapped representations failed.
   - URLs differing only by trailing root slashes (e.g. `https://media4.giphy.com/` vs `https://media4.giphy.com`) failed.
   - Case differences in HTTP methods (`"GET"` vs `"get"`) or actions (`"BLOCKED"` vs `"blocked"`) failed.

2. **Conflation of Missing Data with Ingestion / Mapping Failures:**
   Prior to remediation, any field not found in canonical evidence was marked as `MISSING_EVIDENCE`. The system could not distinguish whether the field was never emitted by the firewall (e.g. HTTP method on blocked HTTPS connection), whether the parser failed to extract it, or whether it was omitted due to token budget compaction.

3. **Inappropriate Fall-Through in URL Matching:**
   A partial URL substring matching fallback caused security hazards (e.g., path traversal attempts like `https://example.com/../../etc/passwd` incorrectly matching `https://example.com/`).

---

## 2. Implemented Remediation

### 2.1 Type-Aware Evidence Comparison (`compare_evidence_values`)
Implemented in `backend/app/services/model_claim_extractor.py`:

```python
def compare_evidence_values(field: str, asserted: Any, observed: Any) -> bool:
    if asserted is None or observed is None:
        return asserted is observed
    
    # Direct equality
    if asserted == observed or str(asserted).strip() == str(observed).strip():
        return True

    # 1. IP Address Normalization
    if "ip" in field.lower():
        try:
            a_ip = ipaddress.ip_network(str(asserted).strip(), strict=False)
            o_ip = ipaddress.ip_network(str(observed).strip(), strict=False)
            if a_ip == o_ip or a_ip.subnet_of(o_ip) or o_ip.subnet_of(a_ip):
                return True
        except ValueError:
            pass

    # 2. HTTP Status Code Normalization (Integer vs String)
    if "status" in field.lower():
        try:
            if int(str(asserted).strip()) == int(str(observed).strip()):
                return True
        except (ValueError, TypeError):
            pass

    # 3. HTTP Method Normalization (Case-Insensitive)
    if "method" in field.lower():
        return str(asserted).strip().upper() == str(observed).strip().upper()

    # 4. URL Normalization (Preserve Security Critical Paths/Query)
    if "url" in field.lower() or "uri" in field.lower():
        try:
            a_url = urlparse(str(asserted).strip())
            o_url = urlparse(str(observed).strip())
            if a_url.netloc.lower() == o_url.netloc.lower() and a_url.scheme.lower() == o_url.scheme.lower():
                a_path = a_url.path.rstrip('/') or '/'
                o_path = o_url.path.rstrip('/') or '/'
                if a_path == o_path and a_url.query == o_url.query:
                    return True
        except Exception:
            pass
        return False

    # 5. Case-Insensitive String Comparison (Category, Action, Hostname)
    return str(asserted).strip().lower() == str(observed).strip().lower()
```

### 2.2 The Eight Canonical Validation States
The validation subsystem establishes 8 distinct, deterministic validation states:

| Validation State | Definition | Impact on Verdict |
|---|---|---|
| `PRESENT_VALID` | Telemetry present in source, correctly normalized, and validated. | Supports decisive verdict. |
| `NOT_IN_SOURCE` | Telemetry was genuinely not emitted by sensor/firewall. | Evaluated against archetype conditional rules. |
| `NOT_MAPPED` | Telemetry present in raw event, but lacked canonical mapping. | Surfaces mapping alert; does not penalize model. |
| `CONTEXT_OMITTED` | Telemetry normalized, but excluded by token compaction. | Flagged as budget constraint. |
| `EVIDENCE_VALUE_MISMATCH` | Model asserted value contradicts observed telemetry. | Rejects claim; triggers `REQUIRES_ATTENTION`. |
| `FIELD_CONFLICT` | Different source events report conflicting telemetry. | Preserves conflict; blocks automated decision. |
| `CLAIM_UNGROUNDED` | Model asserts a fact not present in any evidence line. | Neutralizes claim; penalizes grounding ratio. |
| `CRITERIA_UNSATISFIED` | Model proposed verdict without fulfilling gating criteria. | Reverts verdict to `REQUIRES_ATTENTION`. |

---

## 3. Automated Test Verification

| Test ID | Scenario | Verification Method | Status |
|---|---|---|---|
| **T10** | Model value differs from source | Mismatched IP detected and rejected | PASS |
| **T11** | HTTP status string vs integer | Evaluated `status="200"` against observed `200` $\to$ Matched | PASS |
| **T14** | Genuine insufficient evidence | Model safely abstains with `REQUIRES_ATTENTION` | PASS |
| **T21** | URL normalization edge cases | Verified scheme/host normalization without path traversal leakage | PASS |
