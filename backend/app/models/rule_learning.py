import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.utils.datetime_utils import utc_now


class RuleLearningProfile(Base):
    """
    Maintains per-rule, per-tenant operational learning metrics, accuracy stats,
    and active lifecycle state.
    """
    __tablename__ = "rule_learning_profiles"
    __table_args__ = (
        UniqueConstraint("rule_id", "customer", name="uq_rule_customer_learning"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False)
    rule_identifier: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)
    
    primary_archetype: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    lifecycle_stage: Mapped[str] = mapped_column(String(32), default="LEARNING", index=True, nullable=False)
    # LEARNING, VALIDATION, SUPERVISED_PILOT, CONTROLLED_PRODUCTION, MONITORING, SUSPENDED, REVALIDATION_REQUIRED

    active_prompt_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    active_model_identifier: Mapped[str] = mapped_column(String(64), default="Qwen/Qwen2.5-7B-Instruct-AWQ")

    total_incidents_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_analyst_reviews: Mapped[int] = mapped_column(Integer, default=0)
    verified_tp_count: Mapped[int] = mapped_column(Integer, default=0)
    verified_fp_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_correct_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    abstention_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_failure_count: Mapped[int] = mapped_column(Integer, default=0)

    empirical_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fp_precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tp_recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wilson_lower_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    error_distribution: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    rule = relationship("Rule")
    state_history = relationship("RuleLearningStateHistory", back_populates="profile", cascade="all, delete-orphan", order_by="desc(RuleLearningStateHistory.created_at)")


class RuleLearningStateHistory(Base):
    """
    Immutable audit history recording every transition between rule lifecycle stages.
    """
    __tablename__ = "rule_learning_state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    
    previous_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    new_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    transition_reason: Mapped[str] = mapped_column(Text, default="")
    triggered_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    metrics_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    profile = relationship("RuleLearningProfile", back_populates="state_history")

