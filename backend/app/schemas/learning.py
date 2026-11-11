from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class LearningRecordCreate(BaseModel):
    rule_id: str
    incident_id: str
    verified_verdict: str = Field(..., max_length=32)
    analyst_explanation: str = Field("", max_length=5000)
    tp_indicators: List[str] = Field(default_factory=list)
    fp_indicators: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    evidence_references: List[str] = Field(default_factory=list)
    answered_questions: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: str = Field("PENDING_REVIEW", max_length=32)


class LearningRecordVerifyRequest(BaseModel):
    verification_status: str = Field(..., description="Status must be VERIFIED, REJECTED, DISPUTED, or PENDING_REVIEW")
    review_notes: Optional[str] = Field(None, max_length=2000)


class LearningRecordResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    incident_id: str
    incident_vendor_id: Optional[str] = None
    incident_title: Optional[str] = None
    verified_verdict: str
    analyst_explanation: str
    tp_indicators: List[str] = []
    fp_indicators: List[str] = []
    missing_evidence: List[str] = []
    evidence_references: List[str] = []
    answered_questions: List[Dict[str, Any]] = []
    verification_status: str
    feedback_timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimilarCaseQuery(BaseModel):
    incident_id: Optional[str] = None
    rule_id: Optional[str] = None
    event_type: Optional[str] = None
    source_ip: Optional[str] = None
    command_substring: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)


class SimilarCaseMatch(BaseModel):
    learning_record_id: str
    incident_id: str
    incident_vendor_id: Optional[str] = None
    title: Optional[str] = None
    verified_verdict: str
    analyst_explanation: str
    match_score: float = Field(..., description="Deterministic similarity match score between 0.0 and 1.0")
    matched_features: List[str] = Field(default_factory=list, description="Explicit attributes that matched")
    feedback_timestamp: datetime


class LearningListResponse(BaseModel):
    items: List[LearningRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

