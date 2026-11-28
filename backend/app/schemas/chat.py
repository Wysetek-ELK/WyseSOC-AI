from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

ResponseStatusType = Literal[
    "QUEUED",
    "GENERATING",
    "COMPLETED",
    "TRUNCATED",
    "INTERRUPTED",
    "TIMEOUT",
    "FAILED",
    "CANCELLED",
    "CONTEXT_BUDGET_EXCEEDED",
]


class ChatMessageItem(BaseModel):
    id: Optional[str] = None
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content text")
    reasoning_content: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None
    status: Optional[str] = None
    finish_reason: Optional[str] = None
    stream_termination: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    requested_max_tokens: Optional[int] = None
    effective_context_window: Optional[int] = None
    latency_ms: Optional[float] = None
    attached_incident_id: Optional[str] = None
    is_continuation: bool = False
    parent_message_id: Optional[str] = None
    continuation_index: int = 0
    continuation_available: bool = False
    context_warning: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessageItem] = Field(..., min_length=1, description="Conversation history")
    incident_id: Optional[str] = Field(None, description="Optional FortiSIEM / DB Incident ID to attach as analysis context")
    conversation_id: Optional[str] = Field(None, description="Optional existing SentinelConversation ID")
    temperature: float = Field(0.3, ge=0.0, le=1.5, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=64, le=16384, description="Optional output token cap; None uses context-aware budget")
    system_prompt: Optional[str] = Field(None, description="Optional custom system persona instruction")
    persist: bool = Field(True, description="Persist conversation and messages for the authenticated user")


class ContinueChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Target SentinelConversation ID")
    message_id: str = Field(..., description="Incomplete assistant message ID to continue")
    temperature: float = Field(0.2, ge=0.0, le=1.5, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=64, le=16384, description="Optional output cap override")


class ChatResponse(BaseModel):
    message: ChatMessageItem
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    request_id: Optional[str] = None
    status: str = "COMPLETED"
    finish_reason: Optional[str] = None
    stream_termination: Optional[str] = None
    model: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: Optional[int] = None
    total_tokens: int = 0
    requested_max_tokens: Optional[int] = None
    effective_context_window: Optional[int] = None
    history_trimmed_count: int = 0
    continuation_available: bool = False
    context_warning: Optional[str] = None
    attached_incident_id: Optional[str] = None
    server_url: str
    is_simulated: bool = False


class ChatConversationSummary(BaseModel):
    id: str
    title: str
    attached_incident_id: Optional[str] = None
    message_count: int = 0
    created_at: str
    updated_at: str


class ChatConversationDetail(BaseModel):
    id: str
    title: str
    attached_incident_id: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[ChatMessageItem] = Field(default_factory=list)


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
    logical_hostname: str = "verdictum-cortex-01"
    server_name: str = "Verdictum Cortex"
    configured_provider: str = "OPENAI_COMPATIBLE"
    endpoint_provenance: str = "OFFLINE"
    current_s2_health: str = "OFFLINE"
    gpu_telemetry_verified: bool = False
    test_environment: Optional[str] = None
    verified_max_model_len: Optional[int] = None
    effective_context_window: Optional[int] = None
    enable_thinking: bool = False
