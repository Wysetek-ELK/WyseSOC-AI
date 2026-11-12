# WyseSOC AI — Incident #176061 Full Evidence Trace

**Document:** `02_INCIDENT_176061_EVIDENCE_TRACE.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Target Incident ID:** 176061 (`68ec2d89-d8d3-4c5c-9aec-ec6ea77a1eff`)  
**Incident Title:** Website access policy violation: Same Source and Destination  
**SIEM Source:** FortiSIEM (Reporting Device: `FGT-HQ-FW01`, Model: FortiGate 200E)  
**Status:** AUDITED, TRACED & VERIFIED  

---

## 1. Incident Metadata and Source Telemetry

### 1.1 Stored Database Record
- **Incident UUID:** `68ec2d89-d8d3-4c5c-9aec-ec6ea77a1eff`
- **Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`
- **Rule Identifier:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
- **Rule Name:** `Website access policy violation: Same Source and Destination`
- **Rule Category:** `Security Policy / Web Filtering`
- **Severity:** Medium (Score: 5)
- **First Seen Epoch:** 1774332922 (2026-03-24 10:15:22 UTC)
- **Last Seen Epoch:** 1774332922 (2026-03-24 10:15:22 UTC)
- **Event Count:** 1 linked underlying event

### 1.2 Raw Ingested Event Payload (`Event` Record)
```text
date=2026-03-24 time=10:15:22 devname="FGT-HQ-FW01" devid="FG200ETK18000123" eventtime=1774332922 tz="+0530" logid="0316013001" type="utm" subtype="webfilter" eventtype="ftgd_blk" level="warning" vd="root" policyid=42 sessionid=1092842 srcip=192.0.2.48 srcport=54218 srcintf="port2" srcintfrole="lan" dstip=198.51.100.32 dstport=443 dstintf="port1" dstintfrole="wan" proto=6 service="HTTPS" hostname="media4.giphy.com" url="https://media4.giphy.com/" cat=26 catdesc="Entertainment" action="blocked" reqtype="referral" urlfilteridx=1 urlfilterlist="Default-Block" msg="URL belongs to a denied category in policy"
```

### 1.3 Pre-Parsed SIEM Attributes (`parsed_details`)
```json
{
  "Source IP": "192.0.2.48",
  "Destination IP": "198.51.100.32",
  "Web Site Category": "Entertainment",
  "Action": "blocked",
  "URL": "https://media4.giphy.com/",
  "Protocol": "HTTPS",
  "Device Name": "FGT-HQ-FW01",
  "Policy ID": "42",
  "Message": "URL belongs to a denied category in policy"
}
```

### 1.4 Incident Top-Level Header Attributes
- `incidentSrc`: `"192.0.2.48"`
- `incidentTarget`: `"198.51.100.32"`
- `incidentRptIp`: `"192.0.2.1"`
- `incidentRptDevName`: `"FGT-HQ-FW01"`

---

## 2. End-to-End Evidence Trace Analysis

### 2.1 Trace Matrix

| Required Field | Raw Source Path | Normalized Canonical Path | DB Value | AI Payload (Evidence Table) | Validator Input | Pre-Fix Status | Post-Fix Status |
|---|---|---|---|---|---|---|---|
| `network.source_ip` | `parsed_details["Source IP"]` & `srcip=192.0.2.48` | `network.source_ip` | `192.0.2.48` | Present (`EV-176061-001`) | `192.0.2.48` | FAIL (Mapped to `telemetry.source ip`) | **PASS** |
| `network.destination_ip` | `parsed_details["Destination IP"]` & `dstip=198.51.100.32` | `network.destination_ip` | `198.51.100.32` | Present (`EV-176061-001`) | `198.51.100.32` | FAIL (Mapped to `telemetry.destination ip`) | **PASS** |
| `http.url` | `parsed_details["URL"]` & `url="https://media4.giphy.com/"` | `http.url` | `https://media4.giphy.com/` | Present (`EV-176061-001`) | `https://media4.giphy.com/` | FAIL (Mapped to `web.url`) | **PASS** |
| `http.method` | Not present in UTM webfilter drop | N/A | `None` | Omitted from table | `NOT_IN_SOURCE` (Conditional in `POLICY_VIOLATION`) | FAIL (Classified as `WEB_ATTACK`, flagged missing) | **PASS** (Recognized as non-emitted) |
| `http.status_code` | Not present (connection blocked before HTTP response) | N/A | `None` | Omitted from table | `NOT_IN_SOURCE` (Conditional in `POLICY_VIOLATION`) | FAIL (Classified as `WEB_ATTACK`, flagged missing) | **PASS** (Recognized as non-emitted) |
| `webCategory` | `parsed_details["Web Site Category"]` & `catdesc="Entertainment"` | `webCategory` | `Entertainment` | Present (`EV-176061-001`) | `Entertainment` | FAIL (Dropped as unmapped attribute) | **PASS** |
| `security.action` | `parsed_details["Action"]` & `action="blocked"` | `security.action` | `blocked` | Present (`EV-176061-001`) | `blocked` | FAIL (Dropped as unmapped attribute) | **PASS** |

---

## 3. Detailed Root-Cause Trace by Pipeline Stage

### Stage 1: SIEM Ingestion
- **Pre-Fix:** Ingestion stored the event, but when linked events existed, top-level incident fields (`incidentSrc`, `incidentTarget`, `incidentRptIp`) were not normalized as fallback records.
- **Post-Fix:** `IngestionService.extract_incident_network_endpoints` parses `incidentSrc`, `incidentTarget`, and `incidentRptIp`, ensuring top-level incident context is preserved in `CanonicalEvidenceRecord`.

### Stage 2: Normalization & Field Mapping
- **Pre-Fix Failure A (Space-separated keys):** FortiSIEM parser emitted keys with spaces (`"Source IP"`, `"Destination IP"`). `FIELD_MAPPINGS` only matched exact lowercase keys without spaces. Consequently, the fallback heuristic converted `"Source IP"` into `telemetry.source ip`, failing canonical schema lookup.
- **Pre-Fix Failure B (URL path collision):** `"url"` was mapped to `web.url`, while detection archetypes and validation rules required `http.url`.
- **Pre-Fix Failure C (Omission of category and action):** Neither `"Web Site Category"`, `"webcategory"`, nor `"catdesc"` existed in `FIELD_MAPPINGS`. They were discarded as unrecognized.
- **Pre-Fix Failure D (Syslog Key-Values):** The raw syslog string was never tokenized. If `parsed_details` had missing keys, the embedded attributes in `raw_log` remained inaccessible.
- **Post-Fix:** `EvidenceNormalizationService` added `clean_attr_key`, regex-based `parse_key_value_string`, comprehensive alias dictionaries, and explicit mapping of `http.url`, `webCategory`, and `security.action`.

### Stage 3: Archetype Classification
- **Pre-Fix:** The rule name contained the substring `"Website"`, causing `RuleIntelligenceAnalyzer` to match `"web"` and misclassify the incident as `WEB_ATTACK` (e.g. SQL Injection or Cross-Site Scripting). This forced `http.method` and `http.status_code` into the `mandatory_core_fields` list. Because perimeter firewalls dropping HTTPS traffic at the SNI/TLS stage cannot record HTTP methods or HTTP status codes, the validator flagged both fields as missing.
- **Post-Fix:** Detection archetypes prioritize `POLICY_VIOLATION` over `WEB_ATTACK` for policy, violation, and filtering rules. `POLICY_VIOLATION` defines `network.source_ip`, `security.event_type`, and `event.timestamp` as core mandatory fields, while `http.method`, `http.status_code`, `http.url`, and `webCategory` are conditional.

### Stage 4: AI Context Builder
- **Pre-Fix:** Because canonical fields were absent, the evidence table sent to Qwen lacked `http.url`, `webCategory`, and `security.action`.
- **Post-Fix:** The evidence context table explicitly presents all normalized fields with unique identifiers (`EV-176061-001-network.source_ip`, `EV-176061-001-http.url`, etc.).

### Stage 5: Model Inference & Claim Grounding
- **Pre-Fix:** The model inferred a `FALSE_POSITIVE` verdict by hypothesizing an internal loopback due to the incident title "Same Source and Destination". It cited an evidence ID corresponding to a timestamp when asserting IP identity. `ModelClaimExtractor` detected a value mismatch (`EVIDENCE_VALUE_MISMATCH`), and the validator rejected the proposed FP (`FP_CRITERIA_UNSATISFIED`).
- **Post-Fix:** Type-aware comparison (`compare_evidence_values`) validates IP equality. Furthermore, `IndependentVerdictValidator` detects that `srcip=192.0.2.48` does not equal `dstip=198.51.100.32` (`media4.giphy.com`), flagging contradiction `LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC`. The system correctly abstains with `REQUIRES_ATTENTION` (Confidence 0.0%) if false positive criteria are not satisfied.

---

## 4. Multi-Event Context Assessment
Incident #176061 contains **1 underlying event** from reporting firewall `FGT-HQ-FW01`. No cross-event collision occurred. All necessary fields (`srcip`, `dstip`, `url`, `catdesc`, `action`) were present in this single event's syslog payload and parsed details.
