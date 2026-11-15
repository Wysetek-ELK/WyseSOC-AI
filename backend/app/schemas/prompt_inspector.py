from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionHistoryItem(BaseModel):
    id: str
    execution_id: str
    incident_id: str
    attempt_number: int = 1
    retry_count: int = 0
    captured_at: datetime
    dispatch_status: str  # PREPARED, SEND_ATTEMPTED, COMPLETED, FAILED, NOT_DISPATCHED, PREVIEW_ONLY
    prompt_integrity_status: str  # VERIFIED, MISMATCH, UNVERIFIED
    model_name: str
    provider_type: str
    policy_version_number: Optional[int] = None
    latency_ms: Optional[int] = None
    response_verdict: Optional[str] = None
    is_active_verdict: bool = True
    is_simulated: bool = False


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
    policy_snapshot_hash: Optional[str] = None
    dispatch_status: str  # PREPARED, SEND_ATTEMPTED, COMPLETED, FAILED, NOT_DISPATCHED, PREVIEW_ONLY
    attempt_number: int = 1
    retry_count: int = 0
    execution_id: str
    latency_ms: Optional[int] = None
    is_active_verdict_capture: bool = True
    is_simulated: bool = False


class PromptTechnicalDetails(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    request_sha256: str
    canonical_serialized_payload: Optional[str] = None
    payload_format: str = "CANONICAL_JSON"
    generation_settings: Dict[str, Any] = Field(default_factory=dict)
    integrity_status: str  # VERIFIED, MISMATCH, UNVERIFIED
    integrity_details: Dict[str, Any] = Field(default_factory=dict)
    execution_trace: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


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
    key_takeaways: List[str] = Field(default_factory=list)


class ActualPromptResponse(BaseModel):
    capture_id: Optional[str] = None
    capture_status: str = "CAPTURED_RUNTIME"  # CAPTURED_RUNTIME, HISTORICAL_CAPTURE_UNAVAILABLE, PREVIEW_ONLY
    integrity_status: str = "VERIFIED"  # VERIFIED, MISMATCH, UNVERIFIED
    delivery_status: str = "COMPLETED"  # PREPARED, SEND_ATTEMPTED, COMPLETED, FAILED, NOT_DISPATCHED, PREVIEW_ONLY
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
    available_executions: List[ExecutionHistoryItem] = Field(default_factory=list)


class RuleCaptureSummaryItem(BaseModel):
    rule_id: Optional[str] = None
    incident_id: str
    capture_id: str
    execution_id: str
    captured_at: datetime
    verdict: Optional[str] = None
    dispatch_status: str
    integrity_status: str
    policy_version_number: Optional[int] = None
    is_simulated: bool = False


class RetentionCleanupResponse(BaseModel):
    deleted_count: int
    retention_days: int
    cutoff_timestamp: datetime
    dry_run: bool
    message: str
