# Root Cause Analysis: Incident #175330 Prompt Overflow & CONTEXT_WINDOW_EXCEEDED

**Date:** 2026-11-12  
**Component:** Server 1 Prompt Assembly & Token Budgeting Pipeline  
**Target Incident:** #175330 (`PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT`)  
**Observed Failure:** Model prompt token size exceeded 40,792 tokens against an available prompt budget of 3,584 / 8,192 tokens, failing closed with `CONTEXT_WINDOW_EXCEEDED`.

---

## 1. Executive Summary

During live execution on Server 1 against Server 2's LLM endpoint, FortiSIEM incident #175330 consistently failed with `CONTEXT_WINDOW_EXCEEDED`. While smaller single-event incidents (e.g. #173403) completed inference or bordered context boundaries, incident #175330 generated an unprecedented **40,792 tokens**, exceeding available context by over 1,000%.

Audit of the Server 1 ingestion, normalization, and token-budgeting code uncovered three compounding root causes:
1. **Double Event Ingestion in Normalization:** Both `incident.events` and `incident.raw_payload["rawEvents"]` were independently traversed by `EvidenceNormalizationService`, resulting in 100 raw FortiSIEM events producing double the canonical records (200 event records).
2. **Repetitive Telemetry Inflation Without Compaction:** In high-volume network anomaly detections (e.g., firewall denied port floods), 100 events share identical destination ports (`7680`), protocols (`6`), actions (`deny`), and timestamps, while differing only by ephemeral source ports. Instead of representing frequency as an aggregate count, 361 raw canonical records were emitted, including 189 duplicate timestamps and 100 uncompacted syslog messages (~25,000 tokens of raw text).
3. **Indivisible Telemetry Priority Inversion in TokenBudgetService:** While `TokenBudgetService` correctly trimmed RAG precedents (P7) and secondary events (P5), all `canonical_evidence` records were grouped under P4 (Critical Current Telemetry). P4 was treated as an indivisible mandatory unit that refused reduction. Because P4 alone exceeded the context limit, the service aborted inference.

---

## 2. In-Depth Technical Investigation

### 2.1 Double Normalization Bug
In `EvidenceNormalizationService.normalize_incident_evidence`:
```python
# Before fix:
evts = list(events) if events else []
if not evts:
    evts = incident.raw_payload.get("rawEvents", [])
# Then separately:
if incident.raw_payload and "rawEvents" in incident.raw_payload:
    # Also parsed rawEvents regardless of evts!
```
When FortiSIEM incidents were saved to the database, both the database relational table `IncidentEvent` and the raw JSON payload `raw_payload["rawEvents"]` held the 100 events. The normalization service iterated over both collections, producing duplicate timestamp and syslog canonical evidence records.

### 2.2 Telemetry Characteristics of Network Anomaly Rules
Incident #175330 triggered detection rule `PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT`:
* Description: "Sudden Increase In Firewall Denied Outbound Traffic To A Specific TCP/UDP port"
* Event count: 100 raw events.
* Forensics:
  * Destination Port: `7680` (WUDO / peer-to-peer delivery) across all 100 events.
  * IP Protocol: `6` (TCP) across all 100 events.
  * Firewall Action: `deny` across all 100 events.
  * Timestamps: All within a 60-second burst window.
  * Source Ports: 32 ephemeral high ports from client workstations.
  * Raw Syslog: 100 syslog strings averaging 300–400 characters each.

Because the system previously extracted each attribute from each event into an independent `CanonicalEvidenceRecord`:
- 189 duplicate `event.timestamp` records were created.
- 100 `security.raw_log` records were created (totaling ~100,000 characters).
- 100 identical destination port records were created.
- 100 identical protocol records were created.

### 2.3 Token Budget Allocation Breakdown
Under Server 1's previous token estimation:
- System Safety & JSON Schema (P1): 415 tokens
- Enterprise Investigation Policy (P2): ~1,100 tokens
- Evidence Contract Specification (P3): ~80 tokens
- Canonical Evidence Records (P4): **39,197 tokens**
- Total Prompt Size: **40,792 tokens**

Available context budget on Server 2 (vLLM Qwen2.5-7B-Instruct-AWQ):
- Maximum model context length (`max_model_len`): **4,096 tokens**
- Reserved completion headroom: **512 tokens**
- Available prompt budget: **3,584 tokens**

Because the mandatory P1–P4 core alone was 40,792 tokens, `TokenBudgetService` safely detected overflow and triggered `CONTEXT_WINDOW_EXCEEDED` rather than silently dropping critical evidence.

---

## 3. Remediations Applied

1. **Fixed Double Ingestion in Normalization:**
   `EvidenceNormalizationService.normalize_incident_evidence` now checks if relational events are present; only if absent does it extract nested records from `raw_payload["rawEvents"]`.
2. **Introduced Evidence Compaction Engine (`EvidenceCompactionService`):**
   - **Timestamp Aggregation:** Replaces hundreds of raw timestamps with a single primary trigger timestamp and a bounded `event.time_range` summary (`"2026-11-12T10:00:00Z to 2026-11-12T10:01:00Z (100 events)"`).
   - **Syslog Clustering:** Groups raw syslog strings by structural template, preserving representative samples and occurrence counts.
   - **Tuple Deduplication:** Collapses identical `(source_field, observed_value)` pairs into a single canonical record with an explicit `occurrence_count` attribute, while strictly protecting forensic command lines and file hashes from collapse.
   - **Relevance Selection:** Prioritizes Evidence Contract required fields, detection rule criteria, and core SOC entities.
3. **Synchronized Canonical Evidence Grounding:**
   `VerdictPipeline` synchronizes the deduplicated records back to `norm_result.records` so that when the LLM cites evidence IDs, the claim grounding validator validates citations without reference errors.
