from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PromptVersionResponse(BaseModel):
    id: str
    prompt_id: str
    version_number: int
    status: str  # DRAFT, APPROVED, ARCHIVED
    is_template_draft: bool
    common_prompt: str
    rule_specific_prompt: str
    detection_conditions: str
    required_evidence: str
    tp_indicators: str
    fp_indicators: str
    missing_info_criteria: str
    escalation_conditions: str
    analyst_questions: List[str] = []
    change_summary: str
    quality_status: Optional[str] = "GENERATED_DRAFT"
    quality_score: Optional[float] = None
    quality_assessment_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    approved_by_user_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RulePromptResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    rule_event_type: Optional[str] = None
    title: str
    active_version_id: Optional[str] = None
    active_version: Optional[PromptVersionResponse] = None
    versions: List[PromptVersionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptVersionCreate(BaseModel):
    common_prompt: str = Field("", description="Standard SOC investigation baseline instructions")
    rule_specific_prompt: str = Field(..., min_length=5, description="Rule-specific guidance and pattern details")
    detection_conditions: str = Field("", description="Specific conditions triggering this alert")
    required_evidence: str = Field("", description="Mandatory artifacts analyst must gather")
    tp_indicators: str = Field("", description="Indicators confirming malicious activity")
    fp_indicators: str = Field("", description="Benign administrative indicators")
    missing_info_criteria: str = Field("", description="Criteria for insufficient evidence")
    escalation_conditions: str = Field("", description="Thresholds for P1/P2 elevation")
    analyst_questions: List[str] = Field(default_factory=list, description="Standard investigative Q&A checklist")
    change_summary: str = Field("Manual prompt update", max_length=512)


class PromptDraftGenerateRequest(BaseModel):
    rule_id: str


class PromptApprovalRequest(BaseModel):
    version_id: Optional[str] = None
    change_summary: Optional[str] = "Approved by SOC Lead"


class PromptRollbackRequest(BaseModel):
    target_version_id: str


class RulePromptSummaryItem(BaseModel):
    rule_id: str
    rule_name: str
    event_type: str
    severity: str
    status: str
    data_source: Optional[str] = None
    prompt_id: Optional[str] = None
    active_version_number: Optional[int] = None
    active_version_status: Optional[str] = None
    total_versions: int = 0
    has_approved_prompt: bool = False
    last_updated: Optional[datetime] = None
    
    # AIS 2.0 Enhanced Summary Directory Attributes
    detection_archetype: Optional[str] = "UNKNOWN"
    definition_completeness: Optional[str] = "UNKNOWN"
    quality_score: Optional[float] = None
    quality_validation_status: Optional[str] = "NOT_EVALUATED"
    blocking_issue_count: int = 0
    simulation_status: Optional[str] = "NOT_EVALUATED"
    last_validated_date: Optional[datetime] = None
    revalidation_required: bool = False

    class Config:
        from_attributes = True
