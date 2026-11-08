# 03. DETECTION ARCHETYPE REGISTRY

## Overview

The `DetectionArchetypeRegistry` (`backend/app/services/detection_archetype_registry.py`) is the taxonomic core of Agent Intelligence Studio 2.0. It defines 12 standardized behavioral archetypes, provides deterministic disambiguation heuristics, and specifies contradiction rules to eliminate archetype cross-contamination.

---

## The 12 Standardized Archetypes

Each archetype represents a distinct investigative paradigm with tailored evidentiary expectations:

| Archetype ID | Name | Primary Investigative Focus | Required Telemetry Fields |
| :--- | :--- | :--- | :--- |
| `PROCESS_EXECUTION` | Process Execution & Command Line | Process lineage, arguments, LOLBins, code execution | `process.name`, `process.cmdline`, `process.parent` |
| `NETWORK_CONNECTION` | Network Connection & C2 | Host-to-external socket connections, ports, C2 IPs | `source.ip`, `destination.ip`, `destination.port` |
| `AUTHENTICATION` | Authentication & Identity | Logons, credential stuffing, brute force, MFA bypass | `user.name`, `auth.status`, `source.ip` |
| `FILE_INTEGRITY` | File System & Integrity | Ransomware encryption, system file modifications | `file.path`, `file.hash`, `process.name` |
| `PERSISTENCE` | Persistence & Auto-Start | Scheduled tasks, service installs, registry run keys | `registry.key`, `service.name`, `user.name` |
| `PRIVILEGE_ESCALATION`| Privilege Escalation | Token manipulation, sudo elevation, admin group adds | `user.source_priv`, `user.target_priv`, `process.name` |
| `DEFENSE_EVASION` | Defense Evasion & Anti-Forensics| Log clearing, AV tampering, process hollowing | `process.target`, `event.action`, `user.name` |
| `CREDENTIAL_ACCESS` | Credential Access & Dumping | LSASS memory scraping, NTDS.dit extraction, DCSync | `process.target`, `file.path`, `user.name` |
| `DISCOVERY` | Internal Discovery & Recon | Port scans, Active Directory queries, subnet sweeps | `network.dest_count`, `process.cmdline`, `source.ip` |
| `LATERAL_MOVEMENT` | Lateral Movement | Remote WMI/PowerShell, PsExec, SMB session hijacking | `source.ip`, `destination.ip`, `auth.logon_type` |
| `NETWORK_EXFILTRATION`| Network Exfiltration & Transfer | Outbound byte volume, aggregation window, egress auth | `source.ip`, `destination.ip`, `network.bytes_sent` |
| `CLOUD_AUDIT` | Cloud Control Plane & Audit | IAM changes, S3 bucket policy exposure, CloudTrail | `cloud.actor`, `cloud.action`, `cloud.resource` |

---

## Disambiguation Heuristics

Rules frequently share keywords that lead naive pattern matchers astray. The registry implements precise disambiguation logic:

### 1. Process Execution vs. Network Beaconing
- **The Problem:** An alert named `Cobalt Strike Beacon Execution` contains the word "Beacon" (typically network) but also "Execution" (process).
- **The Disambiguation Rule:** If a rule title or event type contains strong execution indicators (`PROCESS`, `POWERSHELL`, `CMD`, `COMMAND_LINE`, `LOLBIN`, `EXECUTION`) alongside beacon terms, the registry prioritizes `PROCESS_EXECUTION` or evaluates whether a hybrid process-network contract is needed. If the event type is strictly network traffic (e.g. firewall logs), it maps to `NETWORK_CONNECTION`.

### 2. General Network Connection vs. Network Exfiltration
- **The Problem:** Both involve network sockets. A thresholded bulk egress alert must not be treated as a simple port-connection alert.
- **The Disambiguation Rule:** When rule attributes indicate volume or egress direction (`OUTBOUND`, `EGRESS`, `EXFIL`, `UPLOAD`, `LARGE_TRANSFER`, `BYTES_SENT`), the rule is classified as `NETWORK_EXFILTRATION`. The investigation focus shifts from socket existence to byte thresholds, egress destination reputation, transfer protocol, and business authorization.

---

## Contradiction Rules & Contamination Prevention

To ensure policy purity, each archetype defines strict **contradiction rules** (`contradiction_rules`). If an investigator or LLM introduces prompt instructions that belong to a contradictory domain, Gate G2 flags an `ARCHETYPE_RELEVANCE_MISMATCH`.

### Example: `NETWORK_EXFILTRATION` Contradiction Rules

```python
ArchetypeDefinition(
    archetype_id=ArchetypeId.NETWORK_EXFILTRATION,
    name="Network Exfiltration & Data Transfer",
    expected_evidence_fields=[
        "source.ip", "destination.ip", "destination.port",
        "network.bytes_sent", "network.protocol", "network.duration"
    ],
    irrelevant_concepts=[
        "malware_hash", "registry_key", "service_install",
        "scheduled_task", "lolbin_execution", "process_lineage"
    ],
    contradiction_rules=[
        "Must NOT demand executable malware hashes as mandatory true positive proof.",
        "Must NOT demand process command line or parent lineage unless EDR network correlation is explicitly available.",
        "Must NOT assess registry persistence keys for pure network egress volume alerts.",
        "Must assess transfer direction, destination authorization, outbound volume, and historical baseline."
    ]
)
```

By enforcing these boundaries, AIS 2.0 guarantees that exfiltration policies remain focused on egress volume and destination legitimacy, rather than hallucinating endpoint malware indicators.
