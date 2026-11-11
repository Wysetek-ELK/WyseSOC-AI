import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    rule_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True)
    import_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Core Normalized SIEM fields
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", index=True)
    event_severity: Mapped[str] = mapped_column(String(32), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=1, index=True)
    status_name: Mapped[str] = mapped_column(String(64), default="Open")
    category: Mapped[str] = mapped_column(String(128), default="")
    subcategory: Mapped[str] = mapped_column(String(128), default="")
    source_ip: Mapped[str] = mapped_column(String(64), default="", index=True)
    reporting_device: Mapped[str] = mapped_column(String(128), default="")
    reporting_ip: Mapped[str] = mapped_column(String(64), default="")
    customer: Mapped[str] = mapped_column(String(128), default="")
    ticket_id: Mapped[str] = mapped_column(String(64), default="")

    # Normalized Epoch Timestamps (stored in milliseconds as received from SIEM)
    first_seen_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    last_seen_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    updated_at_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Original unmodified raw JSON payload
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Persisted AI Evaluation Verdict and telemetry for instant re-use
    ai_verdict: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    rule: Mapped[Optional["Rule"]] = relationship("Rule", back_populates="incidents")
    import_job: Mapped[Optional["ImportJob"]] = relationship("ImportJob", back_populates="incidents")
    events: Mapped[List["IncidentEvent"]] = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan")
    ground_truth: Mapped[Optional["HistoricalGroundTruth"]] = relationship(
        "HistoricalGroundTruth",
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan"
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    event_receive_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    event_type: Mapped[str] = mapped_column(String(128), default="")
    raw_log: Mapped[str] = mapped_column(Text, default="")
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # Generic nested vendor attributes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")


class HistoricalGroundTruth(Base):
    """
    CRITICAL SECURITY LAYER:
    Maintains historical verdict and closure-related data in a dedicated table,
    strictly isolated from incident investigation inputs.
    Never included in model-facing feature payloads.
    """
    __tablename__ = "historical_ground_truth"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    resolution: Mapped[str] = mapped_column(String(64), default="", index=True)  # "True Positive", "False Positive", etc.
    cleared_reason: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    cleared_user: Mapped[str] = mapped_column(String(128), default="")
    cleared_time_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    resolved_at_epoch: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_ml_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="ground_truth")

