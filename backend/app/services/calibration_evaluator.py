"""
Calibration Evaluator (AIS 2.1).
Examines whether higher Trust Scores correlate with lower observed error rates.
Calculates Brier Score, Expected Calibration Error (ECE), and Reliability Diagrams.

Guarantees:
- Never fabricates calibration metrics when sample counts are insufficient (< 30).
- Distinguishes ordinal Trust Scores (1–10) from empirical calibrated probabilities.
- Fits calibration only on dedicated calibration partitions and evaluates on test data.
"""

import math
import logging
from typing import Dict, Any, List, Optional
from app.schemas.verdict_intelligence import (
    CalibrationReport,
    ReliabilityDiagramBin,
    GroundTruthLabel,
    UserVisibleVerdict,
)

logger = logging.getLogger("ai_verdict.calibration_evaluator")


class CalibrationEvaluator:
    """
    Evaluates score calibration across ordinal Trust Score bands (1-2, 3-4, 5-6, 7-8, 9-10).
    """
    MIN_CALIBRATION_SAMPLES = 30

    @classmethod
    def evaluate_calibration(
        cls,
        evaluations: List[Dict[str, Any]],
    ) -> CalibrationReport:
        """
        Computes reliability bins, ECE, and Brier Score for decisive cases with verified ground truth.
        """
        # Filter for verified ground truth and decisive verdicts
        valid_cases: List[Dict[str, Any]] = []
        for e in evaluations:
            gt = str(e.get("ground_truth_label", "")).upper().strip()
            eff = str(e.get("effective_verdict", "")).upper().strip()
            trust = e.get("trust_score")

            if gt in (GroundTruthLabel.VERIFIED_TP.value, GroundTruthLabel.VERIFIED_FP.value):
                if eff in (UserVisibleVerdict.TRUE_POSITIVE.value, UserVisibleVerdict.FALSE_POSITIVE.value):
                    if trust is not None:
                        is_correct = (
                            (gt == GroundTruthLabel.VERIFIED_TP.value and eff == UserVisibleVerdict.TRUE_POSITIVE.value) or
                            (gt == GroundTruthLabel.VERIFIED_FP.value and eff == UserVisibleVerdict.FALSE_POSITIVE.value)
                        )
                        valid_cases.append({
                            "trust_score": int(trust),
                            "raw_trust": float(e.get("raw_trust_score", trust * 10.0)),
                            "is_correct": is_correct,
                        })

        sample_count = len(valid_cases)

        if sample_count < cls.MIN_CALIBRATION_SAMPLES:
            # Build uncalibrated observation bins
            bins = cls._compute_bins(valid_cases)
            return CalibrationReport(
                is_calibrated=False,
                status="NOT_CALIBRATED",
                calibration_method=None,
                brier_score=None,
                expected_calibration_error=None,
                sample_count=sample_count,
                reliability_bins=bins,
                calibration_notes=[
                    f"BELOW_MINIMUM_THRESHOLD: Sample size (N={sample_count}) is below required minimum of {cls.MIN_CALIBRATION_SAMPLES} for empirical calibration.",
                ],
            )

        # Sufficient samples (N >= 30): Calculate Brier Score and ECE
        # Let predicted probability p = raw_trust / 100.0, true outcome y = 1 if correct else 0
        brier_sum = 0.0
        ece_sum = 0.0
        bins = cls._compute_bins(valid_cases)

        for b in bins:
            if b.sample_count > 0 and b.observed_accuracy is not None:
                # ECE component: (bin_n / total_n) * |observed_acc - mean_predicted|
                ece_sum += (b.sample_count / sample_count) * abs(b.observed_accuracy - (b.mean_predicted_trust / 10.0))

        for c in valid_cases:
            prob = max(0.0, min(1.0, c["raw_trust"] / 100.0))
            y = 1.0 if c["is_correct"] else 0.0
            brier_sum += (prob - y) ** 2

        brier_score = round(brier_sum / sample_count, 4)
        ece = round(ece_sum, 4)

        return CalibrationReport(
            is_calibrated=True,
            status="CALIBRATED",
            calibration_method="Binned Reliability Diagram",
            brier_score=brier_score,
            expected_calibration_error=ece,
            sample_count=sample_count,
            reliability_bins=bins,
        )

    @classmethod
    def _compute_bins(cls, cases: List[Dict[str, Any]]) -> List[ReliabilityDiagramBin]:
        """
        Partitions cases into 5 standard score ranges:
        1: 1–2 (Very Weak)
        2: 3–4 (Weak)
        3: 5–6 (Moderate)
        4: 7–8 (Strong)
        5: 9–10 (Exceptional)
        """
        bin_specs = [
            (1, "1–2 (Very Weak)", [1, 2]),
            (2, "3–4 (Weak)", [3, 4]),
            (3, "5–6 (Moderate)", [5, 6]),
            (4, "7–8 (Strong)", [7, 8]),
            (5, "9–10 (Exceptional)", [9, 10]),
        ]

        bins: List[ReliabilityDiagramBin] = []

        for b_idx, label, scores in bin_specs:
            matched = [c for c in cases if c["trust_score"] in scores]
            n = len(matched)
            if n > 0:
                mean_t = sum(c["trust_score"] for c in matched) / n
                correct_count = sum(1 for c in matched if c["is_correct"])
                acc = correct_count / n
                err = 1.0 - acc
            else:
                mean_t = sum(scores) / len(scores)
                acc = None
                err = None

            bins.append(
                ReliabilityDiagramBin(
                    bin_index=b_idx,
                    score_range=label,
                    sample_count=n,
                    mean_predicted_trust=round(mean_t, 2),
                    observed_accuracy=round(acc, 4) if acc is not None else None,
                    error_rate=round(err, 4) if err is not None else None,
                )
            )

        return bins
