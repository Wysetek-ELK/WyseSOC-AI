import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.utils.datetime_utils import utc_now


class AnalystVerdictReview(Base):
    """
    Persists double-blind, operational, and benchmark certification human analyst determinations,
    recording agreement/disagreement comparisons and establishing verified ground truth.
    """
    __tablename__ = "analyst_verdict_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    investigation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("investigations.id", ondelete="SET NULL"), index=True, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)

    reviewer_id: Mapped[str] = mapped_column(String(128), default="analyst", index=True, nullable=False)
    analyst_verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE, INCONCLUSIVE
    analyst_notes: Mapped[str] = mapped_column(Text, default="")
    correction_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evidence_references: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Double-Blind review support
    blind_mode_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revealed_ai_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    comparison_outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # AGREEMENT_TP, AGREEMENT_FP, AI_FALSE_ALARM, CRITICAL_MISSED_TP, ANALYST_RESOLVED_ABSTENTION, DISPUTED

    ground_truth_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True)
    # VERIFIED, ADJUDICATED, DISPUTED, UNVERIFIED, DRAFT, GT2_SINGLE_REVIEW, GT3_CERTIFIED, CERTIFIED_INCONCLUSIVE

    # AIS 2.6f Benchmark Certification & Governance Extensions
    benchmark_cohort_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    certification_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    review_mode: Mapped[str] = mapped_column(String(32), default="OPERATIONAL", nullable=False, index=True)
    detection_correctness: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # MATCHED, NOT_MATCHED, UNKNOWN
    authorization_context: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # AUTHORIZED, UNAUTHORIZED, UNKNOWN, NOT_APPLICABLE
    confidence_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # LOW, MEDIUM, HIGH
    evidence_sufficiency_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # SUFFICIENT, INSUFFICIENT, PARTIAL
    evidence_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rule_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    additional_evidence_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    attestation_flags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exposure_risk_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    excluded_from_learning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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


class BenchmarkCohort(Base):
    """
    Immutable frozen benchmark dataset definition (e.g., AIS_2_6E_FROZEN_20).
    Maintains strict separation from operational queues and AI training memory.
    """
    __tablename__ = "benchmark_cohorts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cohort_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32), default="2.6e", nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    required_reviewers: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    excluded_from_learning: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    items: Mapped[List["BenchmarkCohortItem"]] = relationship(
        "BenchmarkCohortItem", back_populates="cohort", cascade="all, delete-orphan"
    )


class BenchmarkCohortItem(Base):
    """
    Authoritative membership & certification state of each frozen benchmark incident.
    Separates immutable cohort membership/hashes from mutable review/certification state.
    """
    __tablename__ = "benchmark_cohort_items"
    __table_args__ = (
        UniqueConstraint("cohort_id", "fortisiem_incident_id", name="uq_cohort_fortisiem_incident"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cohort_id: Mapped[str] = mapped_column(String(36), ForeignKey("benchmark_cohorts.id", ondelete="CASCADE"), index=True, nullable=False)
    incident_db_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="SET NULL"), index=True, nullable=True)
    fortisiem_incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), default="")
    expected_policy_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expected_policy_prompt_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT")

    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    priority_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    raw_evidence_sha256: Mapped[str] = mapped_column(String(64), default="")
    rule_definition_sha256: Mapped[str] = mapped_column(String(64), default="")
    canonical_evidence_sha256: Mapped[str] = mapped_column(String(64), default="")

    eligibility_status: Mapped[str] = mapped_column(String(32), default="ELIGIBLE", nullable=False)
    certification_status: Mapped[str] = mapped_column(String(32), default="GT0_UNREVIEWED", index=True, nullable=False)
    # GT0_UNREVIEWED, GT1_HISTORICAL_ONLY, IN_PROGRESS, GT2_SINGLE_REVIEW,
    # PENDING_SECOND_REVIEW, CONFLICT_PENDING_ADJUDICATION, GT3_CERTIFIED, CERTIFIED_INCONCLUSIVE
    certified_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    assigned_reviewer_1: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    assigned_reviewer_2: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    exposure_risk_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exposure_risk_reason: Mapped[str] = mapped_column(Text, default="")
    certification_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    cohort: Mapped["BenchmarkCohort"] = relationship("BenchmarkCohort", back_populates="items")
    incident: Mapped[Optional["Incident"]] = relationship("Incident")


class BenchmarkReviewRevision(Base):
    """
    Immutable audit history when an authorized administrator/senior analyst reopens or revises a locked benchmark review.
    """
    __tablename__ = "benchmark_review_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyst_verdict_reviews.id", ondelete="CASCADE"), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    previous_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    new_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_rationale: Mapped[str] = mapped_column(Text, default="")
    new_rationale: Mapped[str] = mapped_column(Text, default="")
    revised_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    revision_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

