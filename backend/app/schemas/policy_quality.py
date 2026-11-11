from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.utils.datetime_utils import utc_now


class GateStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class SimulationStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INCONCLUSIVE = "INCONCLUSIVE"
    EVALUATED_PASSED = "EVALUATED_PASSED"
    EVALUATED_FAILED = "EVALUATED_FAILED"


class QualityGateResult(BaseModel):
    """Evaluation result for one of the 8 mandatory policy quality gates."""
    gate_id: str = Field(..., description="G1 through G8")
    gate_name: str = Field(..., description="Human-readable gate title")
    status: GateStatus = Field(..., description="PASSED, WARNING, or FAILED")
    score: float = Field(..., ge=0.0, description="Dimension score earned")
    max_score: float = Field(..., ge=0.0, description="Maximum possible score for dimension")
    details: str = Field("", description="Detailed explanation of findings")
    blocking_findings: List[str] = Field(default_factory=list, description="Findings that hard-block approval")
    warnings: List[str] = Field(default_factory=list, description="Advisory quality warnings")


class PolicyQualityAssessmentResponse(BaseModel):
    """
    REQ-05 / REQ-06: Comprehensive Policy Quality Assessment Result.
    Contains evaluation across all 8 gates, dimension score breakdown,
    hard blocking findings, and strict approval eligibility.
    """
    assessment_id: str
    rule_identifier: str
    policy_version_number: int
    prompt_version_id: Optional[str] = None
    archetype: str
    validator_version: str = "v2.2.0"
    scoring_model_version: str = "v2.2.0"
    scoring_denominator: float = 100.0
    structural_denominator: float = 85.0
    empirical_denominator: float = 15.0
    
    # Transparent Quality Score (0 to 100)
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall policy quality index (NOT verdict accuracy)")
    structural_quality_score: Optional[float] = Field(None, description="Score based purely on structural policy gates G1-G7 (0-100)")
    structural_raw_score: Optional[float] = Field(None, description="Raw earned points across structural buckets G1-G7 (out of 85)")
    empirical_validation_score: Optional[float] = Field(None, description="Score from G8 empirical simulation (0-15)")
    empirical_validation_status: Optional[str] = Field(None, description="Status of empirical historical validation")
    validation_status: str = Field("NOT_EVALUATED", description="Explicit non-null validation status combining empirical state and simulated provenance")
    gate_scores_total: float = Field(0.0, description="Exact sum of earned points across G1..G8 gate cards")
    gate_max_total: float = Field(100.0, description="Exact sum of max_score across G1..G8 gate cards (100.0 in v2.2.0, 120.0 in legacy v2.0.0)")
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Dimension scores: detection_semantics (20 = G1 10 + G2 10), evidence_contract (20), tp_fp_criteria (20), abstention_escalation (15), internal_consistency (10), historical_simulation (15)"
    )
    
    # 8 Mandatory Gates
    gate_results: Dict[str, QualityGateResult] = Field(default_factory=dict)
    
    # Actionable Findings
    blocking_issues: List[str] = Field(default_factory=list, description="List of hard-blocking reasons preventing approval")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking recommendations")
    missing_evidence_mappings: List[str] = Field(default_factory=list, description="Telemetry fields required by policy but unmapped")
    recommendations: List[str] = Field(default_factory=list, description="Actionable correction guidance for detection engineer")
    hard_gate_failure: bool = Field(False, description="True when one or more blocking gate findings exist")
    
    # Simulation & Approval Eligibility
    simulation_status: SimulationStatus = Field(SimulationStatus.NOT_EVALUATED)
    simulation_run_id: Optional[str] = Field(None, description="Latest historical simulation run identifier when evaluated")
    simulation_provider_type: Optional[str] = Field(None, description="Provider used for simulation (OPENAI_COMPATIBLE, SIMULATED, etc.)")
    simulation_model_identifier: Optional[str] = Field(None, description="Model identifier recorded by the simulation run")
    simulation_execution_provenance: Optional[str] = Field(None, description="Execution provenance recorded for the latest simulation run")
    simulation_is_simulated: Optional[bool] = Field(None, description="True if latest simulation run used simulated/mock inference")
    simulation_sample_count: Optional[int] = Field(None, description="Total evaluated cases in latest simulation run")
    simulation_verified_cases: Optional[int] = Field(None, description="Eligible independently verified ground-truth cases in latest simulation run")
    simulation_policy_digest: Optional[str] = Field(None, description="Policy SHA-256 digest bound to the latest simulation run")
    approval_eligible: bool = Field(False, description="True ONLY if ZERO blocking issues exist regardless of quality_score")
    structural_approval_eligible: bool = Field(False, description="True if structural/contract/security gates (G1-G7) have zero blocking issues")
    empirical_validation_eligible: bool = Field(False, description="True only if empirical historical simulation Gate G8 passed (EVALUATED_PASSED) with a real provider")
    autonomous_operation_eligible: bool = Field(False, description="True only if both structural gates (G1-G7) and non-simulated empirical Gate G8 passed")
    
    # Historical Preservation Metadata (prevents silent rescoring of persisted legacy records)
    historical_assessment_preserved: bool = Field(False, description="True if a persisted PolicyQualityAssessmentRecord exists under its original scoring model")
    persisted_validator_version: Optional[str] = Field(None, description="Validator version stored on the latest persisted assessment record")
    persisted_quality_score: Optional[float] = Field(None, description="Quality score originally persisted without silent rescoring")
    
    # Cryptographic Content Bindings
    policy_digest: str = Field(..., description="SHA-256 digest of 9 policy sections")
    contract_digest: str = Field(..., description="SHA-256 digest of linked Evidence Contract")
    rule_digest: str = Field(..., description="SHA-256 digest of SIEM rule definition")
    archetype_version: str = "v2.0.0"
    evaluated_at: datetime = Field(default_factory=utc_now)


class QualitySummaryItem(BaseModel):
    """Aggregate metrics across the detection rule library."""
    total_rules: int
    rules_with_approved_policies: int
    policies_passing_static_checks: int
    policies_requiring_review: int
    policies_with_critical_issues: int
    policies_with_incomplete_definitions: int
    policies_with_missing_evidence_mappings: int
    policies_lacking_simulation_evidence: int
    quality_score_average: float
    rules_requiring_revalidation: int
