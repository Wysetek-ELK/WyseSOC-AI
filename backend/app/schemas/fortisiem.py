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


class FortiSIEMBatchPullRequest(BaseModel):
    time_from: Optional[int] = Field(None, description="Start timestamp in epoch milliseconds (defaults to past 90 days or epoch 0)")
    time_to: Optional[int] = Field(None, description="End timestamp in epoch milliseconds (defaults to now)")
    max_count: int = Field(200, ge=1, le=1000, description="Maximum number of incidents to pull in this batch")
    auto_triage_llm: bool = Field(True, description="Whether to automatically run AI Verdict analysis on ingested incidents")
    force_refresh: bool = Field(False, description="Whether to re-import and re-evaluate cached incidents")


class FortiSIEMBatchPullResponse(BaseModel):
    success: bool
    total_discovered: int = 0
    newly_ingested: int = 0
    already_cached: int = 0
    ai_verdicts_generated: int = 0
    checkpoint_epoch: Optional[int] = None
    source: str = "LIVE"  # "LIVE" or "FIXTURE_FALLBACK"
    message: str = ""
    sample_incidents: List[Dict[str, Any]] = Field(default_factory=list)


class FortiSIEMSchedulerStatusResponse(BaseModel):
    is_running: bool
    interval_seconds: int = 180
    auto_ai_verdict: bool = True
    initial_pull_completed: bool = False
    checkpoint_epoch: Optional[int] = None
    last_sync_time: Optional[str] = None
    next_sync_time: Optional[str] = None
    last_status: str = "IDLE"  # "IDLE", "RUNNING", "SUCCESS", "ERROR"
    last_error: Optional[str] = None
    total_pulled_count: int = 0
    total_ai_verdicts_count: int = 0
    recent_sync_logs: List[Dict[str, Any]] = Field(default_factory=list)


class FortiSIEMSchedulerControlRequest(BaseModel):
    interval_seconds: Optional[int] = Field(180, ge=30, le=3600, description="Polling interval in seconds (default: 180 / 3 mins)")
    auto_ai_verdict: Optional[bool] = Field(True, description="Whether to auto-generate AI verdicts on newly pulled incidents")


class FortiSIEMBatchVerdictRequest(BaseModel):
    incident_ids: Optional[List[str]] = Field(None, description="Specific incident IDs to evaluate. If empty, evaluates all pending incidents.")
    max_batch: int = Field(50, ge=1, le=200, description="Maximum incidents to evaluate in one execution")


class FortiSIEMBatchVerdictResponse(BaseModel):
    success: bool
    total_requested: int
    processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


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
    auto_poll_enabled: bool = False
    poll_interval_seconds: int = 180
    auto_ai_verdict: bool = True


class FortiSIEMConfigUpdate(BaseModel):
    host: str = Field(..., description="FortiSIEM supervisor URL/IP (e.g. https://10.x.x.x)")
    username: str = Field(..., description="FortiSIEM API or service account username")
    password: Optional[str] = Field(None, description="FortiSIEM password (optional if already set)")
    verify_ssl: bool = Field(False, description="Whether to verify SSL certificates")
    timeout: float = Field(25.0, ge=5.0, le=120.0, description="HTTP request timeout in seconds")
    mock_fallback: bool = Field(True, description="Whether to fall back to local sample fixtures when offline")
    auto_poll_enabled: Optional[bool] = Field(None, description="Whether to auto-poll FortiSIEM continuously on startup")
    poll_interval_seconds: Optional[int] = Field(None, ge=30, le=3600, description="Continuous polling interval in seconds (default: 180)")
    auto_ai_verdict: Optional[bool] = Field(None, description="Whether to auto-run AI verdict on pulled incidents")


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


class FortiSIEMRuleSyncResponse(BaseModel):
    success: bool
    synced_rules_count: int
    new_rules_count: int
    updated_rules_count: int
    total_local_rules: int
    synced_rules: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


class FortiSIEMRulePullRequest(BaseModel):
    rule_id: str = Field(..., description="Rule ID, Event Type, or Rule Name to pull from FortiSIEM")
    force_refresh: bool = Field(False, description="Whether to update if already exists locally")


class FortiSIEMRulePullResponse(BaseModel):
    success: bool
    rule_id: str
    name: str = ""
    event_type: str = ""
    severity: str = "MEDIUM"
    source: str = "FORTISIEM_LIVE_RULE_API"
    pattern_logic: str = ""
    message: str = ""

