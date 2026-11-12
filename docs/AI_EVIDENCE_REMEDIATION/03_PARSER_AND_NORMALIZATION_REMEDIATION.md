# WyseSOC AI — Parser and Field Normalization Remediation

**Document:** `03_PARSER_AND_NORMALIZATION_REMEDIATION.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Affected Service:** `EvidenceNormalizationService` (`backend/app/services/evidence_normalization_service.py`)  
**Status:** IMPLEMENTED, TESTED & VERIFIED  

---

## 1. Audit Findings and Deficiencies

Prior to remediation, `EvidenceNormalizationService` exhibited five critical limitations when processing security events from enterprise SIEM platforms (such as FortiSIEM and FortiGate UTM):

1. **Space-Separated and Formatted Key Fragility:**
   FortiSIEM parses vendor logs into human-readable keys with spaces and capitalization (e.g., `"Source IP"`, `"Destination IP"`, `"Web Site Category"`, `"Action"`). The existing normalization dictionary (`FIELD_MAPPINGS`) only indexed lowercase, unspaced keys. As a result, the lookup failed and fell through to a naive fallback heuristic that converted `"Source IP"` into `telemetry.source ip`, completely missing canonical schema recognition.

2. **Absence of Syslog Key-Value Tokenizer:**
   Security sensors (e.g. FortiGate, Palo Alto Networks, Check Point) emit structured key-value pairs inside `raw_log` or `rawMessage` (e.g. `srcip=192.0.2.48 dstip=198.51.100.32 service="HTTPS" url="https://media4.giphy.com/" catdesc="Entertainment" action="blocked"`). When the SIEM pre-parser dropped or failed to extract these attributes into `parsed_details`, the backend had no mechanism to parse the raw syslog string.

3. **Inconsistent Canonical Path Mapping:**
   The key `"url"` was mapped to `web.url`, whereas the canonical evidence catalog, archetype validator, and detection rules standardized on `http.url`.

4. **Missing Category and Action Mappings:**
   Enterprise web filtering fields (`webCategory`, `catdesc`, `Web Site Category`, `action`, `act`, `disposition`) were absent from `FIELD_MAPPINGS`. These attributes were silently dropped during normalization.

5. **Omission of Top-Level Incident Fallback Telemetry:**
   When an incident had linked event records, the ingestion pipeline skipped top-level incident fields (`incidentSrc`, `incidentTarget`, `incidentRptIp`, `incidentRptDevName`). If individual event records lacked network endpoints, this critical incident context was lost.

---

## 2. Implemented Remediation

### 2.1 Syslog Key-Value Regex Extractor
Added a high-performance regex tokenizer to extract key-value pairs from raw syslog strings:
```python
KV_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')

def parse_key_value_string(text: str) -> dict[str, str]:
    if not text:
        return {}
    results = {}
    for match in KV_PATTERN.finditer(text):
        key = match.group(1)
        val = match.group(2) if match.group(2) is not None else match.group(3)
        results[key] = val.strip()
    return results
```

### 2.2 Attribute Key Sanitization
Implemented `clean_attr_key(key)` to sanitize attribute names prior to lookup, eliminating sensitivity to spaces, dots, hyphens, and casing:
```python
def clean_attr_key(key: str) -> str:
    return re.sub(r'[\s\.\-_]', '', key).lower()
```
Examples:
- `"Source IP"` $\to$ `"sourceip"`
- `"web_category"` $\to$ `"webcategory"`
- `"HTTP-Status-Code"` $\to$ `"httpstatuscode"`

### 2.3 Comprehensive Canonical Field Dictionary
Expanded `FIELD_MAPPINGS` to encompass all enterprise SIEM variations:

```python
FIELD_MAPPINGS: dict[str, str] = {
    # Network Source Endpoints
    "source_ip": "network.source_ip",
    "src_ip": "network.source_ip",
    "srcip": "network.source_ip",
    "sourceip": "network.source_ip",
    "src": "network.source_ip",
    "client_ip": "network.source_ip",
    
    # Network Destination Endpoints
    "destination_ip": "network.destination_ip",
    "dest_ip": "network.destination_ip",
    "dstip": "network.destination_ip",
    "destinationip": "network.destination_ip",
    "dst": "network.destination_ip",
    "server_ip": "network.destination_ip",
    
    # HTTP & Web Filtering
    "url": "http.url",
    "request_url": "http.url",
    "requesturl": "http.url",
    "uri": "http.url",
    "http_url": "http.url",
    "target_url": "http.url",
    "webcategory": "webCategory",
    "catdesc": "webCategory",
    "websitecategory": "webCategory",
    "urlcategory": "webCategory",
    "category": "webCategory",
    "http_method": "http.method",
    "httpmethod": "http.method",
    "method": "http.method",
    "request_method": "http.method",
    "http_status_code": "http.status_code",
    "httpstatuscode": "http.status_code",
    "httpstatus": "http.status_code",
    "status_code": "http.status_code",
    "statuscode": "http.status_code",
    
    # Security Action & Disposition
    "action": "security.action",
    "act": "security.action",
    "disposition": "security.action",
    "firewall_action": "security.action",
    "security_action": "security.action",
}
```

### 2.4 Provenance and Transformation Tracking
Updated `CanonicalEvidenceRecord` in `backend/app/schemas/canonical_evidence.py` to record transformation provenance:
- `raw_field_name`: Exact original key name in raw source.
- `transformation`: Type of extraction applied (`DIRECT`, `ALIASED`, `KEY_VALUE_EXTRACTED`).
- `validation_status`: Initial normalization verification state.

### 2.5 Unmapped Attribute Preservation
Any source attribute that cannot be confidently mapped to the canonical schema is preserved in `unmapped_fields` on `EvidenceNormalizationResult`. This provides complete visibility to analysts without corrupting canonical telemetry.

---

## 3. Automated Test Verification

| Test ID | Scenario | Input Fixture | Result |
|---|---|---|---|
| **T01** | Canonical schema recognition | `{"network.source_ip": "192.0.2.1"}` | PASS (Recognized with `DIRECT` provenance) |
| **T02** | Alias normalization | `{"srcip": "192.0.2.48", "dstip": "198.51.100.32"}` | PASS (Resolved to canonical paths) |
| **T03** | Nested JSON extraction | `{"network": {"source": {"ip": "192.0.2.5"}}}` | PASS (Traversed dot-path correctly) |
| **T04** | Flattened JSON & raw syslog | `srcip=192.0.2.48 catdesc="Entertainment"` | PASS (Syslog KV tokenizer extracted all fields) |
| **T05** | Missing source field | Omitted field from payload | PASS (Marked `NOT_IN_SOURCE`) |
| **T06** | Unmapped field transparency | `{"custom_app_metric": 992}` | PASS (Preserved in `unmapped_fields`, status `NOT_MAPPED`) |
| **T12** | Conflicting event values | Multiple events with distinct source IPs | PASS (Conflict preserved without overwriting) |
| **T23** | Mapping collision prevention | Specific `src_ip` vs generic `ip` | PASS (Deterministic precedence enforced) |
| **T24** | Multi-event provenance | Aggregated events with distinct IDs | PASS (Correct event ID linkage) |
| **T25** | Malformed source telemetry | Corrupted JSON and unparseable syslog | PASS (Graceful degradation without exceptions) |
