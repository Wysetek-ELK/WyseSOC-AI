# Report 05 — Incident Evidence Mapping, Normalization & Provenance Validation
**Project:** Verdictum AI — Agent Intelligence Studio 2.1 (AIS 2.1)  
**Sample Incidents Audited:** #335, #543, #546, #1477, #176011, #176122  
**Date:** November 21, 2026  

---

## 1. Observed Defect in Production GUI

In `ReviewIncidentsWorkbench.tsx`:
- The incident queue list displayed summaries with valid source IPs, such as:
  `Incident #335 — Source: 172.26.29.65`
- However, the "Normalized Evidence Artifacts" table rendered `-` for all fields (source IP, timestamp, destination port, endpoint IP, hostname).

---

## 2. Root Cause Analysis

### Root Cause: Frontend Field Name Mismatch Against Canonical Schema
In `ReviewIncidentsWorkbench.tsx`:
```tsx
// Defective code in ReviewIncidentsWorkbench.tsx (lines 521-523):
{normalizedEvidence.map((ev, idx) => (
  <tr key={idx} className="hover:bg-slate-900/40">
    <td className="py-1 px-2.5 text-cyan-400 font-semibold">{ev.field}</td>
    <td className="py-1 px-2.5 text-slate-200 truncate max-w-xs">{String(ev.value ?? "-")}</td>
    <td className="py-1 px-2.5 text-slate-500 font-bold">{ev.evidence_id || `EV-${idx + 1}`}</td>
  </tr>
))}
```
1. `api.getIncidentModelPayload()` returns `canonical_evidence`, which is an array of `CanonicalEvidenceRecord` dictionaries serialized by Pydantic:
   - `source_field`: e.g. `"network.source_ip"`, `"endpoint.hostname"`, `"event.timestamp"`
   - `observed_value`: e.g. `"172.26.29.65"`, `"FortiSIEM-Super"`, `"2026-11-20T16:26:00Z"`
   - `evidence_id`: e.g. `"EV-335-TOP-network_source_ip"`
   - `provenance_status`: e.g. `"SOURCE_RECORDED"`, `"METADATA_DERIVED"`
2. The frontend accessed `ev.field` and `ev.value`!
   - `ev.field` was undefined (rendering blank).
   - `ev.value` was undefined, so `String(ev.value ?? "-")` **always evaluated to `"-"`**!

### Secondary Factor: Header-Only Incidents Lacking Child Events
Certain SIEM incidents (e.g. #176122) contain top-level metadata in `incidents` table, but 0 child records in `incident_events`.
`EvidenceNormalizationService` correctly extracts `network.source_ip`, `endpoint.hostname`, `endpoint.ip`, `event.timestamp`, and `security.alert_title` from `Incident` columns.
However, when child events were missing and `canonical_evidence` had fewer records, the frontend lacked explicit provenance attribution distinguishing `Raw Event Log` from `Source: Incident Metadata`.

---

## 3. Authoritative Mapping Contract & Remediation

### 3.1 Field Mapping Hierarchy
```
1. Raw Child Event (IncidentEvent.raw_log / attributes)
   ↳ Provenance: "Raw Event Log" (EV-ID: EV-{inc_id}-{evt_id}-{field})
2. Top-Level Incident Metadata (Incident.source_ip, reporting_device, etc.)
   ↳ Provenance: "Source: Incident Metadata" (EV-ID: EV-{inc_id}-TOP-{field})
3. Unavailable Attributes
   ↳ Provenance: "Not available" (No synthetic EV-ID)
```

### 3.2 Frontend Correction
Update `ReviewIncidentsWorkbench.tsx` and the unified Tab 1 / Tab 2 views:
```tsx
const fieldName = ev.source_field || ev.canonical_field || ev.field || "unknown";
const observedVal = ev.observed_value ?? ev.value ?? (ev.raw_field_name ? String(ev.observed_value) : null);
const provenance = ev.provenance_status === "METADATA_DERIVED" || ev.source_event_id === "TOP" 
  ? "Incident Metadata" 
  : (ev.source_system || "Raw Event Log");
```
- If `observedVal` is null or undefined: Display `Not available` with italic styling.
- Display explicit provenance pill: `Raw Log` vs `Incident Metadata`.
- Never fabricate fake evidence, synthetic EV-IDs, or ungrounded values.
