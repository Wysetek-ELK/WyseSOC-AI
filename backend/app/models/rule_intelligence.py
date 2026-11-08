import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Float, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RuleIntelligenceSnapshot(Base):
    """
    Persisted rule intelligence and semantics snapshot extracted by RuleIntelligenceAnalyzer.
    """
    __tablename__ = "rule_intelligence_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    rule_identifier: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    
    primary_archetype: Mapped[str] = mapped_column(String(64), index=True, default="UNKNOWN")
    secondary_archetype: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    definition_status: Mapped[str] = mapped_column(String(32), index=True, default="UNKNOWN")
    source_provenance: Mapped[str] = mapped_column(String(64), default="HEURISTIC_PARSER")
    
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    aggregation_window: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    
    semantics_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    rule_digest: Mapped[str] = mapped_column(String(64), default="")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rule = relationship("Rule")
