# AI VERDICT — PHASE 2: EVIDENCE NORMALIZATION
## 02. CANONICAL EVIDENCE NORMALIZATION (P2-REQ-01)

---

### 1. Purpose & Motivation
SIEM telemetry arrives in heterogeneous, vendor-specific formats (e.g. FortiSIEM raw events, syslog, JSON attributes). Different rules and devices use varying keys for the same conceptual telemetry: `cmdline` vs `processcommandline` vs `command`, `srcip` vs `src_ip` vs `sourceIp`, or `sha256` vs `hash_sha256`.

`EvidenceNormalizationService` transforms all raw incident telemetry and linked event attributes into standardized, immutable `CanonicalEvidenceRecord` objects with deterministic identifiers and SHA-256 cryptographic digests.

---

### 2. Canonical Schema (`app/schemas/canonical_evidence.py`)

```python
class CanonicalEvidenceRecord(BaseModel):
    evidence_id: str = Field(..., description="Deterministic, unique evidence identifier (e.g. EV-INC-01-EVT1-process_command_line)")
    incident_id: str = Field(..., description="Associated incident ID")
    source_system: str = Field("FortiSIEM", description="Original SIEM or EDR telemetry provider")
    source_event_id: Optional[str] = Field(None, description="Source event ID if extracted from a specific raw event")
    source_field: str = Field(..., description="Canonical source field path (e.g. process.command_line)")
    observed_value: Any = Field(..., description="Original observed value extracted from telemetry")
    observed_at: Optional[str] = Field(None, description="Observation or event timestamp in ISO-8601 format")
    evidence_type: str = Field(..., description="Category: PROCESS_EXECUTION, PROCESS_LINEAGE, USER_CONTEXT, NETWORK_CONNECTION, DNS_QUERY, FILE_HASH, ENDPOINT_TELEMETRY, SECURITY_EVENT")
    availability: str = Field("AVAILABLE", description="AVAILABLE or UNAVAILABLE")
    provenance_status: str = Field("SOURCE_RECORDED", description="Provenance status of the evidence")
    integrity_digest: str = Field(..., description="SHA-256 cryptographic digest of source field and value")
```

---

### 3. Canonical Field Mapping Table

| Raw SIEM Key Variants | Canonical Field Path | Evidence Type |
|---|---|---|
| `cmdline`, `command`, `processcommandline`, `command_line` | `process.command_line` | `PROCESS_EXECUTION` |
| `process`, `process_name`, `app`, `filename` | `process.name` | `PROCESS_EXECUTION` |
| `imagepath`, `filepath` | `process.file_path` | `PROCESS_EXECUTION` |
| `parentcmd`, `parentcmdline`, `parent_command_line` | `process.parent_command_line` | `PROCESS_LINEAGE` |
| `parentprocess`, `parent_process`, `parent` | `process.parent_name` | `PROCESS_LINEAGE` |
| `username`, `user`, `srcuser`, `source_user`, `account` | `user.name` | `USER_CONTEXT` |
| `srcip`, `src_ip`, `source_ip`, `sourceip` | `network.source_ip` | `NETWORK_CONNECTION` |
| `destip`, `dest_ip`, `destination_ip`, `destinationip` | `network.destination_ip` | `NETWORK_CONNECTION` |
| `srcport`, `src_port` | `network.source_port` | `NETWORK_CONNECTION` |
| `destport`, `dest_port` | `network.destination_port` | `NETWORK_CONNECTION` |
| `destdomain`, `domain`, `dns_query` | `dns.domain` | `DNS_QUERY` |
| `url`, `uri` | `web.url` | `DNS_QUERY` |
| `sha256`, `hash_sha256`, `filesha256`, `hash` | `file.hash_sha256` | `FILE_HASH` |
| `md5`, `hash_md5`, `filemd5` | `file.hash_md5` | `FILE_HASH` |
| `devname`, `hostname`, `dev_name` | `endpoint.hostname` | `ENDPOINT_TELEMETRY` |
| `devip` | `endpoint.ip` | `ENDPOINT_TELEMETRY` |
| `action` | `security.action` | `SECURITY_EVENT` |
| `event_type` | `security.event_type` | `SECURITY_EVENT` |

---

### 4. Deterministic Identity & Integrity Digest
- **Evidence Identifier Formula:**
  ```python
  clean_field = source_field.replace(".", "_").replace(" ", "_").lower()
  evidence_id = f"EV-{incident_id}-{source_event_id or 'TOP'}-{clean_field}"
  ```
- **SHA-256 Digest Formula:**
  ```python
  raw_token = f"{source_field.strip().lower()}:{str(observed_value).strip()}"
  integrity_digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
  ```

---

### 5. Ground Truth Purging Guarantee
During normalization, the service consults `FORBIDDEN_GROUND_TRUTH_KEYS`. Any key matching resolution, cleared reason, cleared user, or analyst notes is discarded before canonical records are built:
```python
if norm_key in FORBIDDEN_GROUND_TRUTH_KEYS:
    continue
```
This guarantees that the model receives zero hints about historical analyst determinations.

