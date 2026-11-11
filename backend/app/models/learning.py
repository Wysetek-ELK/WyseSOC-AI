import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class LearningRecord(Base):
    """
    Verified-case knowledge base organized by SIEM Rule ID.
    Only independently verified cases through the data quality workflow
    are eligible for use as trusted training/benchmark ground truth.
    """
    __tablename__ = "learning_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)

    verified_verdict: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION
    analyst_explanation: Mapped[str] = mapped_column(Text, default="")

    tp_indicators: Mapped[List[str]] = mapped_column(JSON, default=list)
    fp_indicators: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    evidence_references: Mapped[List[str]] = mapped_column(JSON, default=list)
    answered_questions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    verification_status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW", index=True)  # PENDING_REVIEW, VERIFIED, REJECTED, DISPUTED
    feedback_timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule")
    incident: Mapped["Incident"] = relationship("Incident")

