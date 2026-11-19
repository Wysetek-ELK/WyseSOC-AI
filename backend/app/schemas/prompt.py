from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


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
    revoked_by_user_id: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    previous_status: Optional[str] = None
    archived_by_user_id: Optional[str] = None
    archived_at: Optional[datetime] = None
    archival_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RulePromptResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    rule_event_type: Optional[str] = None
    title: str
    active_version_id: Optional[str] = None
    active_version: Optional[PromptVersionResponse] = None
    ai_execution_suspended: bool = False
    suspension_reason: Optional[str] = None
    versions: List[PromptVersionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class PromptRevokeRequest(BaseModel):
    revocation_reason: Optional[str] = Field(None, description="Mandatory administrative justification for revoking policy approval")
    reason: Optional[str] = Field(None, description="Alternative field for revocation reason")
    revocationReason: Optional[str] = Field(None, description="CamelCase alternative for revocation reason")

    def get_reason(self) -> str:
        return (self.revocation_reason or self.reason or self.revocationReason or "").strip()


class PolicyEligibilityResponse(BaseModel):
    rule_id: str
    rule_name: str
    is_eligible: bool
    status: str  # "ELIGIBLE", "POLICY_REVOKED", "POLICY_ARCHIVED", "POLICY_DRAFT", "NO_ELIGIBLE_POLICY", "SEMANTIC_MISMATCH", "RULE_SUSPENDED"
    reason_code: str
    explanation: str
    active_version_number: Optional[int] = None
    active_version_status: Optional[str] = None
    selected_version_number: Optional[int] = None
    selected_version_status: Optional[str] = None
    ai_verdict_execution_status: str  # "ENABLED", "SUSPENDED", "BLOCKED"
    is_revoked: bool = False
    revocation_details: Optional[Dict[str, Any]] = None


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
    production_readiness_status: Optional[str] = "INCOMPLETE"
    gates_passed_count: int = 0
    missing_requirements_count: int = 0
    recommended_action_title: Optional[str] = None
    ai_verdict_execution_status: str = "BLOCKED"  # "ENABLED", "SUSPENDED", "BLOCKED"
    selected_policy_version_number: Optional[int] = None
    selected_policy_version_status: Optional[str] = None
    is_revoked: bool = False

    model_config = ConfigDict(from_attributes=True)


class PolicyVersionHistoryItem(BaseModel):
    id: str
    prompt_id: str
    version_number: int
    status: str  # APPROVED, DRAFT, ARCHIVED
    previous_status: Optional[str] = None
    quality_status: Optional[str] = "GENERATED_DRAFT"
    quality_score: Optional[float] = None
    change_summary: str
    is_active: bool = False
    is_eligible_for_deletion: bool = False
    is_eligible_for_archive: bool = False
    blocking_reasons: List[str] = []
    dependency_counts: Dict[str, int] = {}
    usage_label: str = "Unreferenced Draft"
    created_at: datetime
    approved_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    archival_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VersionDeletionPreviewResponse(BaseModel):
    rule_id: str
    rule_name: str
    version_id: str
    version_number: int
    status: str
    is_active: bool
    is_eligible: bool
    blocking_reasons: List[str] = []
    dependency_counts: Dict[str, int] = {}
    records_affected: int = 0
    is_reversible: bool = False
    warning_message: str = ""


class VersionArchiveRequest(BaseModel):
    reason: Optional[str] = Field("Archived by SOC Administrator", description="Administrative justification for archiving version")


class VersionDeleteRequest(BaseModel):
    justification: Optional[str] = Field("Administrative cleanup of obsolete draft", description="Reason for permanent deletion")
    confirmation_text: Optional[str] = Field(None, description="Typed confirmation matching rule or version")


class BulkVersionDeleteRequest(BaseModel):
    version_ids: List[str] = Field(..., min_length=1, description="List of version IDs to evaluate and clean up")
    justification: Optional[str] = Field("Bulk administrative cleanup of obsolete drafts", description="Reason for bulk deletion")
    confirmation_text: Optional[str] = Field(None, description="Typed confirmation 'PERMANENTLY DELETE'")


class BulkVersionDeleteResponse(BaseModel):
    selected_count: int
    eligible_count: int
    deleted_count: int
    protected_count: int
    deleted_version_numbers: List[int] = []
    protected_items: List[Dict[str, Any]] = []
