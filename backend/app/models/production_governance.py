import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.utils.datetime_utils import utc_now


class RulePromotionRequest(Base):
    """
    Formal request to promote a detection rule between lifecycle stages
    (e.g., from SUPERVISED_PILOT to CONTROLLED_PRODUCTION).
    """
    __tablename__ = "rule_promotion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)

    requested_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    requester_user_id: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    # PENDING, APPROVED, REJECTED, CANCELED

    evaluation_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    supporting_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    justification: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    approval = relationship("RulePromotionApproval", back_populates="request", uselist=False, cascade="all, delete-orphan")


class RulePromotionApproval(Base):
    """
    SOC Manager or Admin binding decision and dual-key sign-off for a promotion request.
    """
    __tablename__ = "rule_promotion_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_promotion_requests.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    approver_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVED, REJECTED
    decision_notes: Mapped[str] = mapped_column(Text, default="")
    approval_signature: Mapped[str] = mapped_column(String(128), default="")
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    request = relationship("RulePromotionRequest", back_populates="approval")


class ProductionAutomationPolicy(Base):
    """
    Fine-grained production automation configuration for an approved rule.
    Strictly gates automated FP closures with safety thresholds.
    """
    __tablename__ = "production_automation_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    allowed_verdicts: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["FALSE_POSITIVE"])
    min_trust_score: Mapped[int] = mapped_column(Integer, default=8)
    min_fp_precision: Mapped[float] = mapped_column(Float, default=0.98)
    daily_closure_limit: Mapped[int] = mapped_column(Integer, default=50)
    current_day_closure_count: Mapped[int] = mapped_column(Integer, default=0)
    
    emergency_disable: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class IncidentAutomationAudit(Base):
    """
    Cryptographic, immutable audit log of every automated incident closure,
    escalation, or safety-interlock block.
    """
    __tablename__ = "incident_automation_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)

    action_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # AUTO_CLOSE_FP, ESCALATE_TP, SAFETY_GATE_ABORT, EMERGENCY_DISABLED_ABORT
    
    siem_target: Mapped[str] = mapped_column(String(64), default="FortiSIEM")
    siem_response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    siem_transaction_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(32), default="SUCCESS", index=True, nullable=False)
    # SUCCESS, FAILED, SIMULATED, REJECTED
    
    safety_checks_passed: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    closure_summary: Mapped[str] = mapped_column(Text, default="")
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

