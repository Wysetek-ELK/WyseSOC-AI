# 16. CASE STUDY: LARGE OUTBOUND TRANSFER (`PH_RULE_LARGE_OUTBOUND_XFER`)

## 1. Case Background & Initial State

**Rule Identifier:** `PH_RULE_LARGE_OUTBOUND_XFER`  
**Rule Name:** Large Outbound Transfer  
**Detection Category:** Exfiltration  
**Data Source:** MSSP-Primary  
**Severity:** MEDIUM  
**Initial Incident Metadata:** `{"sentBytes64": 2130499380}`

The rule was automatically synchronized into the database via an incident export feed. The export provided only the rule identifier, name, and an observed event payload containing `sentBytes64 = 2,130,499,380` (~2.13 GB). No authoritative SIEM rule condition or XML definition was initially attached.

---

## 2. Studio 1.0 Failure Analysis

Under Prompt Studio 1.0, the system generated a generic policy with critical defects:
1. **False Threshold Assignment:** The system treated `2130499380` as the authoritative detection threshold.
2. **Archetype Contamination:** The prompt instructed the LLM:
   - *"Inspect suspicious executable hashes and verify on VirusTotal."*
   - *"Analyze parent process lineage and command-line parameters (cmd.exe, powershell.exe)."*
   - *"Inspect autorun registry keys and scheduled tasks for persistence."*
3. **Missing Investigation Focus:** The policy completely omitted:
   - Outbound transfer direction (Egress vs Ingress).
   - Egress destination IP/domain authorization.
   - Transfer protocol and duration.
   - Comparison against historical host egress baselines.
   - Legitimate business transfers (e.g. cloud backups).
4. **Flawed Baseline:** The baseline forced the LLM to output 85–95% confidence and to classify RFC-1918 traffic as automatically benign.

---

## 3. AIS 2.0 Step-by-Step Resolution

### Step 1: Semantics Ingestion without Authoritative XML
- Ingested via `RuleIntelligenceAnalyzer.analyze_rule(rule)`.
- **Classification:** Candidate archetype correctly identified as `NETWORK_EXFILTRATION`.
- **Status:** Evaluated as `SemanticsDefinitionStatus.INCOMPLETE`.
- **Key Outcome:** The observed `sentBytes64` value was recorded strictly as observed telemetry, **not** as a detection threshold (`threshold = None`).
- **Missing Requirements Logged:**
  - `Authoritative SIEM rule definition not ingested.`
  - `Aggregation window and threshold conditions unverified.`

### Step 2: Quality Validation of Studio 1.0 Legacy Policy
- Evaluated against `PolicyQualityValidator`:
  - **Gate G1 (Integrity):** **FAILED** (`DETECTION_DEFINITION_INCOMPLETE`).
  - **Gate G2 (Relevance):** **FAILED** (`ARCHETYPE_RELEVANCE_MISMATCH: Malware execution and process lineage instructions found in NETWORK_EXFILTRATION policy`).
  - **Overall Score:** $40.0 / 100.0$ (Capped at 45.0 by Hard-Gate Override).
  - **Approval Status:** `approval_eligible = False`.
  - **Outcome:** The system successfully blocked approval of the ungrounded policy.

### Step 3: Authoritative XML Ingestion
The SOC Lead provided the authoritative FortiSIEM rule XML:
```xml
<rule id="PH_RULE_LARGE_OUTBOUND_XFER">
  <name>Large Outbound Transfer</name>
  <category>Exfiltration</category>
  <condition>
    <attribute>sentBytes64</attribute>
    <operator>GREATER_THAN</operator>
    <value>1073741824</value>
    <unit>bytes</unit>
    <window>3600</window>
    <groupBy>srcIp,destIp</groupBy>
  </condition>
</rule>
```
- Re-analyzed via `RuleIntelligenceAnalyzer`:
  - `threshold` set to `1073741824.0` (1.0 GB).
  - `threshold_unit` set to `bytes`.
  - `aggregation_window` set to `3600s` (1 hour).
  - `grouping_keys` set to `["srcIp", "destIp"]`.
  - `definition_status` updated to `VERIFIED`.

### Step 4: Intelligent Policy Synthesis & Contract Generation
- `PolicyGenerationService` generated an exfiltration-tailored 9-section policy:
  - Focused strictly on network egress, destination authorization, byte volume, and backup validation.
  - Omitted all irrelevant malware/hash instructions.
- `EvidenceRequirementMapper` generated the Evidence Contract:
  - Mandatory: `source.ip`, `destination.ip`, `network.bytes_sent`.
  - Conditional: `network.duration`, `destination.port`.
  - Optional: `threat_intel.dest_reputation`, `tls.sni`.
  - Prohibited: `process.cmdline`, `file.hash`.

### Step 5: Final Validation & Production Approval
- Re-evaluated via `PolicyQualityValidator`:
  - All 8 gates (G1–G8) evaluated as **PASSED**.
  - Historical simulation verified (sample count waived via `INSUFFICIENT_DATA` warning).
  - Overall Quality Score: **92.0 / 100.0** (Emerald Tier).
  - `approval_eligible = True`.
- SOC Lead approved version:
  - Version 1 promoted to `APPROVED`.
  - Evidence Contract atomically promoted to `APPROVED`.
  - Cryptographic audit event logged with HMAC signature.
