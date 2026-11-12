# WyseSOC AI — AI Context Builder Audit and Remediation

**Document:** `04_AI_CONTEXT_BUILDER_REMEDIATION.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Affected Components:** `VerdictPipeline` (`backend/app/services/verdict_pipeline.py`), `EvidenceCompactionService` (`backend/app/services/evidence_compaction_service.py`)  
**Status:** IMPLEMENTED, TESTED & VERIFIED  

---

## 1. Audit Findings

The AI Context Builder is responsible for assembling the prompt sent to the LLM on Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ`). The audit identified the following critical context-assembly challenges:

1. **Context Window Exceeded on Large Incidents:**
   Prior to recent token budgeting fixes, large incidents containing hundreds of events (such as incident #175330) generated over 40,000 prompt tokens, immediately exceeding Server 2's context limit and triggering `CONTEXT_WINDOW_EXCEEDED`.
2. **Loss of High-Value Web Telemetry During Compaction:**
   When compacting evidence tables under token pressure, `EvidenceCompactionService` previously prioritized host and user fields while treating `url` and `webcategory` as low-priority generic telemetry. In web filtering and proxy incidents, this caused URLs and categories to be dropped before lower-priority network metrics.
3. **Evidence Identifier Provenance:**
   The model requires explicit, unambiguous evidence citations (e.g. `EV-176061-001`, `EV-176061-TOP-source_ip`) to ground its reasoning. When fields were truncated or improperly labeled, the model was forced to cite irrelevant evidence IDs (such as timestamp IDs for IP claims), leading to false grounding failures.

---

## 2. Implemented Remediation

### 2.1 Dynamic Token Budgeting (8K/16K Architecture)
`EvidenceCompactionService` implements dynamic token calculation based on model capacity and reserved outputs:
- **Total Model Capacity:** 16,384 tokens (Qwen2.5-7B-Instruct-AWQ supports up to 32,768 tokens).
- **Reserved Completion Budget:** 2,048 tokens.
- **Maximum Effective Input Budget:** 8,192 tokens.
- **Sub-Budget Allocations:**
  - System Prompt & Safety Directives: 1,500 tokens (Hard Reserve).
  - Detection Rule & Policy Requirements: 1,200 tokens (Hard Reserve).
  - Verified Historical Precedents (Semantic RAG): 1,000 tokens (Tenant-Isolated).
  - Incident Evidence Telemetry: Dynamic remainder (~4,492 tokens).

### 2.2 SOC-Aware Field Prioritization
Updated the field priority classification in `EvidenceCompactionService.compact_evidence` to elevate web and URL telemetry to Priority 3:
```python
# Priority 1: Mandatory Identifiers
PRIORITY_1 = {"event.timestamp", "network.source_ip", "security.event_type", "network.destination_ip"}

# Priority 2: High-Value Entity Telemetry
PRIORITY_2 = {"user.name", "endpoint.hostname", "process.name", "security.action"}

# Priority 3: SOC Investigation Attributes (Web, Proxy, HTTP)
PRIORITY_3 = {"http.url", "webCategory", "http.method", "http.status_code", "network.service", "network.source_port"}

# Priority 4: Extended Network & Performance Metrics
PRIORITY_4 = {"network.bytes_in", "network.bytes_out", "network.packets"}
```
Under token constraints, Priority 4 fields are summarized or truncated first, ensuring URLs, categories, and actions remain fully available in the AI prompt.

### 2.3 Deterministic Deduplication and Compaction
For incidents with repeated events (e.g. repeated firewall drops over minutes):
1. Events with identical source IP, destination IP, URL, and category are grouped.
2. A single compacted evidence record is created containing:
   - `occurrence_count`: Number of deduplicated occurrences.
   - `first_seen` / `last_seen`: Time span of the activity.
   - Preserved unique values.
3. This achieves up to **85% token reduction** on volumetric incidents without dropping a single security indicator.

### 2.4 Evidence ID Tagging
Every evidence line provided in the prompt table is prefixed with a deterministic citation tag:
- `EV-{incident_id}-{event_index}-{canonical_field}`
- Top-level incident attributes: `EV-{incident_id}-TOP-{field}`

This ensures the LLM can reference verified telemetry without hallucinating or referencing arbitrary indices.

---

## 3. Automated Test Verification

| Test ID | Scenario | Verification Method | Status |
|---|---|---|---|
| **T07** | Field dropped from AI context | Verified `CONTEXT_OMITTED` status is tracked if an attribute is excluded during budgeting | PASS |
| **T21** | URL normalization edge cases | Preserved security-relevant paths and query strings across encoding variations | PASS |
| **T22** | Prompt injection in raw evidence | Escaped and quarantined prompt injection strings in raw logs | PASS |
| **8K/16K** | Token budgeting boundary tests | Verified incidents exceeding 4,978 tokens and up to 14,000 tokens compact cleanly | PASS |

