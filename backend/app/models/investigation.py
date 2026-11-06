import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    assigned_to_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Status: PENDING_REVIEW, ASSIGNED, IN_PROGRESS, AWAITING_INFORMATION, REVIEWED, CLOSED_DRY_RUN
    status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW", index=True, nullable=False)

    # Analyst verdict: TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION, or None if in progress
    analyst_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    verdict_reason: Mapped[str] = mapped_column(Text, default="")
    analyst_notes: Mapped[str] = mapped_column(Text, default="")

    # Dispute and verification flags (Data Quality Workflow)
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_independently_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Explicit insufficient evidence reason
    insufficient_evidence_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
    questions: Mapped[List["InvestigationQuestion"]] = relationship("InvestigationQuestion", back_populates="investigation", cascade="all, delete-orphan")
    evidence_items: Mapped[List["InvestigationEvidence"]] = relationship("InvestigationEvidence", back_populates="investigation", cascade="all, delete-orphan")


class InvestigationQuestion(Base):
    __tablename__ = "investigation_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="")

    asked_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answered_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="questions")


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)

    evidence_type: Mapped[str] = mapped_column(String(64), default="TELEMETRY")  # TELEMETRY, LOG, PROCESS_TREE, FILE_HASH, NETWORK
    reference_key: Mapped[str] = mapped_column(String(256), default="")
    evidence_content: Mapped[str] = mapped_column(Text, default="")
    analyst_rationale: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="evidence_items")

