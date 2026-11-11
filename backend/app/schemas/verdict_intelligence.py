"""
Pydantic Schemas for Agent Intelligence Studio 2.1 — Dry-Run Intelligence Validation.
Covers:
- Evidence Sufficiency Engine schemas
- Verdict Trustworthiness Engine schemas
- Claim Grounding & Verification schemas
- Historical Ground Truth Validation schemas
- Empirical Accuracy Evaluation schemas
- Calibration Analysis & Uncertainty schemas
- Simulation Run & Regression Comparison schemas
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------

class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    UNCALIBRATED = "UNCALIBRATED"


class UserVisibleVerdict(str, Enum):
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    REQUIRES_ANALYST_ATTENTION = "REQUIRES_ANALYST_ATTENTION"


class GroundTruthLabel(str, Enum):
    VERIFIED_TP = "VERIFIED_TP"
    VERIFIED_FP = "VERIFIED_FP"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class GroundTruthProvenance(str, Enum):
    SIEM_CLOSED = "SIEM_CLOSED"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    ADJUDICATION_PANEL = "ADJUDICATION_PANEL"
    HISTORICAL_IMPORT = "HISTORICAL_IMPORT"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class EvaluationValidationState(str, Enum):
    VALIDATED = "VALIDATED"
    PASS = "PASS"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_ASSESSED = "NOT_ASSESSED"
    EVALUATION_FAILED = "EVALUATION_FAILED"


class DatasetPartition(str, Enum):
    TRAIN = "TRAIN"
    TUNING = "TUNING"
    CALIBRATION = "CALIBRATION"
    LOCKED_TEST = "LOCKED_TEST"


class ClaimType(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    HYPOTHESIS = "HYPOTHESIS"
    CALCULATION = "CALCULATION"
    EXTERNAL_LOOKUP = "EXTERNAL_LOOKUP"


# --------------------------------------------------------------------------
# 1. Evidence Sufficiency Schemas
# --------------------------------------------------------------------------

class EvidenceFieldAudit(BaseModel):
    field_name: str
    is_mandatory: bool
    is_present: bool
    observed_value: Optional[Any] = None
    data_source: Optional[str] = None
    provenance: Optional[str] = None
    freshness_seconds: Optional[float] = None
    is_valid: bool = True
    validation_error: Optional[str] = None


class EvidenceSufficiencyAssessmentResult(BaseModel):
    incident_id: str
    rule_id: str
    archetype: str
    overall_sufficiency_score: float = Field(..., ge=0.0, le=100.0, description="0-100 Evidence Sufficiency Score")
    required_coverage_score: float = Field(..., ge=0.0, le=40.0, description="40% weight: mandatory field coverage")
    integrity_provenance_score: float = Field(..., ge=0.0, le=25.0, description="25% weight: source reliability & provenance")
    consistency_corroboration_score: float = Field(..., ge=0.0, le=20.0, description="20% weight: internal consistency & independent corroboration")
    freshness_relevance_score: float = Field(..., ge=0.0, le=15.0, description="15% weight: temporal freshness & relevance")
    evidence_status: EvidenceStatus
    mandatory_fields_present: List[str] = Field(default_factory=list)
    mandatory_fields_missing: List[str] = Field(default_factory=list)
    conditional_fields_evaluated: List[Dict[str, Any]] = Field(default_factory=list)
    optional_enrichment_present: List[str] = Field(default_factory=list)
    unsupported_fields_requested: List[str] = Field(default_factory=list)
    contradictions_detected: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def status(self) -> EvidenceStatus:
        return self.evidence_status

    @property
    def sufficiency_score(self) -> float:
        return self.overall_sufficiency_score

    @property
    def freshness_score(self) -> float:
        return self.freshness_relevance_score

    @property
    def can_support_automated_verdict(self) -> bool:
        return self.evidence_status == EvidenceStatus.SUFFICIENT and not self.mandatory_fields_missing and self.overall_sufficiency_score >= 70.0

    @property
    def is_sufficient(self) -> bool:
        return self.evidence_status == EvidenceStatus.SUFFICIENT and not bool(self.mandatory_fields_missing)

    @property
    def missing_mandatory_fields(self) -> List[str]:
        return self.mandatory_fields_missing

    @property
    def missing_optional_fields(self) -> List[str]:
        return self.unsupported_fields_requested


# --------------------------------------------------------------------------
# 2. Claim-to-Evidence Verification Schemas
# --------------------------------------------------------------------------

class ClaimVerificationItem(BaseModel):
    claim_text: str
    claim_type: ClaimType
    referenced_evidence_ids: List[str] = Field(default_factory=list)
    is_grounded: bool = False
    grounding_status: str = "UNCHECKED"  # GROUNDED, REFERENCE_NOT_FOUND, VALUE_MISMATCH, CONTRADICTED, UNVERIFIABLE
    actual_observed_values: Dict[str, Any] = Field(default_factory=dict)
    contradiction_details: Optional[str] = None
    is_model_assisted: bool = False


class ClaimVerificationResult(BaseModel):
    incident_id: str
    total_claims: int
    grounded_claims: int
    unsupported_claims: int
    contradicted_claims: int
    claims: List[ClaimVerificationItem] = Field(default_factory=list)
    has_unsupported_assertions: bool = False
    has_contradictions: bool = False
    grounding_ratio: float = 0.0
    unsupported_threshold_assertion: bool = False
    unsupported_claims_list: List[str] = Field(default_factory=list)

    @property
    def contradiction_detected(self) -> bool:
        return self.has_contradictions or self.contradicted_claims > 0

    @property
    def fabrication_detected(self) -> bool:
        return self.has_unsupported_assertions or self.unsupported_claims > 0

    @property
    def ungrounded_claims(self) -> List[str]:
        return [c.claim_text for c in self.claims if not c.is_grounded] or self.unsupported_claims_list

    @property
    def ungrounded_claims_count(self) -> int:
        return self.unsupported_claims

    @property
    def grounded_claims_count(self) -> int:
        return self.grounded_claims

    @property
    def contradictions(self) -> List[str]:
        return [c.contradiction_details for c in self.claims if c.contradiction_details]

    @property
    def claims_supported(self) -> bool:
        return not self.has_unsupported_assertions and not self.has_contradictions and (self.grounded_claims > 0 or self.total_claims == 0)


# --------------------------------------------------------------------------
# 3. Verdict Trustworthiness Schemas
# --------------------------------------------------------------------------

class TrustScoreDimensionBreakdown(BaseModel):
    direct_claim_support: float = Field(..., ge=0.0, le=35.0, description="Max 35: Direct claim-to-evidence support")
    source_reliability: float = Field(..., ge=0.0, le=20.0, description="Max 20: Evidence source reliability")
    contradiction_handling: float = Field(..., ge=0.0, le=15.0, description="Max 15: Contradiction and counterevidence handling")
    independent_corroboration: float = Field(..., ge=0.0, le=15.0, description="Max 15: Independent multi-source corroboration")
    historical_validation_support: float = Field(..., ge=0.0, le=15.0, description="Max 15: Historical empirical validation support")
    total_raw_score: float = Field(..., ge=0.0, le=100.0, description="Sum of 5 dimensions (0-100)")

    @property
    def claim_support_score(self) -> float:
        return self.direct_claim_support


class VerdictTrustAssessmentResult(BaseModel):
    incident_id: str
    rule_id: str
    archetype: str
    suggested_verdict: str  # Original LLM recommendation
    effective_verdict: UserVisibleVerdict  # Guardrail-adjusted: TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ANALYST_ATTENTION
    trust_score: Optional[int] = Field(None, ge=1, le=10, description="1-10 ordinal scale or None if NOT_SCORABLE")
    historical_trust_score: Optional[int] = Field(None, ge=1, le=10, description="Original legacy trust score preserved for provenance when capped")
    trust_cap_applied: bool = Field(False, description="True when uncalibrated legacy score was normalized to <= 6/10")
    trust_cap_reason: Optional[str] = Field(None, description="Explanation when historical trust score was capped under uncalibrated rules")
    trust_status: str = Field("CALCULATED", description="CALCULATED or NOT_CALCULABLE")
    calculation_version: str = Field("v2.2.0", description="Trustworthiness evaluation calculation engine version")
    raw_trust_score: float = Field(..., ge=0.0, le=100.0)
    evidence_sufficiency_score: float = Field(..., ge=0.0, le=100.0)
    evidence_status: EvidenceStatus
    score_dimensions: TrustScoreDimensionBreakdown
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    confidence_limitations: List[str] = Field(default_factory=list)
    historical_validation_status: str = "UNCALIBRATED"
    is_calibrated: bool = False
    calibrated_probability: Optional[float] = None
    applicable_policy_version: Optional[int] = None
    applicable_contract_version: Optional[str] = None
    escalation_reason: Optional[str] = None
    human_readable_explanation: str
    model_identifier: str = "default-model"
    is_simulated: bool = False
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    evidence_sufficiency: Optional[EvidenceSufficiencyAssessmentResult] = None
    claim_verification: Optional[ClaimVerificationResult] = None

    @property
    def user_visible_verdict(self) -> UserVisibleVerdict:
        return self.effective_verdict

    @property
    def trust_score_ordinal(self) -> Optional[int]:
        return self.trust_score

    @property
    def ordinal_score(self) -> int:
        return self.trust_score if self.trust_score is not None else 1

    @property
    def raw_score_100(self) -> float:
        return self.raw_trust_score

    @property
    def dimension_breakdown(self) -> TrustScoreDimensionBreakdown:
        return self.score_dimensions

    @property
    def claim_support_score(self) -> float:
        return self.score_dimensions.direct_claim_support

    @property
    def explanations(self) -> List[str]:
        return self.confidence_limitations


# --------------------------------------------------------------------------
# 4. Historical Ground Truth Schemas
# --------------------------------------------------------------------------

class GroundTruthItem(BaseModel):
    incident_id: str
    rule_id: str
    historical_timestamp: Optional[int] = None
    original_analyst_verdict: str
    adjudicated_label: GroundTruthLabel
    provenance: GroundTruthProvenance
    analyst_rationale: Optional[str] = None
    label_reliability: float = 1.0
    contradictory_labels_count: int = 0
    dataset_partition: DatasetPartition = DatasetPartition.LOCKED_TEST
    is_eligible: bool = True


# --------------------------------------------------------------------------
# 5. Empirical Accuracy & Statistical Uncertainty Schemas
# --------------------------------------------------------------------------

class IncidentExclusionRecord(BaseModel):
    incident_id: str
    reason: str  # MISSING_ANALYST_LABEL, AMBIGUOUS_LABEL, CORRUPT_OR_EMPTY_PAYLOAD, RULE_MISMATCH, HEURISTIC_OR_ML_LABEL
    detail: str
    rule_id: Optional[str] = None


class IncidentEligibilityFunnel(BaseModel):
    total_scanned: int = 0
    rule_matched: int = 0
    analyst_labeled: int = 0
    eligible: int = 0
    independent_group_count: int = 0
    excluded: int = 0
    duplicate_excluded_count: int = 0
    synthetic_excluded_count: int = 0
    evaluated: int = 0
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)
    exclusions_detail: List[IncidentExclusionRecord] = Field(default_factory=list)
    stage_details: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)


class WilsonConfidenceInterval(BaseModel):
    point_estimate: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_level: float = 0.95


class RiskCoveragePoint(BaseModel):
    trust_threshold: int  # 1 to 10
    coverage_ratio: float  # fraction of incidents with trust >= threshold
    selective_accuracy: Optional[float] = None
    error_rate: Optional[float] = None
    abstention_count: int
    automatic_count: int


class EmpiricalAccuracyMetrics(BaseModel):
    total_evaluated_incidents: int
    verified_ground_truth_cases: int
    unverified_cases: int
    conflicting_cases: int

    # Ground truth class distribution
    tp_ground_truth_count: int = 0
    fp_ground_truth_count: int = 0

    # Eligibility Funnel
    funnel: Optional[IncidentEligibilityFunnel] = None

    # Confusion matrix on decisive automatic decisions
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    # Abstention metrics
    analyst_attention_count: int
    analyst_attention_rate: Optional[float] = None  # abstentions / verified_ground_truth_cases (None when N=0)
    automatic_decision_count: int
    automatic_decision_coverage: Optional[float] = None  # automatic / verified_ground_truth_cases (None when N=0)

    # Proportions & Wilson 95% CIs
    precision: Optional[float] = None
    precision_ci: Optional[WilsonConfidenceInterval] = None
    recall: Optional[float] = None
    recall_ci: Optional[WilsonConfidenceInterval] = None
    specificity: Optional[float] = None
    specificity_ci: Optional[WilsonConfidenceInterval] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None
    balanced_accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    overall_accuracy: Optional[float] = None
    error_rate_among_automatic: Optional[float] = None
    independent_group_count: Optional[int] = None
    metric_status: Optional[str] = None
    balanced_accuracy_reason: Optional[str] = None

    # Safety indicators
    critical_false_negatives: int = 0
    unsupported_verdicts: int = 0
    evidence_insufficiency_count: int = 0
    low_trust_count: int = 0
    risk_coverage_curve: List[RiskCoveragePoint] = Field(default_factory=list)

    @property
    def verified_ground_truth_count(self) -> int:
        return self.verified_ground_truth_cases

    @property
    def confusion_matrix(self):
        class _CM:
            true_positives = self.true_positives
            false_positives = self.false_positives
            true_negatives = self.true_negatives
            false_negatives = self.false_negatives
        return _CM()


class ReliabilityDiagramBin(BaseModel):
    bin_index: int
    score_range: str
    sample_count: int
    mean_predicted_trust: float
    observed_accuracy: Optional[float] = None
    error_rate: Optional[float] = None


class CalibrationReport(BaseModel):
    is_calibrated: bool
    status: str  # CALIBRATED, NOT_CALIBRATED, INSUFFICIENT_DATA
    calibration_method: Optional[str] = None
    brier_score: Optional[float] = None
    expected_calibration_error: Optional[float] = None
    sample_count: int
    reliability_bins: List[ReliabilityDiagramBin] = Field(default_factory=list)
    calibration_notes: List[str] = Field(default_factory=list)

    @property
    def total_calibrated_samples(self) -> int:
        return self.sample_count


# --------------------------------------------------------------------------
# 6. Historical Simulation & Regression Comparison Schemas
# --------------------------------------------------------------------------

class CaseRegressionDetail(BaseModel):
    incident_id: str
    rule_id: str
    ground_truth: str
    baseline_verdict: str
    candidate_verdict: str
    baseline_trust: Optional[int] = None
    candidate_trust: Optional[int] = None
    regression_type: str  # TP_DROPPED_TO_FN, FP_INTRODUCED, UNNECESSARY_ABSTENTION, IMPROVEMENT
    reason: str


class RegressionComparisonReport(BaseModel):
    rule_id: Optional[str] = None
    baseline_run_id: str
    candidate_run_id: str
    validation_state: EvaluationValidationState
    regression_status: Optional[str] = None  # PASS, REGRESSION_DETECTED, INSUFFICIENT_DATA, NOT_ASSESSED
    sample_count: int
    baseline_accuracy: Optional[float] = None
    candidate_accuracy: Optional[float] = None
    accuracy_delta: Optional[float] = None
    baseline_coverage: float
    candidate_coverage: float
    coverage_delta: float
    baseline_recall: Optional[float] = None
    candidate_recall: Optional[float] = None
    recall_delta: Optional[float] = None
    baseline_specificity: Optional[float] = None
    candidate_specificity: Optional[float] = None
    specificity_delta: Optional[float] = None
    critical_regressions_count: int = 0
    statistically_significant: bool = False
    p_value_estimate: Optional[float] = None
    dataset_hash: Optional[str] = None
    policy_digest: Optional[str] = None
    contract_digest: Optional[str] = None
    regressed_cases: List[CaseRegressionDetail] = Field(default_factory=list)
    improved_cases: List[CaseRegressionDetail] = Field(default_factory=list)
    summary_message: str


# --------------------------------------------------------------------------
# 7. Dashboard API Request & Response Schemas
# --------------------------------------------------------------------------

class IncidentTrustEvaluationRequest(BaseModel):
    incident_id: str
    rule_id: Optional[str] = None
    policy_version_number: Optional[int] = None
    allow_simulation: bool = True
    custom_model_output: Optional[Dict[str, Any]] = None


class HistoricalEvaluationRunRequest(BaseModel):
    run_name: str = "Dry-Run Intelligence Validation"
    rule_id: Optional[str] = None
    archetype: Optional[str] = None
    dataset_filter: Optional[str] = None
    sample_limit: Optional[int] = 100
    policy_version_id: Optional[str] = None
    baseline_run_id: Optional[str] = None
    provider_type: str = "SIMULATED"  # SIMULATED, OPENAI_COMPATIBLE
    split_partition: Optional[DatasetPartition] = None
    after_epoch: Optional[int] = None
    before_epoch: Optional[int] = None
