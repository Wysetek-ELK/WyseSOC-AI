# AIS 2.6c — Workstream 9: Rule Semantics, Authorization & Evidence Correctness
**Document ID:** `08_RULE_SEMANTICS_AUTHORIZATION_AND_EVIDENCE_CORRECTNESS.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Rule Families:** CrowdStrike Suspicious Activity & Prisma SASE Suspicious File Threat  
**Artifacts Generated:**  
- `docs/AIS_2_6c/RULE_VERDICT_SEMANTICS_MATRIX.json`  
- `docs/AIS_2_6c/COUNTERFACTUAL_VALIDATION_RESULTS.json`  

---

## 1. Rule Semantics & Evidentiary Boundaries

A core finding of Phase AIS 2.6b was that the model conflated **rule trigger detection** with **confirmed security breach**, and **unknown IT authorization** with **unauthorized malicious activity**.

### 1.1 CrowdStrike Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)
- **Observed Behavior:** Execution of `UltraViewer_Service.exe` or `MEGAsync.exe` launched via Windows Service Control Manager (`services.exe`).
- **Trigger Logic:** Custom Intelligence Indicator of Attack (IoA) rule matched on known remote management software.
- **Evidentiary Boundary:**
  - Observing `UltraViewer_Service.exe` proves software execution.
  - It does **not** prove malicious intrusion, policy violation, or compromise.
  - In FortiSIEM event telemetry, enterprise change authorization is **unknown** (ITSM tickets are never present in raw syslog alerts).
  - The model must report `REQUIRES_ATTENTION` when authorization cannot be verified, rather than asserting that the execution was "unauthorized".

### 1.2 Prisma SASE Suspicious File Threat (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`)
- **Observed Behavior:** Gateway HTTP transfer of static JavaScript web libraries (`ss-widget.min.js`, `clientlib-site.min.js`, `jquery.knob.js`, etc.) or PE binaries (`update.exe`).
- **Trigger Logic:** Palo Alto Prisma SASE perimeter gateway flagged the transfer.
- **Evidentiary Boundary:**
  - Common filenames and CDN destinations are contextual evidence, not conclusive proof of benignness or maliciousness.
  - Standard JavaScript libraries from reputable CDNs without secondary payloads or exploit artifacts represent normal web browsing (`FALSE_POSITIVE` under rule taxonomy).
  - Executable binaries like `update.exe` (`132591888`) lack sandbox detonation reports in SIEM events; they must be routed to `REQUIRES_ATTENTION` rather than guessed as benign or malicious.

---

## 2. Counterfactual Validation Scenarios

To prove that the pipeline does not hardcode filename-based heuristics, we implemented counterfactual test scenarios:

| Test Case | Telemetry Variation | Expected Verdict | Reasoning Integrity Invariant |
|---|---|---|---|
| **CF-CS-01** | `UltraViewer` + Approved Change Ticket `CHG-8821` | `FALSE_POSITIVE` | Legitimate maintenance pre-authorized |
| **CF-CS-02** | `UltraViewer` + Ransomware Precursor (`vssadmin delete shadows`) | `TRUE_POSITIVE` | Active adversary tradecraft observed |
| **CF-CS-03** | `UltraViewer` + Falcon Blocked=True + Zero Authorization Context | `REQUIRES_ATTENTION` | Unknown authorization requires SOC L1 check |
| **CF-PRISMA-01**| `jquery.knob.js` from CDN + Clean HTTP GET | `FALSE_POSITIVE` | Standard benign web UI asset |
| **CF-PRISMA-02**| `jquery.knob.js` + C2 Beaconing to Dynamic DNS IP | `TRUE_POSITIVE` | Malicious masquerading script |
| **CF-PRISMA-03**| `update.exe` from Unknown IP + Zero Sandbox Detonation | `REQUIRES_ATTENTION` | Missing mandatory WildFire report |

---

## 3. Deliverable References

- Rule Verdict Semantics Matrix: [RULE_VERDICT_SEMANTICS_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/RULE_VERDICT_SEMANTICS_MATRIX.json)
- Counterfactual Results: [COUNTERFACTUAL_VALIDATION_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/COUNTERFACTUAL_VALIDATION_RESULTS.json)
