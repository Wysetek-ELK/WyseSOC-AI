import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Integer, Float, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BulkQualityAuditJobRecord(Base):
    """
    Persisted record of bulk policy quality audit execution across detection rules.
    """
    __tablename__ = "bulk_quality_audit_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    
    total_rules: Mapped[int] = mapped_column(Integer, default=0)
    processed_rules: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    review_required_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    incomplete_definitions_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    
    average_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    summary_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
