import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, BigInteger, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TelemetryTimelineRecord(Base):
    """
    Persistent Historical Telemetry Timeline Ledger stored on Server 1.
    Chronologically tracks and archives all telemetry stages, ingestion events,
    model evaluation milestones, and incident lifecycle transitions for future retrieval.
    """
    __tablename__ = "telemetry_timeline_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # OBSERVATION, INGESTION, TRIAGE, REVIEW, RESOLUTION

    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(String(128), default="Server 1 Database", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="INFO", nullable=False)

    source_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reporting_device: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    epoch_ms: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

