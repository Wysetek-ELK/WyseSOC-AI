# AI VERDICT — PHASE 2: PRE-INFERENCE EVIDENCE VALIDATION
## 04. PRE-INFERENCE EVIDENCE VALIDATION (P2-REQ-03)

---

### 1. Objective
Pre-inference evidence validation (`EvidencePreflightValidator`) operates as an automated gate **before** any request is dispatched to the Local LLM.

Sending incidents with missing critical telemetry to an LLM creates two severe risks:
1. **Hallucination Risk:** The model is tempted to invent facts to justify a conclusion.
2. **Resource Waste:** Expensive GPU inference cycles and tokens are spent analyzing an unresolvable event.

The preflight validator deterministically assesses evidence availability and contract compliance, immediately aborting or flagging triage when conditions are unsatisfied.

---

### 2. Preflight Schema (`app/schemas/evidence_preflight.py`)

```python
class PreflightValidationResult(BaseModel):
    incident_id: str
    rule_id: str
    contract_id: str
    contract_version: int
    contract_status: str  # APPROVED, DRAFT, UNVERIFIED
    preflight_status: str  # COMPLETE, PARTIAL, INSUFFICIENT, CONTRADICTORY, UNVERIFIABLE
    required_evidence_count: int
    available_required_count: int
    evidence_completeness: float = Field(0.0, ge=0.0, le=1.0)
    missing_evidence_fields: List[str]
    critical_missing_fields: List[str]
    detected_contradictions: List[str]
    can_proceed_to_inference: bool = True
    must_abstain_immediately: bool = False
    safe_next_action: str = "PROCEED_TO_INFERENCE"
    reason: str = ""
```

---

### 3. Preflight Decision Matrix

| Preflight Condition | Preflight Status | `can_proceed_to_inference` | `must_abstain_immediately` | `safe_next_action` | Action Taken |
|---|---|---|---|---|---|
| Contract status != `APPROVED` | `UNVERIFIABLE` | False | True | `DEFER_TO_HUMAN_ANALYST` | Short-circuit, no LLM call, force `REQUIRES_ATTENTION` |
| Critical evidence missing | `INSUFFICIENT` | False | True | `DEFER_TO_HUMAN_ANALYST` | Short-circuit, no LLM call, force `REQUIRES_ATTENTION` |
| Localhost/loopback contradiction | `CONTRADICTORY` | True | False | `PROCEED_WITH_CONTRADICTION_FLAG` | Proceed to LLM with contradiction flag |
| Non-critical evidence missing | `PARTIAL` | True | False | `PROCEED_TO_INFERENCE` | Proceed to LLM with completeness score $< 1.0$ |
| 100% required evidence present | `COMPLETE` | True | False | `PROCEED_TO_INFERENCE` | Proceed to LLM with completeness score $= 1.0$ |

---

### 4. Semantic Field Alias Matching
In enterprise SIEMs, fields can appear under equivalent representations. The preflight validator implements semantic alias checks:
- `process.name`: satisfied if `process.file_name` or `process.file_path` is present.
- `network.destination_ip`: satisfied if `dns.domain` is present (for web/DNS alerts).

---

### 5. Short-Circuit Implementation in `ai_verdict_service.py`
```python
if preflight.must_abstain_immediately and (not allow_simulated_fallback or is_prod):
    verdict_data = {
        "incident_id": incident.incident_id,
        "proposed_verdict": "REQUIRES_ATTENTION",
        "verdict": "REQUIRES_ATTENTION",
        "confidence": 0.0,
        "raw_model_confidence": 0.0,
        "reason": f"CRITICAL_TELEMETRY_MISSING: {preflight.reason}",
        "missing_evidence": preflight.missing_evidence_fields,
        "latency_ms": 0,
        "model_identifier": "PREFLIGHT_GUARD",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "validation_status": preflight.preflight_status,
        ...
    }
    return verdict_data
```
This ensures zero tokens are consumed when mandatory evidence is absent.

