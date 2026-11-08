import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PolicyDriftEvent(Base):
    """
    Persisted policy drift or revalidation notification event.
    """
    __tablename__ = "policy_drift_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False)
    prompt_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    
    trigger_type: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(String(512), default="")
    changed_fields: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    revalidation_required: Mapped[bool] = mapped_column(Boolean, default=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    rule = relationship("Rule")
    prompt_version = relationship("PromptVersion")
