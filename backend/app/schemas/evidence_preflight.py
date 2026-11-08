from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PreflightValidationResult(BaseModel):
    """
    P2-REQ-03: Pre-Inference Validation Assessment.
    Determines evidence availability and eligibility before dispatching to LLM.
    """
    incident_id: str
    rule_id: str
    contract_id: str
    contract_version: int
    contract_status: str  # APPROVED, DRAFT, UNVERIFIED
    preflight_status: str  # COMPLETE, PARTIAL, INSUFFICIENT, CONTRADICTORY, UNVERIFIABLE
    required_evidence_count: int
    available_required_count: int
    evidence_completeness: float = Field(0.0, ge=0.0, le=1.0)
    missing_evidence_fields: List[str] = Field(default_factory=list)
    critical_missing_fields: List[str] = Field(default_factory=list)
    detected_contradictions: List[str] = Field(default_factory=list)
    can_proceed_to_inference: bool = True
    must_abstain_immediately: bool = False
    safe_next_action: str = "PROCEED_TO_INFERENCE"
    reason: str = ""

