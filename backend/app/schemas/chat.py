from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessageItem(BaseModel):
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content text")
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessageItem] = Field(..., min_length=1, description="Conversation history")
    incident_id: Optional[str] = Field(None, description="Optional FortiSIEM / DB Incident ID to attach as analysis context")
    temperature: float = Field(0.3, ge=0.0, le=1.5, description="Sampling temperature")
    max_tokens: int = Field(1024, ge=64, le=16384, description="Maximum response tokens")
    system_prompt: Optional[str] = Field(None, description="Optional custom system persona instruction")


class ChatResponse(BaseModel):
    message: ChatMessageItem
    model: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    attached_incident_id: Optional[str] = None
    server_url: str
    is_simulated: bool = False


class ChatStatusResponse(BaseModel):
    is_online: bool
    host: str
    port: int
    protocol: str
    base_url: str
    model_name: str
    available_models: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    status_message: str
    configured_provider: str = "OPENAI_COMPATIBLE"
    endpoint_provenance: str = "OFFLINE"
    current_s2_health: str = "OFFLINE"
    gpu_telemetry_verified: bool = False
    test_environment: Optional[str] = None

