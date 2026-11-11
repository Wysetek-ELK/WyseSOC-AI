from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class PilotMode(str, Enum):
    DISABLED = "DISABLED"
    SHADOW = "SHADOW"
    ANALYST_ASSISTED = "ANALYST_ASSISTED"


class PilotIngestionSource(str, Enum):
    ALL = "ALL"
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"


class PilotConfigUpdateRequest(BaseModel):
    pilot_name: str = Field("Default SOC Pilot", min_length=3, max_length=128)
    description: str = Field("", max_length=2000)
    mode: PilotMode = PilotMode.DISABLED
    selected_rule_ids: List[str] = Field(default_factory=list)
    selected_archetypes: List[str] = Field(default_factory=list)
    included_severities: List[str] = Field(default_factory=lambda: ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    ingestion_source: PilotIngestionSource = PilotIngestionSource.ALL
    daily_evaluation_budget: int = Field(500, ge=1, le=50000)
    hourly_evaluation_budget: int = Field(100, ge=1, le=10000)
    max_concurrent_inference: int = Field(2, ge=1, le=16)
    request_timeout_seconds: float = Field(60.0, ge=5.0, le=300.0)
    require_analyst_review: bool = True
    require_approved_policy: bool = True
    allow_external_writeback: bool = False
    allow_auto_incident_closure: bool = False
    error_handling_policy: str = Field("ABSTAIN_AND_LOG", pattern="^(ABSTAIN_AND_LOG|PAUSE_ON_CONSECUTIVE_ERRORS)$")
    consecutive_error_pause_threshold: int = Field(5, ge=1, le=50)
    reporting_schedule: str = Field("HOURLY", pattern="^(HOURLY|DAILY|MANUAL)$")
    change_reason: str = Field("Pilot configuration update", min_length=3, max_length=500)

    @field_validator("allow_external_writeback")
    @classmethod
    def block_external_writeback(cls, v: bool) -> bool:
        if v:
            raise ValueError("PILOT_SAFETY_VIOLATION: External SIEM writeback is strictly prohibited during SOC Pilot.")
        return False

    @field_validator("allow_auto_incident_closure")
    @classmethod
    def block_auto_closure(cls, v: bool) -> bool:
        if v:
            raise ValueError("PILOT_SAFETY_VIOLATION: Autonomous incident closure is strictly prohibited during SOC Pilot.")
        return False

    @field_validator("included_severities")
    @classmethod
    def validate_severities(cls, v: List[str]) -> List[str]:
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        cleaned = [str(s).upper().strip() for s in v if str(s).strip()]
        invalid = [s for s in cleaned if s not in allowed]
        if invalid:
            raise ValueError(f"Unsupported severities: {invalid}. Allowed: {sorted(allowed)}")
        return cleaned


class PilotActivateRequest(BaseModel):
    mode: PilotMode
    change_reason: str = Field(..., min_length=3, max_length=500)


class PilotLifecycleActionRequest(BaseModel):
    reason: str = Field("Operator lifecycle control", min_length=3, max_length=500)


class PilotRollbackRequest(BaseModel):
    target_version: int = Field(..., ge=1)
    reason: str = Field("Rollback to previous safe pilot configuration", min_length=3, max_length=500)


class PilotConfigResponse(BaseModel):
    id: str
    pilot_name: str
    description: str
    version_number: int
    mode: str
    is_paused: bool
    selected_rule_ids: List[str]
    selected_archetypes: List[str]
    included_severities: List[str]
    ingestion_source: str
    daily_evaluation_budget: int
    hourly_evaluation_budget: int
    max_concurrent_inference: int
    request_timeout_seconds: float
    require_analyst_review: bool
    require_approved_policy: bool
    allow_external_writeback: bool
    allow_auto_incident_closure: bool
    error_handling_policy: str
    consecutive_error_pause_threshold: int
    reporting_schedule: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class PilotConfigHistoryItem(BaseModel):
    id: str
    pilot_id: str
    version_number: int
    action: str
    mode: str
    is_paused: bool
    config_snapshot: Dict[str, Any]
    change_reason: str
    changed_by: str
    changed_at: datetime


class PilotBatchRunRequest(BaseModel):
    incident_ids: Optional[List[str]] = None
    max_batch: int = Field(25, ge=1, le=200)
    source_type: str = Field("LIVE", pattern="^(LIVE|HISTORICAL)$")
    allow_simulated: bool = False


class PilotFeedbackRequest(BaseModel):
    action: str = Field(..., pattern="^(ACCEPTED|OVERRIDDEN|DISPUTED|REQUESTED_EVIDENCE)$")
    analyst_decision: str = Field(..., pattern="^(TRUE_POSITIVE|FALSE_POSITIVE|REQUIRES_ATTENTION)$")
    reason: str = Field(..., min_length=3, max_length=2000)


class PilotSupervisorVerifyRequest(BaseModel):
    approved: bool = True
    notes: str = Field("", max_length=2000)


class PilotEvaluationResponse(BaseModel):
    id: str
    pilot_id: str
    pilot_version: int
    incident_id: str
    incident_db_id: Optional[str] = None
    rule_id: str
    archetype: str
    severity: str
    execution_mode: str
    source_type: str
    eligibility_status: str
    proposed_verdict: Optional[str] = None
    validated_verdict: Optional[str] = None
    validation_status: Optional[str] = None
    abstention_reason: Optional[str] = None
    trust_score: Optional[int] = None
    historical_trust_score: Optional[int] = None
    raw_trust_score: Optional[float] = None
    is_calibrated: bool
    evidence_completeness: Optional[float] = None
    grounding_ratio: Optional[float] = None
    supporting_evidence: List[str] = []
    contradictory_evidence: List[str] = []
    missing_evidence: List[str] = []
    policy_version_id: Optional[str] = None
    policy_version_number: Optional[int] = None
    policy_digest: Optional[str] = None
    model_identifier: str
    is_simulated: bool
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    evidence_snapshot_hash: Optional[str] = None
    error_message: Optional[str] = None
    analyst_feedback_action: Optional[str] = None
    analyst_decision: Optional[str] = None
    analyst_override_reason: Optional[str] = None
    analyst_user: Optional[str] = None
    analyst_decided_at: Optional[datetime] = None
    supervisor_verified: bool
    supervisor_user: Optional[str] = None
    supervisor_verified_at: Optional[datetime] = None
    created_at: datetime

