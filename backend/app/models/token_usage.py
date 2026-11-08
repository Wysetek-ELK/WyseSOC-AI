import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TokenUsageRecord(Base):
    """
    Persistent Token Consumption Ledger stored on Server 1.
    Tracks every token expended across all processes:
    - INCIDENT_TRIAGE (single incident real-time triage)
    - BATCH_TRIAGE (background backlog triage)
    - SIMULATION_REPLAY (dry-run testing & replay lab)
    - POLICY_TESTING (prompt studio evaluation & test synthesis)

    Stores bifurcated metrics:
    - prompt_tokens (input context)
    - completion_tokens (generated output/reasoning)
    - total_tokens
    With process type, model identifier, latency, and operational metadata.
    """
    __tablename__ = "token_usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    process_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    process_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    model_identifier: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    # Bifurcated Token Metrics
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Latency & Cost Analytics
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    executed_by_user: Mapped[str] = mapped_column(String(64), default="system", nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

