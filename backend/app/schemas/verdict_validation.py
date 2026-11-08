from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VerdictValidationResult(BaseModel):
    """
    P2-REQ-05: Independent Deterministic Verdict Validation Result.
    Authoritative backend decision record evaluating model propositions against evidence.
    """
    incident_id: str
    proposed_verdict: str = Field(..., description="Verdict proposed by the LLM or simulation")
    final_verdict: str = Field(..., description="Authoritative validated verdict accepted by the system")
    validation_status: str = Field(..., description="VALIDATED, ABSTAINED, REJECTED, INSUFFICIENT_EVIDENCE")
    validation_reason_codes: List[str] = Field(default_factory=list, description="Machine-readable diagnostic reason codes")
    is_decisive_accepted: bool = Field(False, description="True if proposed TP or FP was accepted; False if routed to REQUIRES_ATTENTION")
    evidence_completeness: float = Field(0.0, ge=0.0, le=1.0, description="Proportion of contract required fields present")
    grounding_ratio: float = Field(0.0, ge=0.0, le=1.0, description="Proportion of model claims verified by source evidence")
    total_claims_count: int = 0
    grounded_claims_count: int = 0
    unsupported_claims_count: int = 0
    missing_evidence_fields: List[str] = Field(default_factory=list)
    unsupported_claims: List[Dict[str, Any]] = Field(default_factory=list)
    detected_contradictions: List[str] = Field(default_factory=list)
    analyst_action_directive: str = Field("", description="Guidance for human SOC analyst review")
    contract_id: Optional[str] = None
    contract_version: int = 1
    validator_version: str = "2.0.0"
    raw_model_confidence: float = 0.0
    validated_confidence_display: Optional[float] = None
    replay_signature: str = ""

