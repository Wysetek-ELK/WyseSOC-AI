from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LLMConfigResponse(BaseModel):
    host: str = Field(..., description="Host IP address or hostname of LLM Server 2")
    port: int = Field(8000, description="Port of LLM Server 2 (typically 8000 for vLLM)")
    protocol: str = Field("http", description="Protocol (http or https)")
    base_url: str = Field(..., description="Full base URL for OpenAI-compatible endpoint")
    model_name: str = Field(..., description="Active model identifier")
    timeout: float = Field(30.0, description="Inference timeout in seconds")
    allow_mock_fallback: bool = Field(True, description="Whether fallback to heuristic/mock is allowed when offline")
    is_online: bool = Field(False, description="Cached online reachability status")
    server1_outbound_ip: Optional[str] = Field(None, description="Outbound public IP of Server 1 (for security group whitelisting)")


class LLMConfigUpdate(BaseModel):
    host: str = Field(..., description="LLM Server IP address, hostname, or full URL")
    port: Optional[int] = Field(8000, ge=1, le=65535, description="Port (default: 8000)")
    protocol: Optional[str] = Field("http", description="Protocol (http or https)")
    model_name: Optional[str] = Field(None, description="Model identifier")
    timeout: Optional[float] = Field(None, ge=2.0, le=300.0, description="Timeout in seconds")
    allow_mock_fallback: Optional[bool] = Field(None, description="Allow heuristic/mock fallback when offline")


class LLMTestConnectionRequest(BaseModel):
    host: str = Field(..., description="LLM Server IP, hostname, or full URL to test")
    port: Optional[int] = Field(8000, ge=1, le=65535, description="Port")
    protocol: Optional[str] = Field("http", description="http or https")
    timeout: Optional[float] = Field(5.0, ge=1.0, le=30.0, description="Test connection timeout in seconds")


class LLMTestConnectionResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    message: str
    models: List[str] = Field(default_factory=list)
    tested_url: str = ""
