# AI VERDICT — PHASE 2: EVIDENCE CONTRACT DESIGN
## 03. RULE-SPECIFIC EVIDENCE CONTRACTS (P2-REQ-02)

---

### 1. Conceptual Framework
In AI Verdict, a detection rule cannot be evaluated based on arbitrary LLM preferences. Each rule has a **Machine-Verifiable Evidence Contract** (`RuleEvidenceContract`) that specifies:
1. What evidence fields are mandatory for `TRUE_POSITIVE` vs `FALSE_POSITIVE`.
2. Which fields are **critical** (their absence immediately blocks decisive triage).
3. Specific criteria and contradiction rules.
4. Contract status (`APPROVED` vs `UNVERIFIED`), which is strictly bound to the approval state of the rule's active prompt in Agent Intelligence Studio.

---

### 2. Evidence Contract Schema (`app/schemas/evidence_contract.py`)

```python
class EvidenceFieldRequirement(BaseModel):
    field: str
    evidence_type: str
    required_for_tp: bool = True
    required_for_fp: bool = False
    critical: bool = True
    description: str = ""

class RuleEvidenceContract(BaseModel):
    contract_id: str
    rule_id: str
    prompt_version_id: Optional[str] = None
    version_number: int = 1
    status: str = "UNVERIFIED"  # APPROVED, DRAFT, UNVERIFIED
    detection_archetype: str  # PROCESS_EXECUTION, NETWORK_CONNECTION, FILE_MALWARE, AUTHENTICATION, GENERIC
    required_evidence: List[EvidenceFieldRequirement]
    tp_criteria: List[str] = Field(default_factory=list)
    fp_criteria: List[str] = Field(default_factory=list)
    contradiction_rules: List[Dict[str, Any]] = Field(default_factory=list)
    on_critical_missing_evidence: str = "REQUIRES_ATTENTION"
```

---

### 3. Supported Detection Archetypes

#### Archetype 1: `PROCESS_EXECUTION`
- **Applicable Rules:** LOLBins, PowerShell cradles, cmd.exe execution, script engines, process injection.
- **Required Fields:**
  - `process.command_line` (Critical = True, TP = True, FP = False)
  - `process.name` (Critical = False, TP = True, FP = True)
  - `user.name` (Critical = False, TP = True, FP = False)
  - `process.parent_name` (Critical = False, TP = False, FP = False)
- **Contradiction Rules:** `NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION` (claiming malicious execution without command line or parent lineage).

#### Archetype 2: `NETWORK_CONNECTION`
- **Applicable Rules:** C2 beaconing, outbound exfiltration, port scans, DNS tunneling.
- **Required Fields:**
  - `network.destination_ip` (Critical = True, TP = True, FP = True)
  - `network.source_ip` (Critical = False, TP = True, FP = True)
  - `network.destination_port` (Critical = False, TP = True, FP = False)
- **Contradiction Rules:** `EXTERNAL_C2_ON_LOOPBACK` (claiming external C2 when destination is loopback `127.0.0.1` or internal subnet).

#### Archetype 3: `FILE_MALWARE`
- **Applicable Rules:** Antivirus detection, ransomware binaries, trojan download.
- **Required Fields:**
  - `file.hash_sha256` (Critical = True, TP = True, FP = False)
  - `endpoint.hostname` (Critical = False, TP = True, FP = True)
- **Contradiction Rules:** `MALWARE_EXECUTION_WITHOUT_FILE_HASH`.

#### Archetype 4: `AUTHENTICATION`
- **Applicable Rules:** Brute force login, password spray, Kerberoasting, privilege escalation.
- **Required Fields:**
  - `user.name` (Critical = True, TP = True, FP = True)
  - `network.source_ip` (Critical = False, TP = True, FP = False)
  - `endpoint.hostname` (Critical = False, TP = True, FP = False)

#### Archetype 5: `GENERIC`
- **Applicable Rules:** Generic sensor alerts, policy events, unmapped signatures.
- **Required Fields:**
  - `security.event_type` (Critical = True, TP = True, FP = True)

---

### 4. Policy Approval Binding
The contract derives its status strictly from `PromptVersion.status`:
- `PromptVersion.status == "APPROVED"` $\rightarrow$ `RuleEvidenceContract.status = "APPROVED"`
- `PromptVersion.status != "APPROVED"` $\rightarrow$ `RuleEvidenceContract.status = "UNVERIFIED"`
- If no prompt version is active $\rightarrow$ `RuleEvidenceContract.status = "UNVERIFIED"`

An `UNVERIFIED` contract guarantees that the independent validator will refuse decisive triage and route the incident to `REQUIRES_ATTENTION`.

