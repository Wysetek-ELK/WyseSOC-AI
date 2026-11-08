import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VerdictTrustAssessmentRecord(Base):
    """
    Persists deterministic trust assessments and guardrail outcomes for an evaluated incident.
    """
    __tablename__ = "verdict_trust_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    archetype: Mapped[str] = mapped_column(String(64), default="UNKNOWN")

    suggested_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    trust_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1 to 10 ordinal
    raw_trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_status: Mapped[str] = mapped_column(String(32), default="INSUFFICIENT", index=True)

    score_dimensions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    supporting_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    contradictory_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    confidence_limitations: Mapped[List[str]] = mapped_column(JSON, default=list)

    historical_validation_status: Mapped[str] = mapped_column(String(32), default="UNCALIBRATED")
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    calibrated_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    applicable_policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applicable_contract_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    escalation_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    human_readable_explanation: Mapped[str] = mapped_column(Text, default="")
    model_identifier: Mapped[str] = mapped_column(String(64), default="default-model")
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EvidenceSufficiencyAssessmentRecord(Base):
    """
    Persists granular evidence sufficiency metrics and coverage breakdown.
    """
    __tablename__ = "evidence_sufficiency_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    archetype: Mapped[str] = mapped_column(String(64), default="UNKNOWN")

    overall_sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    required_coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    integrity_provenance_score: Mapped[float] = mapped_column(Float, default=0.0)
    consistency_corroboration_score: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    evidence_status: Mapped[str] = mapped_column(String(32), default="INSUFFICIENT", index=True)
    mandatory_fields_present: Mapped[List[str]] = mapped_column(JSON, default=list)
    mandatory_fields_missing: Mapped[List[str]] = mapped_column(JSON, default=list)
    conditional_fields_evaluated: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    optional_enrichment_present: Mapped[List[str]] = mapped_column(JSON, default=list)
    unsupported_fields_requested: Mapped[List[str]] = mapped_column(JSON, default=list)
    contradictions_detected: Mapped[List[str]] = mapped_column(JSON, default=list)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GroundTruthValidationRecord(Base):
    """
    Maintains verified evaluation ground truth and prevents leakage into inference inputs.
    """
    __tablename__ = "ground_truth_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    original_analyst_verdict: Mapped[str] = mapped_column(String(64), default="")
    adjudicated_label: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # VERIFIED_TP, VERIFIED_FP, UNVERIFIED, CONFLICTING
    provenance: Mapped[str] = mapped_column(String(64), default="HISTORICAL_IMPORT")
    analyst_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    label_reliability: Mapped[float] = mapped_column(Float, default=1.0)
    dataset_partition: Mapped[str] = mapped_column(String(32), default="LOCKED_TEST", index=True)
    is_eligible_for_evaluation: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class HistoricalEvaluationRunRecord(Base):
    """
    Persists historical dry-run evaluation runs, metrics, and regression comparisons.
    """
    __tablename__ = "historical_evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    archetype: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(64), default="default-dataset")
    dataset_hash: Mapped[str] = mapped_column(String(64), default="")
    policy_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    baseline_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    validation_state: Mapped[str] = mapped_column(String(32), default="INCONCLUSIVE", index=True)

    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_cases: Mapped[int] = mapped_column(Integer, default=0)
    verified_ground_truth_cases: Mapped[int] = mapped_column(Integer, default=0)

    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    selective_metrics: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    calibration_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    regression_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    results: Mapped[List["HistoricalEvaluationResultRecord"]] = relationship(
        "HistoricalEvaluationResultRecord",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class HistoricalEvaluationResultRecord(Base):
    """
    Per-incident evaluation result inside a historical evaluation run.
    """
    __tablename__ = "historical_evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("historical_evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    suggested_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    ground_truth_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    trust_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_sufficiency_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_status: Mapped[str] = mapped_column(String(32), default="INSUFFICIENT")

    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_abstained: Mapped[bool] = mapped_column(Boolean, default=False)
    is_critical_error: Mapped[bool] = mapped_column(Boolean, default=False)  # FN: missed true positive

    claims_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    run: Mapped["HistoricalEvaluationRunRecord"] = relationship("HistoricalEvaluationRunRecord", back_populates="results")
