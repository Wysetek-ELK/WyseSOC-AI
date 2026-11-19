# 04 — Evidence Contract & Normalization Architecture
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Contract ID:** `EC-7bd13e89-0828-48e6-8cf5-f3cbf12d438c-V2`  
**Detection Archetype:** `POLICY_VIOLATION`  

---

## 1. Evidence Contract Architecture

The Evidence Contract defines the strict data boundary between raw SIEM log fields and the canonical evidence records provided to the Local LLM. By transforming unstructured vendor logs into a deterministic, schema-enforced structure, the contract eliminates hallucination vectors and prevents prompt-injection payloads from altering detection logic.

### Canonical Schema Requirements for `POLICY_VIOLATION`

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EVIDENCE CONTRACT SCHEMA BOUNDARY                    │
├─────────────────────────┬──────────────────────────────────────────────┤
│ Core (Mandatory)        │ • network.source_ip                          │
│                         │ • security.event_type                        │
│                         │ • event.timestamp                            │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Conditional             │ • user.name                                  │
│ (Evaluated when raw     │ • http.url                                   │
│  logs are present)      │ • webCategory                                │
│                         │ • network.destination_ip                     │
│                         │ • network.destination_domain                 │
│                         │ • security.action                            │
│                         │ • endpoint.hostname                          │
├─────────────────────────┼──────────────────────────────────────────────┤
│ Optional Enrichment     │ • network.service                            │
│ (Non-blocking if absent)│ • telemetry.user group                       │
│                         │ • telemetry.policyid                         │
│                         │ • http.status_code (omitted in UTM blocks)   │
└─────────────────────────┴──────────────────────────────────────────────┘
```

---

## 2. Field Normalization Mapping from FortiGate UTM Logs

Raw logs from the FortiGate firewall stream are mapped into canonical evidence records via the deterministic normalizer:

| Raw FortiGate UTM Field | Canonical Evidence Field | Example Normalized Value | Criticality |
| :--- | :--- | :--- | :--- |
| `srcip` / `srcIpAddr` | `network.source_ip` | `172.26.29.74` | **CORE** |
| `eventType` / `eventtype` | `security.event_type` | `FortiGate-web-ftgd-cat-blk` | **CORE** |
| `eventTime` / `phRecvTime` | `event.timestamp` | `1795095495000` | **CORE** |
| `dstip` / `destIpAddr` | `network.destination_ip` | `151.101.131.42` | **CONDITIONAL** |
| `hostname` / `destName` | `network.destination_domain` | `media.licdn.com` | **CONDITIONAL** |
| `catdesc` / `webCategory` | `webCategory` | `Business` | **CONDITIONAL** |
| `action` | `security.action` | `blocked` | **CONDITIONAL** |
| `user` | `user.name` | `neerajk` | **CONDITIONAL** |
| `group` | `telemetry.user group` | `Limited-Internet-Access` | OPTIONAL |
| `service` | `network.service` | `HTTPS` | OPTIONAL |
| `devname` | `endpoint.hostname` | `GDC-MSSP-FW2` | CONDITIONAL |
| `policyid` | `telemetry.policyid` | `4` | OPTIONAL |

---

## 3. Real Verification Case: Incident #4142

To verify normalization integrity under live operational conditions, incident `#4142` was retrieved and parsed via `/api/incidents/4142/model-payload`:

- **Total Canonical Records Extracted:** **46** canonical evidence items.
- **Evidence Identifiers:** Each record is assigned an immutable digest and evidence ID (e.g. `EV-4142-PAYLOAD_DETAIL-webcategory`, `EV-4142-3211488746794588958-srcip`).
- **Telemetry Verified:**
  - `network.source_ip`: `172.26.29.74`
  - `network.destination_ip`: `151.101.131.42`
  - `network.destination_domain`: `media.licdn.com`
  - `webCategory`: `Business`
  - `security.action`: `blocked`
  - `user.name`: `neerajk`
  - `telemetry.user group`: `Limited-Internet-Access`
  - `http.method`: `GET`
  - `endpoint.hostname`: `GDC-MSSP-FW2`
- **Integrity Digest:** All records passed cryptographic tamper detection (`integrity_digest` verified against original event payload).

---

## 4. Evidence Sufficiency & Compaction

1. **Sliding-Window Compaction:** When an incident contains hundreds of raw UTM events, `EvidenceCompactionService` summarizes identical repeated connection attempts while preserving the full range of timestamps, unique destination domains, user identities, and policy block actions.
2. **Missing Evidence Isolation:** In FortiGate UTM blocks, `http.status_code` is not returned because the firewall drops or resets the session before generating an HTTP response. The contract flags `http.status_code` as `NOT_IN_SOURCE` without degrading overall evidence completeness below acceptable thresholds.
