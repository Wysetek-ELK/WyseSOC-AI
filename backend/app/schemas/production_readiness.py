from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.utils.datetime_utils import utc_now
from app.schemas.policy_quality import QualityGateResult


class ReadinessStatus(str, Enum):
    BLOCKED = "BLOCKED"
    INCOMPLETE = "INCOMPLETE"
    LEARNING = "LEARNING"
    VALIDATING = "VALIDATING"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"


class StageStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NEEDS_ACTION = "NEEDS_ACTION"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"


class ActionButton(BaseModel):
    label: str
    action: str  # "open_tab" | "trigger_validation" | "trigger_simulation" | "request_approval" | "open_review"
    target_tab: Optional[str] = "overview"  # "overview" | "learning" | "advanced"
    target_section: Optional[str] = None  # "editor" | "intelligence" | "contract" | "quality" | "simulation" | "drift"


class ReadinessStageItem(BaseModel):
    stage_id: str
    stage_name: str
    stage_number: int
    status: StageStatus
    simple_explanation: str
    missing_requirement: Optional[str] = None
    next_action: str
    action_button: ActionButton
    technical_details: Dict[str, Any] = Field(default_factory=dict)


class SmartNextAction(BaseModel):
    title: str
    description: str
    label: str
    target_tab: str = "overview"
    target_section: Optional[str] = None
    action_type: str = "NAVIGATE"
    status: str = "primary"  # "primary" | "warning" | "success" | "danger" | "normal"


class ProductionReadinessResponse(BaseModel):
    rule_id: str
    rule_name: str
    rule_identifier: str
    severity: str
    detection_archetype: str
    detection_description: str
    
    # Versioning & Lifecycle
    version_id: Optional[str] = None
    version_number: Optional[int] = None
    version_status: str = "DRAFT"
    rule_deployment_status: str = "ACTIVE"
    deployment_status: str = "ACTIVE"
    active_version_number: Optional[int] = None
    active_version_status: Optional[str] = None
    
    # Authoritative Readiness Summary
    readiness_status: ReadinessStatus
    readiness_label: str
    readiness_progress: int = Field(0, ge=0, le=100)
    quality_score: Optional[float] = None
    quality_gates_passed: int = 0
    total_quality_gates: int = 8
    verified_reviews_count: int = 0
    required_reviews_count: int = 30
    production_reviews_target: int = 100
    approval_eligible: bool = False
    last_evaluated_at: Optional[datetime] = None
    
    # The 6 Human-Readable Guided Checklist Stages
    stages: List[ReadinessStageItem] = Field(default_factory=list)
    
    # One Smart Next Action
    recommended_action: SmartNextAction
    
    # Diagnostic & Compliance
    gate_results: Dict[str, QualityGateResult] = Field(default_factory=dict)
    blocking_requirements: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    supporting_evidence_references: List[str] = Field(default_factory=list)
    
    # Statistical and Operational Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)
