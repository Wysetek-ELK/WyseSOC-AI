from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FortiSIEMPullRequest(BaseModel):
    incident_id: str = Field(..., description="FortiSIEM Incident ID to pull (e.g., 132438483)")
    force_refresh: bool = Field(False, description="Whether to re-import if already present in database")


class FortiSIEMPullResponse(BaseModel):
    success: bool
    incident_id: str
    db_id: Optional[str] = None
    title: str = ""
    event_type: str = ""
    severity: str = "MEDIUM"
    status_name: str = "Open"
    event_count: int = 0
    source: str = "LIVE"  # "LIVE" or "FIXTURE_FALLBACK"
    message: str = ""
    error: Optional[str] = None


class FortiSIEMStatusResponse(BaseModel):
    is_configured: bool
    host: str
    username: str
    verify_ssl: bool
    mode: str  # "LIVE" or "FIXTURE_FALLBACK"
    sample_incident_ids: List[str] = Field(default_factory=list)
