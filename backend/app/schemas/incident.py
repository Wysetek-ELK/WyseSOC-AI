from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class IncidentEventResponse(BaseModel):
    id: str
    event_id: str
    event_receive_time: Optional[int] = None
    event_type: str
    raw_log: str
    attributes: Dict[str, Any]

    model_config = {"from_attributes": True}


class HistoricalGroundTruthResponse(BaseModel):
    id: str
    resolution: str
    cleared_reason: str
    comments: str
    cleared_user: str
    cleared_time_epoch: Optional[int] = None
    resolved_at_epoch: Optional[int] = None
    is_ml_generated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentListItemResponse(BaseModel):
    id: str
    incident_id: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    event_type: str
    title: str
    severity: str
    status_code: int
    status_name: str
    category: str
    source_ip: str
    reporting_device: str
    created_at_epoch: Optional[int] = None
    first_seen_epoch: Optional[int] = None
    last_seen_epoch: Optional[int] = None
    historical_resolution: Optional[str] = None  # Included in list unless blind review mode
    ai_verdict: Optional[Dict[str, Any]] = None  # Stored AI evaluation verdict
    event_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentDetailResponse(BaseModel):
    id: str
    incident_id: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    rule_description: Optional[str] = None
    import_job_id: Optional[str] = None
    event_type: str
    title: str
    description: str
    detail: str
    severity: str
    event_severity: str
    status_code: int
    status_name: str
    category: str
    subcategory: str
    source_ip: str
    reporting_device: str
    reporting_ip: str
    customer: str
    ticket_id: str
    first_seen_epoch: Optional[int] = None
    last_seen_epoch: Optional[int] = None
    created_at_epoch: Optional[int] = None
    updated_at_epoch: Optional[int] = None
    raw_payload: Dict[str, Any]
    events: List[IncidentEventResponse] = []
    ground_truth: Optional[HistoricalGroundTruthResponse] = None
    ai_verdict: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    items: List[IncidentListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ModelFacingEvent(BaseModel):
    event_id: str
    event_type: str
    event_receive_time: Optional[int] = None
    attributes: Dict[str, Any]


class ModelFacingIncidentPayload(BaseModel):
    """
    CRITICAL ALLOWLIST:
    Explicit schema for future model-facing incident payload.
    Strictly excludes:
      - resolution
      - clearedReason / cleared_reason
      - comments
      - clearedUser / cleared_user
      - clearedTime / cleared_time
      - resolvedAt / resolved_at
    Any closure, analyst, or post-investigation evidence is prohibited.
    """
    incident_id: str
    event_type: str
    title: str
    description: str
    detail: str
    severity: str
    category: str
    subcategory: str
    source_ip: str
    reporting_device: str
    reporting_ip: str
    first_seen_epoch: Optional[int] = None
    last_seen_epoch: Optional[int] = None
    created_at_epoch: Optional[int] = None
    events: List[ModelFacingEvent] = []
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    rule_pattern: Optional[str] = None
