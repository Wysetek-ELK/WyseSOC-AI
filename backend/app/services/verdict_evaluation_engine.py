"""
Verdict Evaluation Engine Module.
Computes evaluation metrics, confusion matrices, accuracy, precision, recall, and trust reporting.
"""
from app.services.evaluation_service import (
    VerdictEvaluationEngine,
    EvaluationService,
)

__all__ = ["VerdictEvaluationEngine", "EvaluationService"]

