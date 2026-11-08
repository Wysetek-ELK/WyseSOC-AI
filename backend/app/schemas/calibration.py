from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DatasetSplitType(str, Enum):
    TRAIN = "TRAIN"
    TUNING = "TUNING"
    CALIBRATION = "CALIBRATION"
    LOCKED_TEST = "LOCKED_TEST"


class CalibrationStatus(str, Enum):
    NOT_CALIBRATED = "NOT_CALIBRATED"
    CALIBRATED = "CALIBRATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvaluationMetrics(BaseModel):
    total_cases: int = 0
    evaluated_cases: int = 0
    ground_truth_available_count: int = 0

    tp_count: int = 0
    tn_count: int = 0
    fp_count: int = 0
    fn_count: int = 0
    abstained_count: int = 0  # Cases where system abstained (REQUIRES_ATTENTION)

    precision: Optional[float] = None
    recall: Optional[float] = None
    false_negative_rate: Optional[float] = None
    abstention_rate: Optional[float] = None
    selective_accuracy: Optional[float] = None
    brier_score: Optional[float] = None
    expected_calibration_error: Optional[float] = None


class RuleCalibrationReport(BaseModel):
    """
    Honest calibration and empirical evaluation report (P3-REQ-07).
    Never fabricates high confidence or claims calibrated status without sufficient independent data.
    """
    rule_id: str
    rule_name: str
    sample_size: int = 0
    min_required_samples: int = 30
    calibration_status: CalibrationStatus = CalibrationStatus.NOT_CALIBRATED
    calibration_method: Optional[str] = None
    raw_confidence_summary: Dict[str, float] = Field(default_factory=dict)
    metrics: EvaluationMetrics = Field(default_factory=EvaluationMetrics)
    honest_assessment_notes: str

