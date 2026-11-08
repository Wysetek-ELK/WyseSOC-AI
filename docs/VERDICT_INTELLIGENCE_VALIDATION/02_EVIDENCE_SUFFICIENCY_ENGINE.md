# Evidence Sufficiency Engine (AIS 2.1)

## 1. Core Purpose and Philosophy

In automated security operations, **the presence of high model confidence does not imply the presence of adequate evidence**. A language model presented with half of a log event will frequently generate an assertive verdict based on partial or misleading details.

The **Evidence Sufficiency Engine** (`backend/app/services/evidence_sufficiency_engine.py`) acts as a deterministic pre-requisite gate. It quantifies whether the raw SIEM telemetry provided to the system contains sufficient, integral, and temporally coherent data to justify making an automated classification (`TRUE_POSITIVE` or `FALSE_POSITIVE`).

---

## 2. The 4-Tier Weighting Formula

The engine calculates an **Evidence Sufficiency Score (0–100)** across four distinct dimensions:

$$\text{Sufficiency Score} = 0.40 \times C + 0.25 \times I + 0.20 \times T + 0.15 \times F$$

Where:
- **$C$ = Evidence Coverage (40%)**:
  Ratio of present required evidence fields to total expected fields defined in the rule's `RuleEvidenceContract` or inferred from its `DetectionArchetype`.
- **$I$ = Source Reliability & Integrity (25%)**:
  Telemetry provenance score based on data source pedigree (MSSP, EDR, Firewall, NetFlow, Cloud Audit) and raw field structural integrity (absence of corrupted payloads, malformed JSON, truncated records).
- **$T$ = Temporal Consistency & Sequencing (20%)**:
  Verification that event timestamps are logically ordered (e.g., connection start precedes connection end, authentication precedes egress) and event intervals align with expected detection windows.
- **$F$ = Context Freshness & Completeness (15%)**:
  Presence of supporting context such as reverse DNS resolution, host asset metadata, user identity mappings, and historical baseline counters.

---

## 3. The Infallible Mandatory Field Rule

> [!IMPORTANT]
> **Zero Override Rule:** High overall coverage or strong model confidence can **NEVER** compensate for a missing mandatory evidence field.

If an incident payload is missing even a single field designated as `mandatory` in the `RuleEvidenceContract`:
1. `is_sufficient` is strictly set to `False`.
2. The overall sufficiency score is hard-capped at a maximum of `49.0` (even if coverage, integrity, and freshness would otherwise yield an 80+ score).
3. The specific missing fields are explicitly appended to `missing_mandatory_fields`.
4. Downstream `VerdictGuardrailsEngine` triggers **Guardrail G1**, automatically demoting any proposed `TRUE_POSITIVE` or `FALSE_POSITIVE` verdict to `REQUIRES_ANALYST_ATTENTION`.

### Illustrative Scenario:
In `PH_RULE_LARGE_OUTBOUND_XFER` (Exfiltration Archetype):
- Mandatory fields: `source_ip`, `destination_ip`, `bytes_transferred` (or `sentBytes64`), `direction`.
- If an incident contains `source_ip`, `destination_ip`, `bytes_transferred`, user context, threat intel, and clean timestamps, but omits **`direction`**:
  - Raw coverage: $5/6 = 83\%$.
  - Without the Infallible Rule, the score might be $\sim 85/100$.
  - **With the Infallible Rule**: The engine detects missing `direction`, sets `is_sufficient = False`, caps score to `45.0`, and marks the case as `REQUIRES_ANALYST_ATTENTION`.

---

## 4. Telemetry Field Alias Normalization

SIEM vendors and collectors use divergent naming conventions for identical logical telemetry concepts. The `EvidenceSufficiencyEngine` utilizes an automated alias dictionary to normalize fields before contract evaluation:

```python
FIELD_ALIASES = {
    "source_ip": ["src_ip", "srcip", "sourceip", "sourceIP", "src", "client_ip"],
    "destination_ip": ["dest_ip", "dst_ip", "dstip", "destinationip", "destIP", "target_ip"],
    "destination_port": ["dest_port", "dst_port", "dstport", "destinationPort", "target_port"],
    "bytes_transferred": ["sentBytes64", "sent_bytes", "bytes_out", "outbound_bytes", "bytes"],
    "direction": ["flow_direction", "traffic_direction", "direction_type"],
    "process_name": ["process", "proc_name", "image", "file_name"],
    "process_command_line": ["cmdline", "command_line", "process_cmd", "arguments"],
    "user": ["username", "user_name", "account_name", "src_user"],
}
```

This guarantees that fields such as `sentBytes64: 2130499380` are correctly recognized as `bytes_transferred` without false rejections caused by vendor-specific naming conventions.

---

## 5. Archetype Dynamic Fallbacks

When a custom rule does not have an explicit `RuleEvidenceContract` pre-compiled in the database, the engine dynamically falls back to the archetype definition in `DetectionArchetypeRegistry`:
- **Exfiltration Archetype**: Enforces mandatory `source_ip`, `destination_ip`, `bytes_transferred`, `direction`.
- **Brute Force Archetype**: Enforces mandatory `target_user` (or `user`), `source_ip`, `failure_count`.
- **C2 / Beaconing Archetype**: Enforces mandatory `destination_ip` (or domain), `connection_frequency` (or interval count), `payload_size`.
- **Ransomware Archetype**: Enforces mandatory `process_name`, `file_modifications_count`, `target_directory`.

This fallback ensures 100% test coverage and robust behavior across all 2,000+ SIEM detection rules.
