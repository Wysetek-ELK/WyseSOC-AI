from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


HumanVerdictType = Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"]
DetectionCorrectnessType = Literal["MATCHED", "NOT_MATCHED", "UNKNOWN"]
AuthorizationContextType = Literal["AUTHORIZED", "UNAUTHORIZED", "UNKNOWN", "NOT_APPLICABLE"]
ConfidenceLevelType = Literal["LOW", "MEDIUM", "HIGH"]
EvidenceSufficiencyType = Literal["SUFFICIENT", "PARTIAL", "INSUFFICIENT"]


class CohortProgressCounters(BaseModel):
    cohort_key: str
    total: int = 0
    priority_total: int = 0
    priority_certified: int = 0
    priority_single_reviewed: int = 0
    remaining_total: int = 0
    remaining_certified: int = 0
    gt0_unreviewed: int = 0
    gt1_historical_only: int = 0
    in_progress: int = 0
    gt2_single_review: int = 0
    conflict_pending_adjudication: int = 0
    gt3_certified: int = 0
    certified_inconclusive: int = 0
    exposure_risk_count: int = 0
    my_locked_reviews: int = 0
    my_draft_reviews: int = 0
    blind_review_enforced: bool = True
    excluded_from_learning: bool = True
    ready_for_priority_benchmark: bool = False
    ready_for_full_benchmark: bool = False


class CohortSummaryResponse(BaseModel):
    id: str
    cohort_key: str
    name: str
    description: str
    version: str
    is_frozen: bool
    required_reviewers: int
    excluded_from_learning: bool
    progress: CohortProgressCounters


class GroundTruthQueueItem(BaseModel):
    cohort_item_id: str
    cohort_key: str
    fortisiem_incident_id: str
    incident_db_id: Optional[str] = None
    rule_id: str
    rule_name: str
    vendor: str
    customer: str
    title: Optional[str] = None
    observed_entity: Optional[str] = None
    target_host: Optional[str] = None
    is_priority: bool
    priority_rank: Optional[int] = None
    eligibility_status: str
    certification_status: str
    certified_verdict: Optional[str] = None  # ONLY populated once GT3_CERTIFIED / CERTIFIED_INCONCLUSIVE
    locked_reviewers_count: int = 0
    my_review_status: Literal["NOT_STARTED", "DRAFT", "LOCKED"] = "NOT_STARTED"
    my_review_verdict: Optional[str] = None  # Reviewer sees ONLY their own verdict
    exposure_risk_flag: bool = False
    exposure_risk_reason: str = ""
    blind_status: str = "BLIND_ENFORCED"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GroundTruthQueueResponse(BaseModel):
    cohort: CohortSummaryResponse
    items: List[GroundTruthQueueItem]
    total: int


class RawLogEntry(BaseModel):
    index: int
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    host: Optional[str] = None
    process_name: Optional[str] = None
    file_name: Optional[str] = None
    command_line: Optional[str] = None
    raw_log: str = ""
    parsed_attributes: Dict[str, Any] = Field(default_factory=dict)


class RuleDefinitionView(BaseModel):
    rule_id: str
    rule_name: str
    category: str = ""
    severity: str = ""
    description: str = ""
    condition_summary: str = ""
    rule_definition_sha256: str = ""
    approved_policy_version_id: Optional[str] = None
    approved_policy_version_number: Optional[int] = None
    raw_rule_spec: Dict[str, Any] = Field(default_factory=dict)


class ReviewerSubmissionSummary(BaseModel):
    review_id: str
    reviewer_id: str
    analyst_verdict: str
    detection_correctness: Optional[str] = None
    authorization_context: Optional[str] = None
    confidence_level: Optional[str] = None
    evidence_sufficiency_status: Optional[str] = None
    analyst_notes: str = ""
    evidence_references: List[str] = Field(default_factory=list)
    additional_evidence_json: List[Dict[str, Any]] = Field(default_factory=list)
    attestation_flags: Dict[str, Any] = Field(default_factory=dict)
    is_locked: bool = False
    is_draft: bool = False
    certification_round: int = 1
    certification_version: int = 1
    created_at: Optional[datetime] = None


class GroundTruthDetailResponse(BaseModel):
    cohort_item: GroundTruthQueueItem
    incident_overview: Dict[str, Any]
    rule_definition: RuleDefinitionView
    raw_logs: List[RawLogEntry]
    normalized_evidence: List[Dict[str, Any]]
    additional_evidence: List[Dict[str, Any]]
    raw_evidence_sha256: str = ""
    canonical_evidence_sha256: str = ""
    blind_review_guarantees: Dict[str, Any]
    my_review: Optional[ReviewerSubmissionSummary] = None
    locked_reviewers_count: int = 0
    other_reviewer_submitted: bool = False
    can_submit_lock: bool = True
    lock_blocked_reason: Optional[str] = None
    can_adjudicate: bool = False
    conflict_reviews: List[ReviewerSubmissionSummary] = Field(default_factory=list)
    certified_result: Optional[Dict[str, Any]] = None
    revisions: List[Dict[str, Any]] = Field(default_factory=list)


class AdditionalEvidenceInput(BaseModel):
    evidence_type: str = Field("MANUAL_INVESTIGATION", max_length=64)
    reference_key: str = Field("", max_length=256)
    evidence_content: str = Field(..., min_length=1, max_length=8000)
    analyst_rationale: str = Field("", max_length=2000)


class AttestationFlagsInput(BaseModel):
    evidence_reviewed: bool = False
    no_ai_or_historical_influence: bool = False
    independent_judgment: bool = False


class GroundTruthReviewSubmitRequest(BaseModel):
    mode: Literal["DRAFT", "LOCK"] = "LOCK"
    human_verdict: HumanVerdictType
    detection_correctness: DetectionCorrectnessType = "UNKNOWN"
    authorization_context: AuthorizationContextType = "UNKNOWN"
    confidence_level: ConfidenceLevelType = "MEDIUM"
    evidence_sufficiency_status: EvidenceSufficiencyType = "SUFFICIENT"
    rationale: str = Field("", max_length=10000)
    evidence_references: List[str] = Field(default_factory=list)
    additional_evidence: List[AdditionalEvidenceInput] = Field(default_factory=list)
    attestation_flags: AttestationFlagsInput = Field(default_factory=AttestationFlagsInput)


class GroundTruthAdjudicateRequest(BaseModel):
    final_verdict: HumanVerdictType
    rationale: str = Field(..., min_length=15, max_length=10000)
    detection_correctness: DetectionCorrectnessType = "UNKNOWN"
    authorization_context: AuthorizationContextType = "UNKNOWN"
    evidence_references: List[str] = Field(default_factory=list)


class GroundTruthReopenRequest(BaseModel):
    review_id: str
    new_verdict: HumanVerdictType
    new_rationale: str = Field(..., min_length=15, max_length=10000)
    revision_reason: str = Field(..., min_length=10, max_length=2000)
