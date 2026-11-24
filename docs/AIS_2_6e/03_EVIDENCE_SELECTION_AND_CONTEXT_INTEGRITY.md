# AIS 2.6e — Workstream 2: Evidence Selection and Context Integrity Report

**Phase:** AIS 2.6e  
**Evaluated At:** 2026-11-24T17:10:00Z  
**Document Identity:** `docs/AIS_2_6e/03_EVIDENCE_SELECTION_AND_CONTEXT_INTEGRITY.md`  
**Referenced Manifests:**  
- [EVIDENCE_RETENTION_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/EVIDENCE_RETENTION_REGISTER.json)
- [CONTEXT_OVERFLOW_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CONTEXT_OVERFLOW_REGISTER.json)
- [CORRECTED_BASELINE_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CORRECTED_BASELINE_METRICS.json)

---

## 1. Evidence Preservation Hierarchy

In accordance with Non-Negotiable Requirement 5:
> *"No silent removal of critical telemetry to satisfy context limits. If all decision-critical evidence cannot fit, mark the incident CONTEXT_BUDGET_BLOCKED."*

`TokenBudgetService` implements a strict priority hierarchy:
1. **Tier P1 (IMMUTABLE):** System safety instructions and JSON output schema.
2. **Tier P2 (IMMUTABLE):** Approved rule-specific decision directives.
3. **Tier P3 (IMMUTABLE):** Mandatory Evidence Contract requirements.
4. **Tier P4 (IMMUTABLE):** Critical current incident telemetry, primary process command lines, file hashes, parent processes, and canonical evidence citations.
5. **Tier P5 (PROGRESSIVELY TRIMMABLE):** Correlated secondary events beyond the trigger event.
6. **Tier P6 (TRIMMABLE):** Optional enrichment fields (GeoIP, external whois).
7. **Tier P7 (TRIMMED FIRST):** Historical RAG precedents.

---

## 2. Deterministic Compaction vs Destructive Truncation

`TokenBudgetService._compact_canonical_evidence` eliminates non-reasoning forensic overhead without omitting decision-critical attributes:
- Strips null metadata fields and redundant internal schema descriptors.
- Preserves every `evidence_id`, `source_field`, and `observed_value`.
- Preserves primary command lines (e.g. `"C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe"`), target hosts, and user contexts.
- Retains IOC values (e.g. `update.ultraviewer.net`) and parent process lineages (`services.exe`).

### Evidence Retention Audit Results
Across all 20 frozen cohort incidents:
- **Total Canonical Evidence Records:** 100% of primary evidence records retained.
- **Decision-Critical Indicators Preserved:** 100% (20 of 20 incidents).
- **Critical Evidence Omitted:** 0% (0 of 20 incidents).
- **Incidents Blocked on Context Budget:** 0 incidents (`CONTEXT_OVERFLOW_REGISTER.json` confirms `total_overflows: 0`).

---

## 3. Transparency & Lineage Assurance

Every prompt sent to the LLM carries traceable evidence IDs matching the normalized canonical evidence. The model is instructed to cite these explicit evidence IDs in its `supporting_claims`, enabling the deterministic validator (Mode C) to verify factual grounding against raw telemetry.
