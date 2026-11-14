from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LLMConfigResponse(BaseModel):
    host: str = Field(..., description="Host IP address or hostname of LLM Server 2")
    port: int = Field(8000, description="Port of LLM Server 2 (typically 8000 for vLLM)")
    protocol: str = Field("http", description="Protocol (http or https)")
    base_url: str = Field(..., description="Full base URL for OpenAI-compatible endpoint")
    model_name: str = Field(..., description="Active model identifier")
    timeout: float = Field(30.0, description="Inference timeout in seconds")
    context_budget: int = Field(16384, description="Configured total context window budget in tokens")
    max_tokens: int = Field(1024, description="Reserved completion tokens per inference call")
    target_input_budget: int = Field(8192, description="Target effective input token budget in tokens")
    available_input_tokens: int = Field(8192, description="Dynamically calculated available input tokens based on model capacity and reserved output tokens")
    verified_max_model_len: Optional[int] = Field(
        None,
        description="Model-server max_model_len last observed from Server 2 /models probe (None until verified)",
    )
    context_budget_verified: bool = Field(
        False,
        description="True only when Server 2 reported max_model_len >= configured context_budget",
    )
    context_budget_warning: Optional[str] = Field(
        None,
        description="Warning when configured context_budget exceeds model capacity without Server 2 capacity verification or exceeds verified limit",
    )
    operating_mode: str = Field("development", description="Resolved platform operating mode")
    allow_mock_fallback: bool = Field(False, description="Whether fallback to heuristic/mock is allowed when offline")
    is_online: bool = Field(False, description="Cached online reachability status")
    logical_hostname: str = Field("verdictum-cortex-01", description="Logical hostname for Verdictum Cortex (Server 2)")
    core_logical_hostname: str = Field("verdictum-core-01", description="Logical hostname for Verdictum Core (Server 1)")
    server1_outbound_ip: Optional[str] = Field(None, description="Outbound public IP of Server 1 (for security group whitelisting)")
    core_outbound_ip: Optional[str] = Field(None, description="Outbound public IP of Verdictum Core")
    model_profiles: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Configurable per-model context window, completion, and input budget limits")


class LLMConfigUpdate(BaseModel):
    host: str = Field(..., description="LLM Server IP address, hostname, or full URL")
    port: Optional[int] = Field(8000, ge=1, le=65535, description="Port (default: 8000)")
    protocol: Optional[str] = Field("http", description="Protocol (http or https)")
    model_name: Optional[str] = Field(None, description="Model identifier")
    timeout: Optional[float] = Field(None, ge=2.0, le=300.0, description="Timeout in seconds")
    context_budget: Optional[int] = Field(None, ge=1024, le=131072, description="Total context window budget (e.g. 16384 or 8192)")
    max_tokens: Optional[int] = Field(None, ge=64, le=16384, description="Reserved completion tokens per response")
    target_input_budget: Optional[int] = Field(None, ge=512, le=131072, description="Target effective input token budget (e.g. 8192)")
    model_profiles: Optional[Dict[str, Dict[str, int]]] = Field(None, description="Configurable per-model limit overrides")
    allow_mock_fallback: Optional[bool] = Field(None, description="Allow heuristic/mock fallback when offline (disabled in production)")


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
    server_max_model_len: Optional[int] = Field(
        None,
        description="Reported max_model_len from Server 2 /models metadata when exposed by vLLM",
    )
    context_budget_supported: Optional[bool] = Field(
        None,
        description="Whether reported server_max_model_len supports configured LOCAL_LLM_CONTEXT_BUDGET (None if unexposed)",
    )
    available_input_tokens: Optional[int] = Field(
        None,
        description="Dynamically calculated available input tokens based on server_max_model_len and reserved output tokens",
    )
    target_input_budget: Optional[int] = Field(
        None,
        description="Configured target effective input token budget in tokens",
    )
