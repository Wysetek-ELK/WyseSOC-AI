# 04. EVIDENCE REQUIREMENT MAPPING

## Overview

The `EvidenceRequirementMapper` (`backend/app/services/evidence_requirement_mapper.py`) acts as the compiler bridge between abstract detection semantics and enforceable **Evidence Contracts**. 

In Phase 2 of AI Verdict, Evidence Contracts were established to deterministically verify whether required telemetry fields were present before allowing LLM inference. In AIS 2.0, this mapper dynamically analyzes the rule's archetype, authoritative conditions, and observed data source capabilities to construct a four-tier contract:

```text
+-------------------------------------------------------------------------+
|                  FOUR-TIER EVIDENCE REQUIREMENT TIERS                   |
|                                                                         |
|  1. CORE REQUIREMENTS (Mandatory / Non-Negotiable)                      |
|     - Absence immediately halts inference and forces safe abstention.   |
|     - Example: source.ip, destination.ip, network.bytes_sent            |
|                                                                         |
|  2. CONDITIONAL REQUIREMENTS (Required if Specific Conditions Met)      |
|     - Example: If destination is cloud storage -> bucket_name required. |
|     - Example: If TLS encrypted -> tls.sni / cert.subject required.     |
|                                                                         |
|  3. OPTIONAL ENRICHMENT (Helpful for Triage, Never Blocks)              |
|     - Example: geo_ip, whois_org, threat_intel_reputation               |
|                                                                         |
|  4. EXPLICITLY UNAVAILABLE / UNSUPPORTED (Blocked from Verification)    |
|     - Identifies fields that the telemetry source cannot provide.       |
|     - Prevents policy instructions from demanding non-existent data.    |
+-------------------------------------------------------------------------+
```

---

## Mapping Logic by Archetype

The mapper executes deterministic rule matching:

### 1. `NETWORK_EXFILTRATION`
- **Core Requirements:**
  - `source.ip`: The internal transmitting host.
  - `destination.ip`: The external recipient.
  - `network.bytes_sent`: Actual outbound payload volume.
- **Conditional Requirements:**
  - `network.duration`: Required if threshold is time-windowed (e.g. rate-based transfer).
  - `destination.port`: Required if protocol identification is ambiguous.
- **Optional Requirements:**
  - `threat_intel.dest_reputation`: External IP reputation score.
  - `destination.domain` or `tls.sni`: Resolved hostname for cloud services.
- **Explicitly Unavailable:**
  - `process.cmdline`, `process.parent_name`, `file.hash` (when data source is a pure network firewall / NetFlow tap).

### 2. `PROCESS_EXECUTION`
- **Core Requirements:**
  - `process.name`: The executed binary name.
  - `process.cmdline`: Full invocation arguments.
  - `host.name` or `host.ip`: Target endpoint.
- **Conditional Requirements:**
  - `process.parent_name`: Required if execution involves LOLBins (e.g. `cmd.exe` spawned by `word.exe`).
  - `process.hash`: Required if binary originates from non-standard paths.
- **Optional Requirements:**
  - `user.name`: Initiating security context.
- **Explicitly Unavailable:**
  - `network.bytes_sent` (unless EDR includes network flow telemetry).

---

## Contract Alignment Verification

When an Evidence Contract is generated via `map_requirements()`, the resulting structure matches the runtime `RuleEvidenceContract` schema:

```python
RuleEvidenceContract(
    rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
    archetype="NETWORK_EXFILTRATION",
    mandatory_fields=[
        EvidenceFieldRequirement(
            field_name="source.ip",
            field_type="string",
            description="Originating internal host IP address",
            is_mandatory=True,
            validation_rule="is_ip_address"
        ),
        EvidenceFieldRequirement(
            field_name="destination.ip",
            field_type="string",
            description="External egress destination IP address",
            is_mandatory=True,
            validation_rule="is_ip_address"
        ),
        EvidenceFieldRequirement(
            field_name="network.bytes_sent",
            field_type="integer",
            description="Total outbound bytes transmitted",
            is_mandatory=True,
            validation_rule="is_positive_integer"
        )
    ],
    optional_fields=[...],
    contract_status="DRAFT"  # Synchronized to APPROVED only upon policy approval
)
```

This dynamic contract guarantees that the LLM is never evaluated against data that was never collected, nor can a policy demand evidence that the telemetry feed cannot supply.
