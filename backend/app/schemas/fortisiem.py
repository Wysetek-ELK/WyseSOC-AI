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
    live_incident_ids: List[str] = Field(default_factory=list)


class FortiSIEMConfigResponse(BaseModel):
    is_configured: bool
    host: str
    username: str
    is_password_set: bool
    verify_ssl: bool
    timeout: float
    mock_fallback: bool


class FortiSIEMConfigUpdate(BaseModel):
    host: str = Field(..., description="FortiSIEM supervisor URL/IP (e.g. https://10.x.x.x)")
    username: str = Field(..., description="FortiSIEM API or service account username")
    password: Optional[str] = Field(None, description="FortiSIEM password (optional if already set)")
    verify_ssl: bool = Field(False, description="Whether to verify SSL certificates")
    timeout: float = Field(25.0, ge=5.0, le=120.0, description="HTTP request timeout in seconds")
    mock_fallback: bool = Field(True, description="Whether to fall back to local sample fixtures when offline")


class FortiSIEMTestConnectionRequest(BaseModel):
    host: str = Field(..., description="FortiSIEM supervisor URL/IP")
    username: str = Field(..., description="FortiSIEM API username")
    password: Optional[str] = Field(None, description="Password to test (uses saved password if None)")
    verify_ssl: bool = Field(False, description="Whether to verify SSL certificates")
    timeout: float = Field(10.0, ge=3.0, le=60.0, description="Test connection timeout")


class FortiSIEMTestConnectionResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
