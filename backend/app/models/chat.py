import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.utils.datetime_utils import utc_now


class SentinelConversation(Base):
    """
    Persistent Verdictum Sentinel chat conversation owned strictly by a single user.
    Preserves investigation threads across page reloads without cross-user leakage.
    """
    __tablename__ = "sentinel_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256), default="Sentinel Investigation", nullable=False)
    attached_incident_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, index=True, nullable=False)

    messages: Mapped[List["SentinelMessage"]] = relationship(
        "SentinelMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SentinelMessage.created_at.asc()",
    )


class SentinelMessage(Base):
    """
    Persistent message and execution telemetry for Verdictum Sentinel Chat.
    Tracks explicit response lifecycle state, token accounting, finish reason,
    and safe continuation lineage.
    """
    __tablename__ = "sentinel_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sentinel_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reasoning_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle & completion integrity
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED", index=True, nullable=False)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stream_termination: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Model & token telemetry
    model_identifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reasoning_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    effective_context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Continuation lineage
    is_continuation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_message_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    continuation_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attached_incident_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    conversation: Mapped["SentinelConversation"] = relationship("SentinelConversation", back_populates="messages")
