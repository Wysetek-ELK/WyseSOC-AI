"""
AIS 3.2 — Database Models for Dynamic Rule Contracts, Organizational Context,
and AIS 3.2 Development/Evaluation Provenance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.datetime_utils import utc_now


class RuleContractRecord(Base):
    """Versioned, auditable Dynamic Rule Contract persisted in PostgreSQL."""

    __tablename__ = "ais32_rule_contracts"
    __table_args__ = (
        UniqueConstraint("rule_db_id", "contract_version", name="uq_ais32_rule_contract_ver"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rule_db_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fortisiem_rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    rule_definition_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    primary_archetype: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    secondary_archetype: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mapping_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    approval_state: Mapped[str] = mapped_column(String(32), default="PROVISIONAL", index=True, nullable=False)
    # PROVISIONAL, APPROVED, DRAFT, REVOKED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    contract_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    policy_provenance: Mapped[str] = mapped_column(String(64), default="RULE_INTELLIGENCE_ENGINE_V3_2", nullable=False)
    contract_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    overrides_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reviewer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    rule = relationship("Rule")


class OrganizationalContextRecord(Base):
    """
    Authoritative PostgreSQL store for verified, tenant-scoped organizational context
    (authorized scanners, internal IP ranges, assets, maintenance windows, exceptions, etc.).
    """

    __tablename__ = "ais32_organizational_contexts"
    __table_args__ = (
        UniqueConstraint("customer", "context_type", "dedup_hash", name="uq_ais32_org_ctx_dedup"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer: Mapped[str] = mapped_column(String(128), default="DEFAULT", index=True, nullable=False)
    context_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    context_value: Mapped[str] = mapped_column(String(512), nullable=False)
    match_pattern: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), default="MANUAL_ADMIN", nullable=False)

    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True, nullable=False)
    # VERIFIED, UNVERIFIED, EXPIRED, REJECTED
    approval_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    # PENDING, APPROVED, REJECTED, REVOKED
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    record_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class IntelligenceExecutionRecord(Base):
    """
    AIS 3.2 execution provenance record capturing Mode A/B benchmark runs,
    paired evaluations, token budgets, semantic dimensions, and validator module diagnostics.
    """

    __tablename__ = "ais32_execution_records"
    __table_args__ = (
        UniqueConstraint("run_id", "mode", "fortisiem_incident_id", name="uq_ais32_exec_run_mode_inc"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_key: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    cohort_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # MODE_A | MODE_B
    fortisiem_incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    incident_db_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    archetype: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    contract_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    contract_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    wire_prompt_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    model_identifier: Mapped[str] = mapped_column(String(128), default="Qwen/Qwen3-14B-AWQ", nullable=False)
    actual_model_returned: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    inference_request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gpu_provenance: Mapped[str] = mapped_column(String(64), default="LIVE_SERVER2_VLLM", nullable=False)

    execution_status: Mapped[str] = mapped_column(String(32), default="COMPLETED", index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    raw_llm_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    validated_verdict: Mapped[str] = mapped_column(String(32), default="REQUIRES_ATTENTION", nullable=False)
    effective_operational_verdict: Mapped[str] = mapped_column(String(32), default="REQUIRES_ATTENTION", nullable=False)
    validator_status: Mapped[str] = mapped_column(String(64), default="UNVERIFIED", nullable=False)
    validator_module: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    grounding_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    semantic_dimensions_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    token_audit_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_audit_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    org_context_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validator_detail_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    parsed_output_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    wire_system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    wire_user_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_response_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
