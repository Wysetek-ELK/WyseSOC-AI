import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PilotConfiguration(Base):
    """
    Versioned SOC Pilot control configuration (Phase 9).
    Defaults strictly to DISABLED with zero autonomous closure or external SIEM writeback.
    """
    __tablename__ = "pilot_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pilot_name: Mapped[str] = mapped_column(String(128), default="Default SOC Pilot", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="Controlled SOC Pilot for Evidence-First Verdict Validation")
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active_config: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # DISABLED | SHADOW | ANALYST_ASSISTED
    mode: Mapped[str] = mapped_column(String(32), default="DISABLED", index=True, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Scope filters (empty list = all rules/archetypes/severities)
    selected_rule_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    selected_archetypes: Mapped[List[str]] = mapped_column(JSON, default=list)
    included_severities: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    ingestion_source: Mapped[str] = mapped_column(String(32), default="ALL", nullable=False)  # ALL | LIVE | HISTORICAL

    # Operational budgets & limits
    daily_evaluation_budget: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    hourly_evaluation_budget: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_concurrent_inference: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    request_timeout_seconds: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    # Safety & Governance Controls
    require_analyst_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approved_policy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_external_writeback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_auto_incident_closure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_handling_policy: Mapped[str] = mapped_column(String(64), default="ABSTAIN_AND_LOG", nullable=False)
    consecutive_error_pause_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    reporting_schedule: Mapped[str] = mapped_column(String(32), default="HOURLY", nullable=False)

    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class PilotConfigHistory(Base):
    """
    Immutable version history of every pilot configuration change, activation, pause, or rollback.
    """
    __tablename__ = "pilot_config_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pilot_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_configurations.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class PilotEvaluationRecord(Base):
    """
    Stores SOC Pilot AI recommendations & human analyst feedback separately from authoritative
    SIEM closure decisions, preserving complete provenance and preventing self-confirming loops.
    """
    __tablename__ = "pilot_evaluations"
    __table_args__ = (
        Index("ix_pilot_eval_idempotency", "idempotency_key", unique=True),
        Index("ix_pilot_eval_pilot_created", "pilot_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(192), nullable=False)
    pilot_id: Mapped[str] = mapped_column(String(36), ForeignKey("pilot_configurations.id", ondelete="CASCADE"), index=True, nullable=False)
    pilot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    incident_db_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    archetype: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM")

    execution_mode: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # SHADOW | ANALYST_ASSISTED
    source_type: Mapped[str] = mapped_column(String(32), default="LIVE", index=True, nullable=False)  # LIVE | HISTORICAL | SIMULATED
    eligibility_status: Mapped[str] = mapped_column(String(32), default="EVALUATED", index=True, nullable=False)

    # AI recommendation & independent validation (immutable once written)
    proposed_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    validated_verdict: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    validation_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    abstention_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trust_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_trust_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_completeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    grounding_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    supporting_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    contradictory_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Provenance & resource telemetry
    policy_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    policy_digest: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model_identifier: Mapped[str] = mapped_column(String(128), default="")
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human analyst review & supervisor verification (never overwrites validated_verdict)
    analyst_feedback_action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # ACCEPTED | OVERRIDDEN | DISPUTED | REQUESTED_EVIDENCE
    analyst_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    analyst_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyst_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    analyst_decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    supervisor_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supervisor_user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    supervisor_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    supervisor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

