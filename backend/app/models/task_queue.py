import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class QueuedTask(Base):
    """
    Durable Task Queue Ledger stored on Server 1.
    Tracks asynchronous execution across Celery / Redis and in-process execution:
    - LIVE_TRIAGE
    - BATCH_TRIAGE
    - SIMULATION_REPLAY
    - FORTISIEM_PULL
    """
    __tablename__ = "queued_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    queue_name: Mapped[str] = mapped_column(String(64), index=True, default="live_triage", nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), index=True, default="INCIDENT", nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    # State Machine: QUEUED -> PROCESSING -> COMPLETED / FAILED / RETRYING / DEAD_LETTER
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

