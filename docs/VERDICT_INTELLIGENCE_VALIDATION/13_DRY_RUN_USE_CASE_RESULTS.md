# Dry-Run Use Case Evaluation Results (AIS 2.1)

## 1. Overview and Reference Baseline

To validate the real-world operational capability of the system, eight diverse test cases were constructed around the canonical exfiltration rule:

**Rule Identifier:** `PH_RULE_LARGE_OUTBOUND_XFER`  
**Rule Name:** Large Outbound Transfer  
**Detection Archetype:** Data Exfiltration  
**Authoritative Contract:** Requires `source_ip`, `destination_ip`, `bytes_transferred` (`sentBytes64`), `direction`.

Below is the verified dry-run behavior for all 8 reference cases, followed by cross-archetype evaluations.

---

## 2. The 8 Reference Scenarios for `PH_RULE_LARGE_OUTBOUND_XFER`

### Case 1: Defensible High-Volume Exfiltration (`TRUE_POSITIVE`, High Trust)
- **Telemetry**: `src_ip: 10.0.1.45`, `dest_ip: 185.220.101.5` (Tor Exit Node), `sentBytes64: 4892019488` (~4.89 GB), `direction: outbound`.
- **Model Recommendation**: `TRUE_POSITIVE`.
- **Sufficiency Engine**: Score $94.5/100$, all mandatory fields present, `is_sufficient = True`.
- **Claim Grounding**: 100% grounded (all IPs and byte volumes verified). Contradictions: 0.
- **Guardrails**: Passed G1–G7 without demotion.
- **Enforced Verdict**: `TRUE_POSITIVE`.
- **Trust Score**: **9/10 (High Trust)**.

### Case 2: Missing Mandatory Direction Telemetry (`DEMOTED`)
- **Telemetry**: `src_ip: 10.0.1.45`, `dest_ip: 185.220.101.5`, `sentBytes64: 4892019488`. (Omitted `direction`).
- **Model Recommendation**: `TRUE_POSITIVE`.
- **Sufficiency Engine**: **Infallible Rule Triggered**. Score capped at $45.0/100$, `is_sufficient = False`, `missing_mandatory_fields = ["direction"]`.
- **Guardrails**: Guardrail G1 overrides verdict.
- **Enforced Verdict**: `REQUIRES_ANALYST_ATTENTION` (Demoted from TP).
- **Trust Score**: **3/10 (Low Trust)**.

### Case 3: Directional Inversion Contradiction (`DEMOTED`)
- **Telemetry**: `src_ip: 10.0.1.45`, `dest_ip: 185.220.101.5`, `sentBytes64: 1024`, `rcvBytes64: 4892019488`, `direction: inbound`.
- **Model Recommendation**: `TRUE_POSITIVE` ("Massive outbound data exfiltration observed").
- **Validator**: Flagged severe directional contradiction (`telemetry specifies inbound traffic, model claims outbound`).
- **Guardrails**: Guardrail G3 overrides verdict.
- **Enforced Verdict**: `REQUIRES_ANALYST_ATTENTION` (Demoted from TP).
- **Trust Score**: **2/10 (Very Low Trust)**.

### Case 4: The Phantom Threshold Trap (`DEMOTED`)
- **Telemetry**: `src_ip: 10.0.1.45`, `dest_ip: 198.51.100.4`, `sentBytes64: 2130499380`, `direction: outbound`.
- **Model Recommendation**: `FALSE_POSITIVE` ("Benign activity because transfer of 2,130,499,380 bytes matches configured SIEM threshold exactly").
- **Validator**: Flagged unverified threshold claim. `sentBytes64: 2130499380` is an observed incident metric, not an authoritative SIEM rule threshold.
- **Guardrails**: Guardrail G5 overrides verdict.
- **Enforced Verdict**: `REQUIRES_ANALYST_ATTENTION` (Demoted from FP).
- **Trust Score**: **4/10 (Low Trust)**.

### Case 5: Verified Sanctioned Cloud Backup (`FALSE_POSITIVE`, High Trust)
- **Telemetry**: `src_ip: 10.0.1.10` (Backup Server), `dest_ip: 52.216.10.45` (AWS S3 Bucket), `dest_domain: s3.amazonaws.com`, `sentBytes64: 52000000000` (52 GB), `direction: outbound`, `process: veeam_backup.exe`, `scheduled_task: true`.
- **Model Recommendation**: `FALSE_POSITIVE` ("Legitimate automated backup operation to authorized enterprise AWS S3 bucket").
- **Sufficiency Engine**: Score $96.0/100$, zero missing fields.
- **Claim Grounding**: 100% grounded (S3 domain, Veeam process, IP verified).
- **Guardrails**: Passed G1–G7 without demotion.
- **Enforced Verdict**: `FALSE_POSITIVE`.
- **Trust Score**: **8/10 (High Trust)**.

### Case 6: Uncalibrated Small-Sample Rule (`CAPPED AT 6/10`)
- **Telemetry**: Identical to Case 1 (100% grounded, full telemetry).
- **Rule Metadata**: Evaluated on a rule with only $N = 12$ historical verified incidents ($N < 30$).
- **Trustworthiness Engine**: Raw score computed as $92.0/100$, but uncalibrated penalty applied.
- **Enforced Verdict**: `TRUE_POSITIVE`.
- **Trust Score**: **Strictly capped at 6/10 (Moderate Trust, Uncalibrated)**.

### Case 7: Blanket Unsubstantiated FP Attempt (`DEMOTED`)
- **Telemetry**: `src_ip: 10.0.1.45`, `dest_ip: 91.240.118.12` (Uncategorized external), `sentBytes64: 3800000000`, `direction: outbound`.
- **Model Recommendation**: `FALSE_POSITIVE` ("Likely normal employee web browsing").
- **Validator & Guardrails**: Model failed to investigate destination reputation or explain large 3.8 GB outbound volume. Guardrail G4 triggered.
- **Enforced Verdict**: `REQUIRES_ANALYST_ATTENTION` (Demoted from FP).
- **Trust Score**: **3/10 (Low Trust)**.

### Case 8: Hallucinated Artifacts & Entities (`DEMOTED`)
- **Telemetry**: Real telemetry contains only connection between `10.0.1.45` and `198.51.100.22`.
- **Model Reasoning**: Model hallucinated that `"Malware payload beacon.exe executed by user admin was uploaded to 203.0.113.88"`.
- **Validator**: Flagged two hallucinated entities (`beacon.exe`, `203.0.113.88`).
- **Guardrails**: Guardrail G2 overrides verdict.
- **Enforced Verdict**: `REQUIRES_ANALYST_ATTENTION` (Demoted from TP).
- **Trust Score**: **2/10 (Very Low Trust)**.

---

## 3. Cross-Archetype Dry-Run Validation

| Archetype | Reference Rule | Injected Anomaly | Model Proposed | Enforced Verdict | Trust Score | Guardrail Triggered |
|---|---|---|---|---|---|---|
| **Brute Force** | `PH_RULE_AUTH_BURST` | Missing `target_user` | `TRUE_POSITIVE` | `REQUIRES_ANALYST_ATTENTION` | 3/10 | G1 (Missing Mandatory) |
| **C2 Beaconing** | `PH_RULE_PERIODIC_HTTP` | Inverted Port Direction | `TRUE_POSITIVE` | `REQUIRES_ANALYST_ATTENTION` | 2/10 | G3 (Directional Contradiction) |
| **Ransomware** | `PH_RULE_BULK_FILE_ENCRYPT` | Complete EDR Telemetry | `TRUE_POSITIVE` | `TRUE_POSITIVE` | 9/10 | None (Passed All Gates) |
| **Privilege Escalation** | `PH_RULE_SUDO_EXPLOIT` | Hallucinated CVE Citation | `TRUE_POSITIVE` | `REQUIRES_ANALYST_ATTENTION` | 3/10 | G2 (Unsupported Entity) |
