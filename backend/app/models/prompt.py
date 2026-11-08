import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RulePrompt(Base):
    __tablename__ = "rule_prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), default="")
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule")
    versions: Mapped[List["PromptVersion"]] = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan", order_by="desc(PromptVersion.version_number)")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_prompts.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status: DRAFT, APPROVED, ARCHIVED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True, nullable=False)
    is_template_draft: Mapped[bool] = mapped_column(Boolean, default=True)

    # AIS 2.0 Quality Workflow State & Score
    quality_status: Mapped[str] = mapped_column(String(32), default="GENERATED_DRAFT", nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_assessment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Prompt Components
    common_prompt: Mapped[str] = mapped_column(Text, default="")
    rule_specific_prompt: Mapped[str] = mapped_column(Text, default="")
    detection_conditions: Mapped[str] = mapped_column(Text, default="")
    required_evidence: Mapped[str] = mapped_column(Text, default="")
    tp_indicators: Mapped[str] = mapped_column(Text, default="")
    fp_indicators: Mapped[str] = mapped_column(Text, default="")
    missing_info_criteria: Mapped[str] = mapped_column(Text, default="")
    escalation_conditions: Mapped[str] = mapped_column(Text, default="")
    analyst_questions: Mapped[List[str]] = mapped_column(JSON, default=list)

    change_summary: Mapped[str] = mapped_column(String(512), default="Initial draft")

    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    prompt: Mapped["RulePrompt"] = relationship("RulePrompt", back_populates="versions")

