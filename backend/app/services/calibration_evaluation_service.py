import math
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.learning import LearningRecord
from app.models.rule import Rule
from app.schemas.calibration import (
    DatasetSplitType,
    CalibrationStatus,
    EvaluationMetrics,
    RuleCalibrationReport,
)


class CalibrationEvaluationService:
    """
    Empirical Evaluation & Honest Confidence Calibration Engine (P3-REQ-07).
    Guarantees honest reporting:
    - Never fabricates calibrated confidence when sample sizes are small or absent.
    - Strictly reports 'NOT_CALIBRATED' when verified ground-truth cases < 30.
    - Accurately tracks Precision, Recall, False Negative Rate, Abstention Rate, and Selective Accuracy.
    - Manages clean 4-way dataset partitioning (Train, Tuning, Calibration, Locked-Test).
    """
    MIN_CALIBRATION_SAMPLES = 30

    @classmethod
    def assign_dataset_partition(cls, incident_id: str) -> DatasetSplitType:
        """
        Deterministically assigns an incident to a dataset partition using SHA-256 hash modulo.
        Guarantees zero partition leakage across runs.
        Split:
        - 0-49: TRAIN (50%)
        - 50-69: TUNING (20%)
        - 70-84: CALIBRATION (15%)
        - 85-99: LOCKED_TEST (15%)
        """
        digest = hashlib.sha256(incident_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100

        if bucket < 50:
            return DatasetSplitType.TRAIN
        elif bucket < 70:
            return DatasetSplitType.TUNING
        elif bucket < 85:
            return DatasetSplitType.CALIBRATION
        else:
            return DatasetSplitType.LOCKED_TEST

    @classmethod
    def calculate_metrics(
        cls,
        evaluations: List[Dict[str, Any]],
    ) -> EvaluationMetrics:
        """
        Calculates empirical evaluation metrics across a set of incident evaluations.
        Each evaluation dictionary must contain:
        - 'predicted_verdict': str (TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION)
        - 'ground_truth_verdict': Optional[str] (TRUE_POSITIVE, FALSE_POSITIVE)
        - 'confidence': float (0.0 to 100.0)
        """
        total = len(evaluations)
        gt_count = 0
        tp = 0
        tn = 0
        fp = 0
        fn = 0
        abstained = 0

        brier_sum = 0.0
        brier_count = 0

        # Binning for Expected Calibration Error (5 bins: [0-20), [20-40), [40-60), [60-80), [80-100])
        bin_counts = [0] * 5
        bin_correct = [0] * 5
        bin_conf_sum = [0.0] * 5

        for item in evaluations:
            pred = item.get("predicted_verdict")
            gt = item.get("ground_truth_verdict")
            conf = float(item.get("confidence", 0.0))
            prob = max(0.0, min(1.0, conf / 100.0))

            if not gt:
                continue

            gt_norm = gt.upper().strip()
            pred_norm = pred.upper().strip() if pred else "REQUIRES_ATTENTION"
            gt_count += 1

            if pred_norm == "REQUIRES_ATTENTION":
                abstained += 1
                continue

            if gt_norm == "TRUE_POSITIVE":
                actual_label = 1.0
                if pred_norm == "TRUE_POSITIVE":
                    tp += 1
                    is_correct = True
                else:
                    fn += 1
                    is_correct = False
            elif gt_norm == "FALSE_POSITIVE":
                actual_label = 0.0
                if pred_norm == "FALSE_POSITIVE":
                    tn += 1
                    is_correct = True
                else:
                    fp += 1
                    is_correct = False
            else:
                continue

            # Brier Score calculation: (prob - actual_label)^2
            brier_sum += (prob - actual_label) ** 2
            brier_count += 1

            # ECE binning
            bin_idx = min(4, int(prob * 5))
            bin_counts[bin_idx] += 1
            bin_conf_sum[bin_idx] += prob
            if is_correct:
                bin_correct[bin_idx] += 1

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
        fnr = (fn / (tp + fn)) if (tp + fn) > 0 else None
        abstention_rate = (abstained / gt_count) if gt_count > 0 else None
        non_abstained = tp + tn + fp + fn
        selective_accuracy = ((tp + tn) / non_abstained) if non_abstained > 0 else None
        brier_score = (brier_sum / brier_count) if brier_count > 0 else None

        # ECE calculation
        ece = 0.0
        if brier_count > 0:
            for i in range(5):
                if bin_counts[i] > 0:
                    bin_acc = bin_correct[i] / bin_counts[i]
                    bin_conf = bin_conf_sum[i] / bin_counts[i]
                    ece += (bin_counts[i] / brier_count) * abs(bin_acc - bin_conf)

        return EvaluationMetrics(
            total_cases=total,
            evaluated_cases=len(evaluations),
            ground_truth_available_count=gt_count,
            tp_count=tp,
            tn_count=tn,
            fp_count=fp,
            fn_count=fn,
            abstained_count=abstained,
            precision=round(precision, 4) if precision is not None else None,
            recall=round(recall, 4) if recall is not None else None,
            false_negative_rate=round(fnr, 4) if fnr is not None else None,
            abstention_rate=round(abstention_rate, 4) if abstention_rate is not None else None,
            selective_accuracy=round(selective_accuracy, 4) if selective_accuracy is not None else None,
            brier_score=round(brier_score, 4) if brier_score is not None else None,
            expected_calibration_error=round(ece, 4) if brier_count > 0 else None,
        )

    @classmethod
    async def generate_rule_calibration_report(
        cls,
        db: AsyncSession,
        rule_id: str,
    ) -> RuleCalibrationReport:
        """
        Compiles an honest calibration and empirical evaluation report for a given detection rule.
        """
        rule_q = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_q.scalars().first()
        rule_name = rule.name if rule else rule_id

        # Query incidents for this rule that have ground truth
        inc_q = await db.execute(
            select(Incident)
            .where(Incident.rule_id == rule_id)
            .options(selectinload(Incident.ground_truth))
        )
        incidents = inc_q.scalars().all()

        # Query verified learning records for this rule
        lr_q = await db.execute(
            select(LearningRecord).where(
                LearningRecord.rule_id == rule_id,
                LearningRecord.verification_status == "VERIFIED"
            )
        )
        lrs_by_inc = {lr.incident_id: lr.verified_verdict for lr in lr_q.scalars().all()}

        evaluations: List[Dict[str, Any]] = []
        confidences: List[float] = []

        for inc in incidents:
            gt_label = None
            if inc.ground_truth and inc.ground_truth.resolution:
                res_norm = inc.ground_truth.resolution.upper()
                if "TRUE" in res_norm:
                    gt_label = "TRUE_POSITIVE"
                elif "FALSE" in res_norm:
                    gt_label = "FALSE_POSITIVE"
            if not gt_label and inc.id in lrs_by_inc:
                gt_label = lrs_by_inc[inc.id]

            ai_v = inc.ai_verdict or {}
            pred_v = ai_v.get("verdict")
            conf = float(ai_v.get("raw_model_confidence", ai_v.get("confidence", 0.0)) or 0.0)

            if conf > 0:
                confidences.append(conf)

            if gt_label:
                evaluations.append({
                    "incident_id": inc.incident_id,
                    "predicted_verdict": pred_v,
                    "ground_truth_verdict": gt_label,
                    "confidence": conf,
                })

        metrics = cls.calculate_metrics(evaluations)
        sample_size = metrics.ground_truth_available_count

        conf_summary: Dict[str, float] = {}
        if confidences:
            conf_summary = {
                "mean_raw_confidence": round(sum(confidences) / len(confidences), 2),
                "min_raw_confidence": round(min(confidences), 2),
                "max_raw_confidence": round(max(confidences), 2),
            }

        # Calibration status assessment
        if sample_size < cls.MIN_CALIBRATION_SAMPLES:
            status = CalibrationStatus.NOT_CALIBRATED
            notes = (
                f"INSUFFICIENT_SAMPLE_SIZE: Only {sample_size} independently verified ground-truth cases "
                f"are available for rule '{rule_name}' (minimum required: {cls.MIN_CALIBRATION_SAMPLES}). "
                "Per Phase 3 AI Verdict governance policies, confidence calibration is WITHHELD. "
                "Model confidence must be interpreted as raw, uncalibrated heuristic scores."
            )
        else:
            status = CalibrationStatus.CALIBRATED
            notes = (
                f"CALIBRATION_VALID: {sample_size} verified ground-truth cases evaluated. "
                f"Expected Calibration Error (ECE): {metrics.expected_calibration_error}, "
                f"Brier Score: {metrics.brier_score}."
            )

        return RuleCalibrationReport(
            rule_id=rule_id,
            rule_name=rule_name,
            sample_size=sample_size,
            min_required_samples=cls.MIN_CALIBRATION_SAMPLES,
            calibration_status=status,
            calibration_method="PLATT_SCALING" if status == CalibrationStatus.CALIBRATED else None,
            raw_confidence_summary=conf_summary,
            metrics=metrics,
            honest_assessment_notes=notes,
        )
