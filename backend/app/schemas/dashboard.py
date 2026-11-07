from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class SeverityCount(BaseModel):
    severity: str
    count: int
    percentage: float = 0.0


class SourceCount(BaseModel):
    source: str
    count: int
    percentage: float = 0.0


class StatusCount(BaseModel):
    status: str
    count: int


class GroundTruthCount(BaseModel):
    verdict: str
    count: int
    percentage: float = 0.0


class RecentActivityItem(BaseModel):
    incident_id: str
    title: str
    severity: str
    event_type: str
    created_at_epoch: Optional[int] = None
    historical_verdict: Optional[str] = None
    ai_verdict: Optional[Dict[str, Any]] = None
    created_at: datetime


class RecentImportJobItem(BaseModel):
    id: str
    filename: str
    file_type: str
    imported_count: int
    duplicate_count: int
    error_count: int
    status: str
    created_at: datetime


class DashboardMetricsResponse(BaseModel):
    total_incidents: int
    total_rules: int
    historical_true_positives: int
    historical_false_positives: int
    unresolved_incidents: int
    ai_evaluated_count: int = 0
    ai_true_positives: int = 0
    ai_false_positives: int = 0
    ai_requires_attention: int = 0
    ai_pending_evaluation: int = 0
    severity_breakdown: List[SeverityCount]
    source_breakdown: List[SourceCount]
    ground_truth_breakdown: List[GroundTruthCount]
    recent_activity: List[RecentActivityItem]
    recent_imports: List[RecentImportJobItem]
    is_empty: bool = False

