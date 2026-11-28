"""
AIS 3.1 — Idempotent, Checkpointed Live Holdout Benchmark Persistence Models.

Stores:
1. `AIS31BenchmarkRun`: immutable run metadata, frozen policy/manifest hashes, model runtime identity.
2. `AIS31BenchmarkResult`: per-incident wire prompt capture, raw LLM verdict, validated application
   verdict, token accounting, latency, and GPU provenance — strictly isolated from ground truth labels
   during execution.
"""

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


class AIS31BenchmarkRun(Base):
    """Frozen benchmark execution run record with checkpoint and resume support."""

    __tablename__ = "ais31_benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_key: Mapped[str] = mapped_column(String(96), unique=True, index=True, nullable=False)
    cohort_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_type: Mapped[str] = mapped_column(String(32), default="FULL_HOLDOUT_100", nullable=False)
    benchmark_grade: Mapped[str] = mapped_column(
        String(64), default="PROVISIONAL_SINGLE_REVIEW_BENCHMARK", nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True, nullable=False)

    expected_model: Mapped[str] = mapped_column(String(128), default="Qwen/Qwen3-14B-AWQ", nullable=False)
    actual_model_returned: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    vllm_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context_limit: Mapped[int] = mapped_column(Integer, default=8192, nullable=False)
    max_completion_tokens: Mapped[int] = mapped_column(Integer, default=768, nullable=False)
    target_input_budget: Mapped[int] = mapped_column(Integer, default=7424, nullable=False)

    neutral_prompt_version: Mapped[str] = mapped_column(String(64), default="NEUTRAL_SOC_BASELINE_V2", nullable=False)
    neutral_prompt_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    policy_freeze_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    rag_excluded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memory_excluded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    enable_thinking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    total_target_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by_user: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    runtime_manifest_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    results: Mapped[List["AIS31BenchmarkResult"]] = relationship(
        "AIS31BenchmarkResult", back_populates="run", cascade="all, delete-orphan"
    )


class AIS31BenchmarkResult(Base):
    """Per-incident immutable benchmark execution record (strictly free of ground truth labels)."""

    __tablename__ = "ais31_benchmark_results"
    __table_args__ = (
        UniqueConstraint("run_id", "fortisiem_incident_id", name="uq_ais31_run_incident"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ais31_benchmark_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cohort_item_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    incident_db_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    fortisiem_incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), default="")
    sequence_rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    execution_status: Mapped[str] = mapped_column(String(32), default="COMPLETED", index=True, nullable=False)
    # COMPLETED, FAILED, QUARANTINED, CONTEXT_OVERFLOW
    eligibility_state: Mapped[str] = mapped_column(String(32), default="ELIGIBLE", nullable=False)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_sha256: Mapped[str] = mapped_column(String(64), default="")
    canonical_evidence_sha256: Mapped[str] = mapped_column(String(64), default="")
    rule_definition_sha256: Mapped[str] = mapped_column(String(64), default="")
    policy_sha256: Mapped[str] = mapped_column(String(64), default="")
    wire_prompt_sha256: Mapped[str] = mapped_column(String(64), default="")
    result_integrity_sha256: Mapped[str] = mapped_column(String(64), default="")

    model_identifier: Mapped[str] = mapped_column(String(128), default="Qwen/Qwen3-14B-AWQ")
    actual_model_returned: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    inference_request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    request_timestamp_utc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_timestamp_utc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    gpu_provenance: Mapped[str] = mapped_column(String(64), default="LIVE_SERVER2_VLLM", nullable=False)
    error_classification: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Exact wire capture (restricted to admin/eval inspector)
    wire_system_prompt: Mapped[str] = mapped_column(Text, default="")
    wire_user_content: Mapped[str] = mapped_column(Text, default="")
    wire_token_audit_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_response_text: Mapped[str] = mapped_column(Text, default="")
    raw_vllm_envelope_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    parsed_output_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Separated Verdict Layers
    raw_llm_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    raw_llm_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parsed_verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    validated_application_verdict: Mapped[str] = mapped_column(String(32), default="REQUIRES_ATTENTION")
    validator_status: Mapped[str] = mapped_column(String(64), default="UNVERIFIED")
    validator_action: Mapped[str] = mapped_column(String(64), default="ABSTENTION_PRESERVED")
    validator_rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validator_reason_codes_json: Mapped[List[str]] = mapped_column(JSON, default=list)
    deterministic_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_grounding_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    grounding_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    inconclusive_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mode_b_policy_eligibility: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    run: Mapped["AIS31BenchmarkRun"] = relationship("AIS31BenchmarkRun", back_populates="results")
