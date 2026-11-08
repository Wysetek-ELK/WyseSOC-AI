# 02. RULE INTELLIGENCE ANALYZER

## Overview

The `RuleIntelligenceAnalyzer` (`backend/app/services/rule_intelligence_analyzer.py`) is the foundational ingestion engine of Agent Intelligence Studio 2.0. Its primary mission is to extract the **true detection semantics** of a SIEM detection rule by strictly separating **authoritative rule logic** from **observed incident telemetry**, preventing false threshold hallucination.

---

## The 7-Tier Input Hierarchy

To resolve detection ambiguity, the analyzer evaluates data sources in order of strict evidentiary precedence:

```text
+-------------------------------------------------------------------------+
|                  7-TIER INPUT HIERARCHY PRECEDENCE                      |
|                                                                         |
|  Tier 1: Authoritative SIEM XML/JSON Rule Definition [HIGHEST]          |
|          (Raw FortiSIEM / Splunk / Sigma rule condition logic)          |
|                               ^                                         |
|  Tier 2: Exported SIEM Rule Metadata & Filter Conditions                 |
|          (Formal query strings, threshold parameters, group-by keys)    |
|                               ^                                         |
|  Tier 3: Rule Name & Description Textual Semantics                      |
|          (Formal vendor naming standards, e.g. "Outbound", "Exfil")     |
|                               ^                                         |
|  Tier 4: Rule Category & Severity Classification                         |
|          (MITRE ATT&CK tactics, FortiSIEM category, base severity)      |
|                               ^                                         |
|  Tier 5: Data Source & Event Type Semantics                              |
|          (Firewall traffic, EDR process, Identity authentication)       |
|                               ^                                         |
|  Tier 6: Observed Incident Metadata Pattern                              |
|          (Aggregated event attributes from live telemetry)              |
|                               ^                                         |
|  Tier 7: Raw Telemetry Attribute Names [LOWEST]                         |
|          (Field keys present in sample events without thresholds)       |
+-------------------------------------------------------------------------+
```

### Ingestion Logic & Field Extraction

When `analyze_rule(rule, authoritative_siem_definition)` is executed:
1. **Tier 1 Extraction:** If an authoritative definition (XML or dictionary) is supplied, the analyzer parses:
   - `threshold` (numerical limit, e.g. `1073741824`).
   - `threshold_unit` (e.g. `bytes`, `events`, `count`).
   - `aggregation_window` (e.g. `3600s`).
   - `grouping_keys` (e.g. `["srcIp", "destIp"]`).
   - `conditions` (e.g. `direction = 'OUTBOUND' AND proto = 'TCP'`).
   - Provenance is marked as `SourceProvenance.SIEM_EXPORT` or `AUTHORITATIVE_API`.
   - Status is marked as `SemanticsDefinitionStatus.VERIFIED`.
2. **Fallback Analysis (Tiers 2–7):** If no authoritative definition is available:
   - Observed incident patterns (e.g., `{"sentBytes64": 2130499380}`) are extracted strictly as `observed_telemetry_keys` and `observed_telemetry_samples`.
   - **Crucial Rule:** The numerical value `2130499380` is NEVER assigned as the rule's detection threshold.
   - The status is explicitly assigned as `SemanticsDefinitionStatus.INCOMPLETE`.
   - Missing requirements are formally registered:
     - `Authoritative SIEM rule definition not ingested.`
     - `Aggregation window and threshold conditions unverified.`
     - `Provisional draft generated with unresolved detection conditions.`

---

## Data Schema: `DetectionSemantics`

The output of the analyzer is a strictly typed Pydantic model (`backend/app/schemas/rule_intelligence.py`):

```python
class DetectionSemantics(BaseModel):
    rule_id: str
    rule_name: str
    definition_status: SemanticsDefinitionStatus  # VERIFIED | INCOMPLETE | PROVISIONAL | DEPRECATED
    provenance: SourceProvenance                  # SIEM_EXPORT | AUTHORITATIVE_API | SYNTHESIZED_FALLBACK
    detection_intent: str                         # Summary of what the rule detects
    monitored_entity: str                         # e.g., "Network Egress Flow", "Host Process"
    threshold: Optional[float] = None             # Authoritative threshold only
    threshold_unit: Optional[str] = None          # e.g., "bytes", "attempts"
    aggregation_window: Optional[str] = None      # e.g., "1 hour", "5 minutes"
    grouping_keys: List[str] = Field(default_factory=list)
    observed_telemetry_keys: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    confidence_in_definition: float               # 0.0 to 1.0 based on tier completeness
    analyzed_at: datetime
```

---

## Protection Against False Threshold Hallucination

In prior systems, an alert triggered by a large transfer of 2.1 GB would cause the policy to instruct the model: *"Check if sent bytes exceeds 2,130,499,380 bytes."* If the next day an attacker exfiltrates 1.8 GB (which violates the true SIEM threshold of 1.0 GB), the AI verdict would produce a False Negative because 1.8 GB < 2.1 GB.

`RuleIntelligenceAnalyzer` prevents this catastrophic failure:
- When status is `INCOMPLETE`, the system generates an explicit requirement:
  ```text
  [!] UNRESOLVED DETECTION CONDITION: Authoritative byte threshold undefined.
      Investigator must inspect destination authorization and compare observed
      outbound volume against historical baseline rather than a static cutoff.
  ```
- This guarantees safety until a SOC Lead ingests the official SIEM XML rule definition.
