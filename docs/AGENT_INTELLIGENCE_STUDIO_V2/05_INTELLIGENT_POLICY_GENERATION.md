# 05. INTELLIGENT POLICY GENERATION

## Overview

The `PolicyGenerationService` (`backend/app/services/policy_generation_service.py`) synthesizes tailored, 9-section investigation policies. Rather than applying a static text template, it crafts every section based on the evaluated `DetectionSemantics`, the matched `ArchetypeDefinition`, and the generated `RuleEvidenceContract`.

---

## Enterprise SOC Baseline v2.0.0

A critical achievement in AIS 2.0 is the complete elimination of flawed prescriptive instructions in the system-wide baseline.

### What Was Removed:
1. **Prescriptive Confidence Ranges:** Removed all requirements dictating that verdicts must fall between 85% and 95%. Verdict confidence must reflect empirical telemetry sufficiency, not an arbitrary quota.
2. **Blanket RFC-1918 Benign Classification:** Removed the dangerous rule that internal IP communication is presumed harmless. Lateral movement and internal staging routinely leverage RFC-1918 subnets.
3. **Mandatory Malware Hashes for All Alerts:** Removed universal process/hash requirements from the baseline.

### What Was Added (`ENTERPRISE_SOC_BASELINE_V2`):
- Strict instruction to evaluate incidents according to their specific detection archetype.
- Mandatory distinction between established business operations and unapproved data egress.
- Requirement to verify whether observed attributes meet or exceed authoritative detection thresholds.
- Deterministic abstention rules when critical telemetry fields are absent.

---

## The 9-Section Tailored Synthesis Architecture

Every generated policy contains 9 structured sections conforming strictly to the platform's unified compiler specification:

```text
+-------------------------------------------------------------------------+
|                  NINE-SECTION TAILORED POLICY SCHEMA                    |
|                                                                         |
|  Section 1: Common SOC Baseline Protocol (Enterprise SOC Baseline v2)   |
|  Section 2: Rule Metadata & Detection Intent Specification              |
|  Section 3: Evidence Grounding Contract & Mandatory Fields              |
|  Section 4: True Positive (TP) Specific Criteria                        |
|  Section 5: False Positive (FP) Benign Justification Criteria           |
|  Section 6: Required Context & Secondary Telemetry Correlation          |
|  Section 7: Abstention, Escalation & Investigation Boundaries           |
|  Section 8: Structured Output Schema & Confidence Scoring Rules         |
|  Section 9: Authoritative Examples & Boundary Case Disambiguation       |
+-------------------------------------------------------------------------+
```

### Section Synthesis for `NETWORK_EXFILTRATION`

When synthesizing a policy for a network exfiltration rule like `PH_RULE_LARGE_OUTBOUND_XFER`, the generator tailors the sections as follows:

1. **Section 2 (Metadata & Intent):**
   - Explicitly records whether the byte threshold is authoritative or provisional.
   - Declares the monitored entity as `Network Egress Flow`.
2. **Section 3 (Evidence Grounding):**
   - Mandates extraction of `source.ip`, `destination.ip`, and `network.bytes_sent`.
   - Explicitly warns: *"Do not demand endpoint process command lines or malware hashes unless EDR telemetry is correlated in the incident."*
3. **Section 4 (True Positive Criteria):**
   - Evaluates:
     - Confirmed outbound egress direction.
     - Egress volume reaching or exceeding configured threshold within aggregation window.
     - Destination IP/domain is external, unapproved, suspicious, or lacks business justification.
     - Protocol anomalies (e.g. non-standard ports, tunneling).
4. **Section 5 (False Positive Criteria):**
   - Evaluates:
     - Verified scheduled backup jobs to authorized cloud endpoints (e.g. AWS S3, Azure Blob, OneDrive).
     - Approved IT file distribution or CDN synchronization.
     - Verified benign transfer with authorized user sign-off.
     - Overly sensitive rule threshold triggering on standard business spikes.
5. **Section 7 (Abstention & Escalation):**
   - Mandates abstention if byte counts are absent or transfer direction cannot be determined.
   - Demands immediate human escalation if destination IP is associated with known APT C2 infrastructure.

---

## Strict Draft State & Immutability

Generated policies are saved with status `DRAFT`. They are never published directly to active production. Even if generated from verified SIEM semantics, a policy must undergo automated validation via `PolicyQualityValidator` and formal approval by an authorized SOC Lead.
