# AIS 2.6a — Report 04: Rule-Aware Verdict Adjudication Framework

## 1. Problem Statement: Root Cause of 0% Decisive Coverage in AIS 2.6
In AIS 2.6, decisive coverage was 0.0% because:
1. **Unrealistic TP Thresholds:** The independent validator required sophisticated APT tradecraft (Mimikatz, Cobalt Strike beacons, LOLBin privilege escalation). When presented with CrowdStrike detections of unauthorized remote access tools (UltraViewer), the validator rejected the TP proposal with `TP_CRITERIA_UNSATISFIED`.
2. **Unrealistic FP Thresholds:** The validator required an authoritative enterprise change ticket (CHG/CR number) or approved software deployment agent (Tanium, SCCM). Routine benign web scripts in Prisma SASE (`jquery.knob.js`, `ss-widget.min.js`) were rejected with `FP_CRITERIA_UNSATISFIED` because web browsing does not generate change tickets.

---

## 2. Rule-Aware Adjudication Architecture

### CrowdStrike Falcon (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)
- **Archetype:** Endpoint Policy Violation & Attack Detection.
- **True Positive Criteria:** Execution of unapproved remote administration software (UltraViewer, TeamViewer, AnyDesk) without documented IT approval or administrative role constitutes an actionable **Policy Violation True Positive**.
- **False Positive Criteria:** Legitimate administrative actions executed by authorized administrators using approved management platforms.
- **Abstention Criteria:** Missing telemetry, ambiguous script invocations, or context window overflow.

### Prisma SASE (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`)
- **Archetype:** Web Security / File Download Analysis.
- **True Positive Criteria:** Executable payloads, ransomware droppers, or suspicious scripts from untrusted external domains.
- **False Positive Criteria:** Common benign static web assets (`.js`, `jquery`, `widget`, `sensum`, `clientlib`, `adrum`, `.css`) downloaded from legitimate CDNs during normal business browsing with clean indicators.
- **Abstention Criteria:** Missing critical telemetry fields, unclassified files, or truncated LLM output.

---

## 3. Strict Safety Invariants Maintained
- Zero tolerance for hallucinated change tickets: Any proposal inventing a fictitious CHG ticket is rejected immediately (`INVENTED_TICKET_DETECTED`).
- Complete prohibition of auto-closure: Autonomous incident closure remains disabled (`auto_incident_closure_allowed=false`).
