import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ActualLLMPromptCapture(Base):
    """
    Immutable, execution-linked record of the exact outbound prompt and request payload
    sent from Server 1 (Verdictum AI) to Server 2 (Local LLM / OpenAI Compatible Provider)
    at the provider boundary.
    """
    __tablename__ = "actual_llm_prompt_captures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), default="", nullable=False)

    policy_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    policy_status: Mapped[str] = mapped_column(String(32), default="UNCONFIGURED", nullable=False)
    policy_source: Mapped[str] = mapped_column(String(32), default="DATABASE", nullable=False)
    policy_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Delivery status: PREPARED, SEND_ATTEMPTED, COMPLETED, FAILED, NOT_DISPATCHED, PREVIEW_ONLY
    dispatch_status: Mapped[str] = mapped_column(String(32), default="PREPARED", nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active_verdict_capture: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    model_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), default="OPENAI_COMPATIBLE", nullable=False)
    generation_settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    compiled_system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    user_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rag_precedents: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    has_rag_precedents: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    evidence_requirements: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    verdict_schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_request_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    canonical_serialized_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_format: Mapped[str] = mapped_column(String(32), default="CANONICAL_JSON", nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    response_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    response_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Integrity verification: VERIFIED, MISMATCH, UNVERIFIED (distinct from delivery status)
    prompt_integrity_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    integrity_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    l1_explanation: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    is_redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
