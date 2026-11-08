from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class GateStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class SimulationStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
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
    validator_version: str = "v2.0.0"
    
    # Transparent Quality Score (0 to 100)
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall policy quality index (NOT verdict accuracy)")
    structural_quality_score: Optional[float] = Field(None, description="Score based purely on structural policy gates G1-G7 (0-100)")
    empirical_validation_score: Optional[float] = Field(None, description="Score from G8 empirical simulation (0-15)")
    empirical_validation_status: Optional[str] = Field(None, description="Status of empirical historical validation")
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Dimension scores: detection_semantics (20), evidence_contract (20), tp_fp_criteria (20), abstention_escalation (15), internal_consistency (10), historical_simulation (15)"
    )
    
    # 8 Mandatory Gates
    gate_results: Dict[str, QualityGateResult] = Field(default_factory=dict)
    
    # Actionable Findings
    blocking_issues: List[str] = Field(default_factory=list, description="List of hard-blocking reasons preventing approval")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking recommendations")
    missing_evidence_mappings: List[str] = Field(default_factory=list, description="Telemetry fields required by policy but unmapped")
    recommendations: List[str] = Field(default_factory=list, description="Actionable correction guidance for detection engineer")
    
    # Simulation & Approval Eligibility
    simulation_status: SimulationStatus = Field(SimulationStatus.NOT_EVALUATED)
    approval_eligible: bool = Field(False, description="True ONLY if ZERO blocking issues exist regardless of quality_score")
    
    # Cryptographic Content Bindings
    policy_digest: str = Field(..., description="SHA-256 digest of 9 policy sections")
    contract_digest: str = Field(..., description="SHA-256 digest of linked Evidence Contract")
    rule_digest: str = Field(..., description="SHA-256 digest of SIEM rule definition")
    archetype_version: str = "v2.0.0"
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


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
