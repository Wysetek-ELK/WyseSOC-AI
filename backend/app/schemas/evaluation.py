from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConfusionMatrixData(BaseModel):
    true_positive_as_tp: int = 0
    true_positive_as_fp: int = 0
    true_positive_as_abstain: int = 0
    false_positive_as_fp: int = 0
    false_positive_as_tp: int = 0
    false_positive_as_abstain: int = 0


class EvaluationMetricsResponse(BaseModel):
    job_id: str
    job_status: str
    is_simulated: bool
    total_evaluated: int
    resolved_predictions: int
    abstention_count: int
    error_count: int

    # Core mathematical metrics (percentages 0.0 - 100.0)
    verdict_accuracy: float
    tp_precision: float
    tp_recall: float
    fp_precision: float
    fp_recall: float
    f1_score: float
    abstention_coverage: float

    # Confusion Matrix
    confusion_matrix: ConfusionMatrixData

    # Performance per rule
    rule_breakdown: List[Dict[str, Any]] = []

    # Latency
    average_latency_ms: float = 0.0
    generated_at: datetime


class RulePerformanceSummary(BaseModel):
    rule_id: str
    rule_name: str
    total_incidents: int
    evaluated_count: int
    verdict_accuracy: float
    tp_precision: float
    tp_recall: float
    fp_precision: float
    fp_recall: float
    coverage: float


class PromptComparisonItem(BaseModel):
    prompt_version_number: int
    prompt_version_id: str
    is_template_draft: bool
    status: str
    evaluated_cases: int
    verdict_accuracy: float
    tp_precision: float
    fp_precision: float
    coverage: float
    average_latency_ms: float


class RuleMaturityResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    event_type: Optional[str] = None
    maturity_status: str  # NOT_TESTED, LEARNING, UNDER_EVALUATION, CANDIDATE_FOR_AUTOMATION, APPROVED_FOR_AUTOMATION
    precision_score: float
    recall_score: float
    f1_score: float
    coverage_score: float
    sample_size: int
    unresolved_evidence_gaps: List[str] = []
    recommendation_explanation: str
    is_admin_approved: bool
    approved_by_username: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: str
    latest_test_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaturityApprovalRequest(BaseModel):
    approval_notes: str = Field(..., min_length=3, max_length=1000)
