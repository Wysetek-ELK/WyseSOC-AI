import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DryRunConfig(Base):
    __tablename__ = "dry_run_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    rule_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True)
    prompt_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)

    # Provider: DISABLED, SIMULATED, OPENAI_COMPATIBLE
    provider_type: Mapped[str] = mapped_column(String(32), default="SIMULATED", nullable=False)

    # Split Strategy: ALL, CHRONOLOGICAL_70_30, GROUP_AWARE_HOST
    split_strategy: Mapped[str] = mapped_column(String(32), default="ALL", nullable=False)

    # Filters applied to dataset
    dataset_filters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    rule: Mapped[Optional["Rule"]] = relationship("Rule")
    jobs: Mapped[List["DryRunJob"]] = relationship("DryRunJob", back_populates="config", cascade="all, delete-orphan", order_by="desc(DryRunJob.started_at)")


class DryRunJob(Base):
    __tablename__ = "dry_run_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id: Mapped[str] = mapped_column(String(36), ForeignKey("dry_run_configs.id", ondelete="CASCADE"), index=True, nullable=False)

    # Status: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)

    total_items: Mapped[int] = mapped_column(Integer, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Critical simulation flag
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Error message if failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    config: Mapped["DryRunConfig"] = relationship("DryRunConfig", back_populates="jobs")
    results: Mapped[List["DryRunResult"]] = relationship("DryRunResult", back_populates="job", cascade="all, delete-orphan")


class DryRunResult(Base):
    __tablename__ = "dry_run_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("dry_run_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)

    # Predicted Verdict: TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION
    predicted_verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Integer, default=100)  # Integer percentage 0-100
    reasoning: Mapped[str] = mapped_column(Text, default="")

    supporting_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    analyst_questions: Mapped[List[str]] = mapped_column(JSON, default=list)

    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    model_identifier: Mapped[str] = mapped_column(String(64), default="simulated-v1")
    prompt_version_number: Mapped[int] = mapped_column(Integer, default=1)

    # Validation: VALID, INVALID_SCHEMA, UNEXPECTED_VERDICT
    validation_status: Mapped[str] = mapped_column(String(32), default="VALID", index=True)

    # Critical isolation flag
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["DryRunJob"] = relationship("DryRunJob", back_populates="results")
    incident: Mapped["Incident"] = relationship("Incident")
