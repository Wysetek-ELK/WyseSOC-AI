import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Float, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PolicyQualityAssessmentRecord(Base):
    """
    Persisted policy quality assessment result evaluated across 8 mandatory gates.
    """
    __tablename__ = "policy_quality_assessments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False)
    prompt_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), index=True, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    
    archetype: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    approval_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    simulation_status: Mapped[str] = mapped_column(String(32), default="NOT_EVALUATED")
    
    score_breakdown: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict)
    gate_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    blocking_issues: Mapped[List[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_evidence_mappings: Mapped[List[str]] = mapped_column(JSON, default=list)
    recommendations: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    policy_digest: Mapped[str] = mapped_column(String(64), default="")
    contract_digest: Mapped[str] = mapped_column(String(64), default="")
    rule_digest: Mapped[str] = mapped_column(String(64), default="")
    validator_version: Mapped[str] = mapped_column(String(32), default="v2.0.0")
    
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    rule = relationship("Rule")
    prompt_version = relationship("PromptVersion")
