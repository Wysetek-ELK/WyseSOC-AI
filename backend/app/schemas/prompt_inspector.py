from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PromptExecutionSummary(BaseModel):
    incident_id: str
    rule_id: str
    rule_name: str
    model_name: str
    provider_type: str
    captured_at: datetime
    policy_version_id: Optional[str] = None
    policy_version_number: Optional[int] = None
    policy_status: str
    policy_source: str
    dispatch_status: str
    attempt_number: int = 1
    execution_id: str
    latency_ms: Optional[int] = None


class PromptTechnicalDetails(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    request_sha256: str
    generation_settings: Dict[str, Any] = Field(default_factory=dict)
    integrity_status: str  # VERIFIED, MISMATCH, UNVERIFIED
    integrity_details: Dict[str, Any] = Field(default_factory=dict)
    execution_trace: Dict[str, Any] = Field(default_factory=dict)


class PromptL1Explanation(BaseModel):
    headline: str
    policy_version_used: str
    mandatory_evidence_available: bool = True
    mandatory_evidence_summary: str = "Mandatory evidence verified"
    historical_precedents_included: int = 0
    verdict_returned: str = "UNKNOWN"
    prompt_matches_approved_policy: bool = False
    prompt_integrity_status: str = "VERIFIED"
    summary_text: str = ""


class ActualPromptResponse(BaseModel):
    capture_id: Optional[str] = None
    capture_status: str = "CAPTURED_RUNTIME"  # CAPTURED_RUNTIME, HISTORICAL_CAPTURE_UNAVAILABLE, PREVIEW_ONLY
    integrity_status: str = "VERIFIED"  # VERIFIED, MISMATCH, UNVERIFIED
    execution_summary: PromptExecutionSummary
    system_prompt: str
    incident_payload: str
    rag_precedents: List[Dict[str, Any]] = Field(default_factory=list)
    has_rag_precedents: bool = False
    evidence_requirements: Dict[str, Any] = Field(default_factory=dict)
    verdict_schema: Dict[str, Any] = Field(default_factory=dict)
    technical_details: PromptTechnicalDetails
    l1_explanation: PromptL1Explanation
    raw_model_response: Optional[str] = None
    raw_request_payload: Optional[Dict[str, Any]] = None
    is_redacted: bool = False
