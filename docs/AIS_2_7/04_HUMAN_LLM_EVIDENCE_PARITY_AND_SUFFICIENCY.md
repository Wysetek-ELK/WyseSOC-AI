# 04 — Human vs LLM Evidence Parity & Sufficiency

**Phase:** AIS 2.7 (Workstream 4)

---

## 1. Evidence Parity Summary

| Stratum | Count | Available to Both Human & LLM | Human-Only Evidence / Context | Unavailable to Both |
|---|---:|---|---|---|
| **CrowdStrike `UltraViewer_Service.exe`** | 9 | Full CrowdStrike `EppDetectionSummaryEvent` attributes (process, command line, SHA-256, host, user, `ProcessBlocked`/`KillProcess` flags) + rule definition | Implicit tenant rule policy (Tosoh CrowdStrike rule blocks UltraViewer) | ITSM change ticket / authorization record; external TI feed |
| **CrowdStrike `MEGAsync.exe` (`132501348`)** | 1 | Full CrowdStrike event (`MEGAsync.exe` attempting COM/registry modification on Falcon sensor, MITRE `T1562.001`, Severity 70, `RegistryOperationBlocked=true`, SHA-256 `c9eee5a5...`) | **External hash reputation lookup** ("executable hash was checked and found to be clean") + behavioral confirmation | Executable digital signature / VT reputation inside SIEM payload |
| **Prisma SASE (`*.js`, `update.exe`)** | 10 | Palo Alto Prisma SASE `THREAT-file` syslog JSON (`Source User`, `Source IP`, `Destination IP`, `File Name`, `Application Name`, `Action=alert`) + rule definition | Client historical FP feedback referenced in human notes | **File SHA-256/MD5 hash, full HTTP URL, payload detonation** |

---

## 2. Critical Parity Findings

1. **`132501348` (`MEGAsync.exe`) — Human-Only Evidence Dependency:** In the raw CrowdStrike payload, `MEGAsync.exe` triggers `Defense Evasion / Disable or Modify Tools (T1562.001)` at Severity 70 (`High`) for attempting to modify a Falcon sensor COM object. The human reviewer classified it `FALSE_POSITIVE` after externally checking the SHA-256 hash reputation and verifying legitimate MEGA behavior. Without external reputation or authorization context, an evidence-grounded LLM cannot verify cleanliness from static logs alone.
2. **Prisma SASE (10 incidents):** Both human and LLM lack file hashes and full URLs; the human reviewer appropriately classified all 10 as `INCONCLUSIVE`. An LLM evaluated on evidence-grounded reasoning should abstain (`REQUIRES_ATTENTION`) rather than hallucinate benignness or compromise.

Artifacts: [EVIDENCE_AVAILABILITY_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/EVIDENCE_AVAILABILITY_MATRIX.json) and [HUMAN_ONLY_EVIDENCE_DEPENDENCIES.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/HUMAN_ONLY_EVIDENCE_DEPENDENCIES.json).
