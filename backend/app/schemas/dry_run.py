from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DryRunConfigCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    description: str = Field("", max_length=1000)
    rule_id: Optional[str] = None  # None evaluates across all rules
    prompt_version_id: Optional[str] = None
    provider_type: str = Field("SIMULATED", max_length=32)  # DISABLED, SIMULATED, OPENAI_COMPATIBLE
    split_strategy: str = Field("ALL", max_length=32)  # ALL, CHRONOLOGICAL_70_30, GROUP_AWARE_HOST
    dataset_filters: Dict[str, Any] = Field(default_factory=dict)


class DryRunConfigResponse(BaseModel):
    id: str
    name: str
    description: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    prompt_version_id: Optional[str] = None
    provider_type: str
    split_strategy: str
    dataset_filters: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DryRunResultResponse(BaseModel):
    id: str
    job_id: str
    incident_id: str
    incident_vendor_id: Optional[str] = None
    incident_title: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    predicted_verdict: str
    confidence: float
    reasoning: str
    supporting_evidence: List[str] = []
    missing_evidence: List[str] = []
    analyst_questions: List[str] = []
    latency_ms: int
    model_identifier: str
    prompt_version_number: int
    validation_status: str
    is_simulated: bool
    ground_truth_verdict: Optional[str] = None
    is_agreement: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DryRunJobResponse(BaseModel):
    id: str
    config_id: str
    config_name: Optional[str] = None
    status: str  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    total_items: int
    processed_items: int
    error_count: int
    is_simulated: bool
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DryRunTriggerRequest(BaseModel):
    config_id: str
    custom_sample_limit: Optional[int] = Field(None, ge=1, le=1000)
