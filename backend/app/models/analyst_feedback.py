import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.utils.datetime_utils import utc_now


class AnalystVerdictReview(Base):
    """
    Persists double-blind and standard human analyst determinations,
    recording agreement/disagreement comparisons and establishing verified ground truth.
    """
    __tablename__ = "analyst_verdict_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    investigation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("investigations.id", ondelete="SET NULL"), index=True, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)

    reviewer_id: Mapped[str] = mapped_column(String(128), default="analyst", index=True, nullable=False)
    analyst_verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE
    analyst_notes: Mapped[str] = mapped_column(Text, default="")
    correction_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evidence_references: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Double-Blind review support
    blind_mode_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revealed_ai_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    comparison_outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # AGREEMENT_TP, AGREEMENT_FP, AI_FALSE_ALARM, CRITICAL_MISSED_TP, ANALYST_RESOLVED_ABSTENTION, DISPUTED

    ground_truth_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True)
    # VERIFIED, ADJUDICATED, DISPUTED, UNVERIFIED

    review_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    incident = relationship("Incident")
    adjudication = relationship("AnalystReviewAdjudication", back_populates="review", uselist=False, cascade="all, delete-orphan")


class AnalystReviewAdjudication(Base):
    """
    Senior Analyst / L2 Manager binding adjudication for disputed or high-risk analyst reviews.
    """
    __tablename__ = "analyst_review_adjudications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyst_verdict_reviews.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    adjudicator_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    
    final_verdict: Mapped[str] = mapped_column(String(32), nullable=False)  # TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE
    adjudication_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    original_dispute_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    review = relationship("AnalystVerdictReview", back_populates="adjudication")

