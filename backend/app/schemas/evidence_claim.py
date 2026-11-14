from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class ModelSupportingClaim(BaseModel):
    """
    P2-REQ-04: Structured Factual Claim extracted from Model Output.
    Must be independently grounded against canonical incident evidence.
    Standardized to support both evidence_ids and cited_evidence_ids interchangeably.
    """
    claim_type: str = Field(..., description="OBSERVED_FACT, PROCESS_EXECUTION, NETWORK_CONNECTION, FILE_HASH, USER_CONTEXT, etc.")
    evidence_ids: List[str] = Field(default_factory=list, description="Referenced evidence ID(s) claimed by the model")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Standardized cited canonical evidence IDs (e.g. EV-01)")
    field: str = Field(..., description="Canonical telemetry field, e.g. process.command_line")
    asserted_value: Any = Field(..., description="Value asserted by the model")
    is_grounded: bool = Field(False, description="True if verified against real canonical evidence")
    grounding_status: str = Field("UNCHECKED", description="GROUNDED, EVIDENCE_REFERENCE_NOT_FOUND, EVIDENCE_VALUE_MISMATCH, FIELD_NOT_FOUND, CLAIM_NOT_VERIFIABLE")
    matched_evidence_id: Optional[str] = Field(None, description="Actual matching evidence ID in canonical evidence")
    actual_observed_value: Optional[str] = Field(None, description="Real observed value in incident telemetry")
    reason: str = Field("", description="Diagnostic reason for grounding status")

    @model_validator(mode="after")
    def sync_evidence_ids(self) -> "ModelSupportingClaim":
        if self.evidence_ids and not self.cited_evidence_ids:
            self.cited_evidence_ids = list(self.evidence_ids)
        elif self.cited_evidence_ids and not self.evidence_ids:
            self.evidence_ids = list(self.cited_evidence_ids)
        return self


class ClaimGroundingResult(BaseModel):
    """Aggregate result from model claim extraction and grounding verification."""
    incident_id: str
    total_claims: int
    grounded_claims: int
    unsupported_claims: int
    grounding_ratio: float = Field(0.0, ge=0.0, le=1.0)
    claims: List[ModelSupportingClaim] = Field(default_factory=list)
    unsupported_claim_details: List[Dict[str, Any]] = Field(default_factory=list)
    has_hallucinations: bool = False

