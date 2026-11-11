from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)


class QuestionAnswer(BaseModel):
    answer: str = Field(..., min_length=1, max_length=5000)


class InvestigationQuestionResponse(BaseModel):
    id: str
    investigation_id: str
    question: str
    answer: str
    asked_by_user_id: Optional[str] = None
    answered_by_user_id: Optional[str] = None
    created_at: datetime
    answered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceAttach(BaseModel):
    evidence_type: str = Field("TELEMETRY", max_length=64)
    reference_key: str = Field("", max_length=256)
    evidence_content: str = Field(..., min_length=1)
    analyst_rationale: str = Field("", max_length=2000)


class InvestigationEvidenceResponse(BaseModel):
    id: str
    investigation_id: str
    evidence_type: str
    reference_key: str
    evidence_content: str
    analyst_rationale: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationAssignRequest(BaseModel):
    user_id: Optional[str] = None  # None unassigns


class InvestigationStatusUpdate(BaseModel):
    status: str = Field(..., max_length=32)  # PENDING_REVIEW, ASSIGNED, IN_PROGRESS, AWAITING_INFORMATION, REVIEWED, CLOSED_DRY_RUN


class AnalystVerdictSubmit(BaseModel):
    analyst_verdict: str = Field(..., max_length=32)  # TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION
    verdict_reason: str = Field("", max_length=5000)
    analyst_notes: str = Field("", max_length=5000)
    insufficient_evidence_reason: Optional[str] = Field(None, max_length=2000)
    is_disputed: bool = False
    is_independently_verified: bool = False
    status: Optional[str] = "REVIEWED"
    action_type: Optional[str] = Field(None, max_length=32)  # ACCEPTED | OVERRIDDEN | DISPUTED | REQUESTED_EVIDENCE


class AIAssuranceSummary(BaseModel):
    incident_summary: str = ""
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    policy_version_number: Optional[int] = None
    policy_digest: Optional[str] = None
    proposed_verdict: Optional[str] = None
    validated_verdict: Optional[str] = None
    validation_status: Optional[str] = None
    abstention_reason: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    trust_score: Optional[int] = None
    historical_trust_score: Optional[int] = None
    trust_cap_applied: bool = False
    is_calibrated: bool = False
    calibration_status: str = "NOT_CALIBRATED"
    historical_sample_count: int = 0
    historical_validation_status: str = "UNCALIBRATED"
    model_identifier: Optional[str] = None
    is_simulated: bool = False
    configured_provider: Optional[str] = None
    execution_provenance: Optional[str] = None
    historical_execution_provenance: Optional[str] = None
    current_s2_health: Optional[str] = None
    test_environment: Optional[str] = None
    pilot_evaluation_id: Optional[str] = None
    pilot_mode: Optional[str] = None
    evaluated_at: Optional[str] = None
    analyst_feedback_action: Optional[str] = None
    supervisor_verified: bool = False


class InvestigationListItem(BaseModel):
    id: str
    incident_id: str
    incident_vendor_id: Optional[str] = None
    title: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    severity: Optional[str] = None
    event_type: Optional[str] = None
    status: str
    assigned_to_user_id: Optional[str] = None
    assigned_to_username: Optional[str] = None
    analyst_verdict: Optional[str] = None
    is_disputed: bool
    is_independently_verified: bool
    question_count: int = 0
    evidence_count: int = 0
    ai_validated_verdict: Optional[str] = None
    ai_trust_score: Optional[int] = None
    pilot_mode: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationDetailResponse(BaseModel):
    id: str
    incident_id: str
    assigned_to_user_id: Optional[str] = None
    assigned_to_username: Optional[str] = None
    status: str
    analyst_verdict: Optional[str] = None
    verdict_reason: str = ""
    analyst_notes: str = ""
    is_disputed: bool = False
    is_independently_verified: bool = False
    insufficient_evidence_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Incident summary data
    incident_vendor_id: Optional[str] = None
    title: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    severity: Optional[str] = None
    event_type: Optional[str] = None
    source_ip: Optional[str] = None
    reporting_device: Optional[str] = None
    
    # Sub-collections
    questions: List[InvestigationQuestionResponse] = []
    evidence_items: List[InvestigationEvidenceResponse] = []
    ai_assurance: Optional[AIAssuranceSummary] = None

    model_config = ConfigDict(from_attributes=True)


class InvestigationQueueResponse(BaseModel):
    items: List[InvestigationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

