import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Float, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RuleMaturityEvaluation(Base):
    """
    Tracks the conservative automation readiness progression of each SIEM rule.
    States:
    - NOT_TESTED (Initial)
    - LEARNING
    - UNDER_EVALUATION
    - CANDIDATE_FOR_AUTOMATION (Meets strict threshold criteria)
    - APPROVED_FOR_AUTOMATION (Requires human Administrator sign-off)
    """
    __tablename__ = "rule_maturity_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)

    maturity_status: Mapped[str] = mapped_column(String(32), default="NOT_TESTED", index=True, nullable=False)

    # Calculated metrics from real evaluation runs
    precision_score: Mapped[float] = mapped_column(Float, default=0.0)
    recall_score: Mapped[float] = mapped_column(Float, default=0.0)
    f1_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)

    # Evidence and gap analysis
    unresolved_evidence_gaps: Mapped[List[str]] = mapped_column(JSON, default=list)
    recommendation_explanation: Mapped[str] = mapped_column(Text, default="")

    # Governance: Mandatory human administrator approval
    is_admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approval_notes: Mapped[str] = mapped_column(Text, default="")

    latest_test_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationship
    rule: Mapped["Rule"] = relationship("Rule")

