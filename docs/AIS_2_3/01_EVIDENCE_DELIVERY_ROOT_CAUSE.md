# AIS 2.3 — Evidence Delivery Root Cause Analysis

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3 (Real Evidence Delivery & Verdict Accuracy Pilot)  
**Date:** November 23, 2026  
**Status:** COMPLETE & GROUNDED  

---

## 1. Executive Summary

During AIS 2.2a smoke testing, 5/5 real inference calls executed against Server 2's local GPU model (`Qwen/Qwen2.5-7B-Instruct-AWQ`) returned `REQUIRES_ATTENTION`. Crucially, the model's generated rationales reported:
> *"The raw event count is zero, and critical fields are missing."*

A thorough forensic audit of the end-to-end evidence delivery path was conducted in Stage A of AIS 2.3, tracing the workflow from original raw ingestion through database persistence, payload allowlisting, policy compilation, token budgeting, to prompt assembly.

This investigation confirmed three distinct root causes that systematically starved the model of telemetry:
1. **Target Population Disconnect:** The 20 historical benchmark incidents containing rich endpoint and file threat telemetry (`fixtures/Incident json.zip`) were never ingested into Server 1's PostgreSQL database. Instead, previous evaluations operated on firewall scan incidents that had no endpoint telemetry.
2. **Raw Telemetry Token Overflow & Aggressive Trimming:** Passing uncompacted raw JSON fixtures resulted in 43,434+ tokens of raw dumps, drastically exceeding the 3,328-token prompt budget for the 4,096-token Qwen AWQ model. Downstream token budgeting pruned all secondary events and stripped primary event attributes to prevent token overflow.
3. **Attribute Container Nesting & Key Alias Gaps:** FortiSIEM fixture JSON encapsulates event attributes inside a nested `attribute` dictionary (`{"eventId": ..., "attribute": {"Command": ..., "File Name": ...}}`). Previous parsers did not unwrap this sub-dictionary, and canonical normalization maps lacked space-separated vendor aliases (e.g. `Raw Event Log`, `Parent Command`, `SHA256 Hash`).

---

## 2. End-to-End Evidence Delivery Audit

The expected evidence delivery pipeline is:
```
FortiSIEM Incident JSON
  └── Database Persistence (incidents & incident_events)
        └── ModelFacingPayload Allowlist (zero ground truth)
              └── Canonical Evidence Normalization (cryptographic digests)
                    └── Unified Policy Compilation (Section 1–9 directives)
                          └── TokenBudgetService (4,096 context window)
                                └── Local GPU Inference (Qwen AWQ)
                                      └── Independent Verdict Validation & Guardrails
```

### 2.1 Defect 1: Incident Population Disconnect
- Server 1's PostgreSQL database hosted 6,167 incidents, predominantly belonging to `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`).
- The 20 curated historical benchmark fixtures—consisting of 10 CrowdStrike alerts (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) and 10 Palo Alto Prisma SASE alerts (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`)—existed only within the offline zip file `fixtures/Incident json.zip`.
- When Server 1 was queried for candidate evaluation incidents during AIS 2.2a, it naturally selected Heavy TCP scan incidents. Because these incidents consist solely of firewall network connections without process lineages or endpoint files, the model accurately stated that endpoint evidence was absent.

### 2.2 Defect 2: Token Overflow & Destructive Compaction
- In `EmpiricalBenchmarkHarness.evaluate_single_incident`, the harness passed `incident_rec.sanitized_payload` directly into `TokenBudgetService.budget_prompt`.
- Forensic measurement revealed that a single CrowdStrike fixture with 25 events contained **43,434 tokens** in `rawEvents` due to 64 verbose attributes per event (including unparsed collector metadata, geographic coordinates, and raw syslog buffers).
- Total prompt tokens reached **46,190 tokens**, against an available prompt budget of **3,328 tokens** ($4,096 - 768$ completion tokens).
- To prevent complete context explosion, `TokenBudgetService` executed fallback trimming steps (Steps 3a, 3d, 3e), which popped secondary events (`events_pruned_count: 24`) and stripped `raw_log` or replaced it with a 200-char truncated preview.
- Consequently, the model received an empty or severely pruned event array.

### 2.3 Defect 3: Nested Attribute Container & Key Gaps
- FortiSIEM event objects in `rawEvents` store event details in a nested dictionary under the key `"attribute"`.
- `_get_field(evt, "attributes", "attribute", {})` extracted the outer wrapper `{"attribute": {...}, "eventId": ...}`.
- When `TokenBudgetService._compact_events` executed:
  ```python
  min_attrs = {k: v for k, v in attrs.items() if v is not None and (k in contract_fields or len(str(v)) < 250)}
  ```
  The value `v` was the entire inner `"attribute"` dictionary, whose stringified length exceeded 250 characters. Because `"attribute"` was not a field in the Evidence Contract, `TokenBudgetService` purged the entire dictionary, leaving only `{"eventId": "..."}`.
- Furthermore, `FIELD_MAPPINGS` in `evidence_normalization_service.py` lacked mappings for space-separated FortiSIEM keys:
  - `Raw Event Log` $\rightarrow$ Unmapped (`None`)
  - `Parent Command` $\rightarrow$ Unmapped (`None`)
  - `Parent File Name` $\rightarrow$ Unmapped (`None`)
  - `Machine Quarantined` $\rightarrow$ Unmapped (`None`)
  - `SHA256 Hash` $\rightarrow$ Unmapped (`None`)
  - `MD5 Hash` $\rightarrow$ Unmapped (`None`)
  - `Application Name` $\rightarrow$ Unmapped (`None`)

---

## 3. Root Cause Summary Matrix

| Failure Mode | Component | Observed Symptom | Technical Root Cause |
| :--- | :--- | :--- | :--- |
| **Population Disconnect** | Database Inventory | Zero events evaluated for target rules | Historical benchmark fixtures in `Incident json.zip` were never imported to PostgreSQL. |
| **Context Window Overflow** | `TokenBudgetService` | `CONTEXT_WINDOW_EXCEEDED` (46,190 tokens) | Raw `rawEvents` list bypassed `build_model_facing_payload`, dumping 43k tokens into prompt budget. |
| **Attribute Purging** | `TokenBudgetService._compact_events` | `attributes: {'eventId': '...'}` | Nested `"attribute"` container exceeded 250 chars and was dropped as non-contract field. |
| **Unmapped Telemetry** | `EvidenceNormalizationService` | 0 canonical records for hashes and raw logs | `FIELD_MAPPINGS` lacked aliases for `Raw Event Log`, `Parent Command`, `SHA256 Hash`, etc. |
| **SQLAlchemy Lazy Load** | `verdict_pipeline.py` | `raw_events = []` | Direct dict lookup `incident.__dict__.get("events")` bypassed SQLAlchemy attribute instrumentation. |

All five root cause mechanisms have been resolved in Stage A and Stage D of AIS 2.3.
