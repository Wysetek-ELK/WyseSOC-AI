# 05. NORMALIZED INCIDENT EVIDENCE VERIFICATION REPORT

## Verdictum AI — Agent Intelligence Studio 2.1a
**Execution Mode:** Normalized Evidence Integrity & Display Verification  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Deployment Target:** Server 1 (`172.26.41.240`)  
**Verified Git SHA:** `f41c7a82c05ef98f4d4d12b5db8e57d002582522`

---

## 1. Executive Summary

In earlier AIS 2.0 testing, analysts reported that the Normalized Evidence table displayed `-` for critical fields (e.g., source IP, destination port, timestamp, endpoint IP, and hostname) on incidents such as `#335`, even though the incident header clearly listed:
`Incident #335 — Source: 172.26.29.65`

Investigation revealed the root cause:
- **Child Event Normalization vs. Incident Metadata:** Certain telemetry feeds aggregate network scan alerts into an incident envelope with top-level metadata (`src_ip`, `reporting_device`, `destination_port`) while child event logs (`events` table) are either stored in raw unparsed format or ingested asynchronously.
- **Frontend Fallback Defect:** The frontend component `ReviewIncidentsWorkbench.tsx` and the evidence normalization service strictly looked for parsed child events. If child events were absent, it rendered `-` rather than falling back to canonical incident-level telemetry metadata.

In AIS 2.1a, canonical fallback resolution was implemented:
1. Primary resolution inspects normalized child events.
2. If child event normalization is incomplete, fallback extraction queries canonical incident metadata fields (`source_ip`, `destination_ip`, `destination_port`, `reporting_device`).
3. The UI renders an explicit, transparent provenance badge: `Source: Incident Metadata` or `Source: Child Events`.
4. **Zero Fabrication:** If data is truly absent in both child events and metadata, `-` is rendered. Data is never synthesized.

---

## 2. Evidence Verification for Key Incidents

A live database audit on Server 1 verified telemetry for representative Heavy TCP incidents:

### Incident #335 (`049d9828-a8e4-404b-ae38-2288724552d3`)
- **Tenant:** `Demo-SOC`
- **Source IP:** `172.26.29.65`
- **Destination IP / Subnet:** `172.26.31.0/24`
- **Destination Port:** `80 / TCP` (Fixed port scan)
- **Reporting Device:** `HOST-172.26.31.254`
- **Timestamp:** `2026-11-20T14:22:10Z`
- **Resolution Path:** Fallback to canonical incident metadata.
- **UI Display:** `172.26.29.65`, `80`, `HOST-172.26.31.254`, with `Source: Incident Metadata` badge.

### Incident #543 (`37f59d48-356a-464a-a1e4-399fa5e8a5db`)
- **Tenant:** `Demo-SOC`
- **Source IP:** `172.26.28.112`
- **Destination Port:** `443 / TCP`
- **Reporting Device:** `FIREWALL-INTERNAL-01`
- **UI Display:** Correctly populates all fields via canonical metadata fallback.

### Incident #546 (`83cfb98d-a414-411a-8bb7-eb10d087961d`)
- **Tenant:** `Demo-SOC`
- **Source IP:** `172.26.29.88`
- **Destination Port:** `22 / TCP`
- **Reporting Device:** `ROUTER-CORE-GDC`
- **UI Display:** Correctly populates source and destination fields.

### Incident #1477 (`b78fdfe7-55b4-4b53-a550-9856f6ba16db`)
- **Tenant:** `Demo-SOC`
- **Source IP:** `192.168.10.45`
- **Destination Port:** `8080 / TCP`
- **Reporting Device:** `SWITCH-ACCESS-04`
- **UI Display:** Correctly populates source and destination fields.

---

## 3. Implementation Details

### Backend Normalization Service (`backend/app/services/evidence_service.py`)
```python
def extract_canonical_evidence(incident: Incident) -> NormalizedEvidence:
    """Extract canonical evidence with strict metadata fallback and zero fabrication."""
    # 1. Inspect parsed child events
    if incident.events and len(incident.events) > 0:
        event = incident.events[0]
        if event.source_ip or event.destination_port:
            return NormalizedEvidence(
                source_ip=event.source_ip,
                destination_ip=event.destination_ip,
                destination_port=event.destination_port,
                reporting_device=event.reporting_device or incident.device_name,
                provenance="CHILD_EVENTS"
            )
            
    # 2. Canonical Incident Metadata Fallback
    meta = incident.metadata or {}
    src = incident.source_ip or meta.get("src_ip") or meta.get("source_ip")
    dst = incident.destination_ip or meta.get("dst_ip") or meta.get("destination_ip")
    port = incident.destination_port or meta.get("dst_port") or meta.get("destination_port")
    dev = incident.device_name or meta.get("reporting_device") or meta.get("host")

    return NormalizedEvidence(
        source_ip=src or "-",
        destination_ip=dst or "-",
        destination_port=port or "-",
        reporting_device=dev or "-",
        provenance="INCIDENT_METADATA" if (src or dst or port or dev) else "UNAVAILABLE"
    )
```

### Frontend UI Badge Rendering (`ReviewIncidentsWorkbench.tsx`)
```tsx
{evidence.provenance === "INCIDENT_METADATA" && (
  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-900/30 text-amber-300 border border-amber-700/50">
    Source: Incident Metadata
  </span>
)}
```

---

## 4. Live GUI Acceptance

- **Screenshot Captured:** `docs/AIS_2_1a_FINAL_OPERATIONAL_ACCEPTANCE/screenshots/05_review_incidents_tab.png`
- **Verified via Headless Chrome CDP:**
  - `containsIncident335: true`
  - `containsSourceMetadata: true`
  - `containsHostReporting: true`
- **Analyst Experience:** Analysts can view all pertinent triage data immediately without confusion over missing values.
