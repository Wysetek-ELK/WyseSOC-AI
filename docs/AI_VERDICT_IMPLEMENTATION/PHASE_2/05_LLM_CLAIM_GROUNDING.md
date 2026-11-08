# AI VERDICT — PHASE 2: LLM CLAIM GROUNDING
## 05. STRUCTURED LLM EVIDENCE CLAIMS & CLAIM GROUNDING (P2-REQ-04)

---

### 1. The Hallucination Problem in SOC AI
Language models can produce persuasive analytical justifications citing plausible-sounding facts that were never present in the actual telemetry. For example, a model classifying an alert as a `TRUE_POSITIVE` might state:
> *"The endpoint initiated outbound command-and-control communication to Cobalt Strike server at 198.51.100.44 and dropped payload with SHA-256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855."*

If the SIEM record only observed an internal `cmd.exe` process without network traffic or file hashes, the model has **fabricated critical indicators of compromise (IOCs)**.

Accepting such a verdict is dangerous. `ModelClaimExtractor` provides independent verification that every factual assertion made by the model is backed by canonical evidence.

---

### 2. Claim Grounding Schema (`app/schemas/evidence_claim.py`)

```python
class ModelSupportingClaim(BaseModel):
    claim_type: str  # PROCESS_EXECUTION, NETWORK_CONNECTION, FILE_HASH, USER_CONTEXT, etc.
    evidence_ids: List[str] = Field(default_factory=list)
    field: str  # Canonical telemetry field, e.g. process.command_line
    asserted_value: Any  # Value asserted by the model
    is_grounded: bool = False  # True if verified against real canonical evidence
    grounding_status: str  # GROUNDED, EVIDENCE_REFERENCE_NOT_FOUND, EVIDENCE_VALUE_MISMATCH, FIELD_NOT_FOUND, CLAIM_NOT_VERIFIABLE
    matched_evidence_id: Optional[str] = None
    actual_observed_value: Optional[str] = None
    reason: str = ""

class ClaimGroundingResult(BaseModel):
    incident_id: str
    total_claims: int
    grounded_claims: int
    unsupported_claims: int
    grounding_ratio: float = Field(0.0, ge=0.0, le=1.0)
    claims: List[ModelSupportingClaim] = Field(default_factory=list)
    unsupported_claim_details: List[Dict[str, Any]] = Field(default_factory=list)
    has_hallucinations: bool = False
```

---

### 3. Claim Extraction Architecture

The extractor operates in two complementary modes:

#### Mode A: Structured JSON Claims (Model cites Evidence IDs)
When the model outputs structured JSON with `supporting_claims`:
```json
{
  "claim_type": "PROCESS_EXECUTION",
  "evidence_ids": ["EV-INC-1001-EVT1-process_name"],
  "field": "process.name",
  "asserted_value": "powershell.exe"
}
```
1. Verifies that `evidence_id` exists in the current incident's canonical records.
2. Rejects cited IDs belonging to other incidents (`EVIDENCE_REFERENCE_NOT_FOUND`).
3. Compares `asserted_value` against `actual_observed_value` in the canonical record. If different, flags `EVIDENCE_VALUE_MISMATCH`.

#### Mode B: Unstructured Free-Text Regex Harvesting
For legacy responses or models returning prose:
1. Regex scans for:
   - SHA-256 hashes: `\b[a-fA-F0-9]{64}\b`
   - MD5 hashes: `\b[a-fA-F0-9]{32}\b`
   - IPv4 addresses: `\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b`
   - Executable binaries: `\b([a-zA-Z0-9_\-\.]+\.(?:exe|dll|ps1|bat|sh|bin))\b`
2. Each extracted entity is checked against the incident's canonical records.
3. If an entity was never observed in incident telemetry, it is marked `CLAIM_NOT_VERIFIABLE` and `has_hallucinations = True`.

---

### 4. Grounding Metrics Calculation
$$\text{Grounding Ratio} = \frac{\text{Grounded Claims}}{\text{Total Claims}}$$
- If $\text{Total Claims} = 0$, $\text{Grounding Ratio} = 1.0$.
- If $\text{Unsupported Claims} > 0$, `has_hallucinations = True`.

Any decisive verdict (`TRUE_POSITIVE` or `FALSE_POSITIVE`) with `has_hallucinations == True` is **categorically rejected** by the independent validator.

