"""
Empirical Accuracy Evaluator (AIS 2.1).
Computes exact classification metrics, Wilson score confidence intervals,
selective classification risk-coverage curves, and abstention reporting.

Positive Class Definition:
- Positive Class: TRUE_POSITIVE (Confirmed Malicious/Unauthorized Activity)
- Negative Class: FALSE_POSITIVE (Confirmed Benign/Authorized Activity)
- REQUIRES_ANALYST_ATTENTION: Abstention (routes to human review; not a ground-truth label)
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.verdict_intelligence import (
    UserVisibleVerdict,
    GroundTruthLabel,
    EmpiricalAccuracyMetrics,
    WilsonConfidenceInterval,
    RiskCoveragePoint,
    IncidentEligibilityFunnel,
)

logger = logging.getLogger("ai_verdict.empirical_accuracy")


class EmpiricalAccuracyEvaluator:
    """
    Evaluates observed system verdicts against verified ground truth cases.
    Guarantees honest statistical reporting without inflating accuracy by hiding abstentions.
    """

    @classmethod
    def calculate_wilson_ci(cls, successes: int, trials: int, confidence: float = 0.95) -> WilsonConfidenceInterval:
        """
        Computes Wilson score interval for a binomial proportion.
        Handles small sample sizes (N < 30) robustly without degenerate zero bounds.
        """
        if trials <= 0:
            return WilsonConfidenceInterval(point_estimate=None, lower_bound=None, upper_bound=None, confidence_level=confidence)

        p = successes / trials
        z = 1.95996  # 95% two-sided normal quantile

        denominator = 1.0 + (z ** 2) / trials
        center_adj = p + (z ** 2) / (2.0 * trials)
        spread = z * math.sqrt((p * (1.0 - p) + (z ** 2) / (4.0 * trials)) / trials)

        lower = max(0.0, (center_adj - spread) / denominator)
        upper = min(1.0, (center_adj + spread) / denominator)

        return WilsonConfidenceInterval(
            point_estimate=round(p, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            confidence_level=confidence,
        )

    @classmethod
    def evaluate_performance(
        cls,
        evaluations: List[Dict[str, Any]],
        compute_curve: bool = True,
        funnel: Optional[IncidentEligibilityFunnel] = None,
    ) -> EmpiricalAccuracyMetrics:
        """
        Calculates empirical evaluation metrics across evaluated incidents.
        Each item in evaluations must contain:
        - 'effective_verdict': str ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ANALYST_ATTENTION")
        - 'ground_truth_label': Optional[str] ("VERIFIED_TP", "VERIFIED_FP", "UNVERIFIED", "CONFLICTING")
        - 'trust_score': Optional[int] (1 to 10)
        - 'evidence_status': Optional[str]
        """
        total = len(evaluations)
        verified_gt_count = 0
        unverified_count = 0
        conflicting_count = 0
        tp_gt_count = 0
        fp_gt_count = 0

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        analyst_attention = 0
        unsupported_count = 0
        insufficiency_count = 0
        low_trust_count = 0

        for item in evaluations:
            eff_verdict = str(item.get("effective_verdict") or "REQUIRES_ANALYST_ATTENTION").upper().strip()
            gt_label = item.get("ground_truth_label")
            trust = item.get("trust_score")
            ev_status = str(item.get("evidence_status", "")).upper()

            if ev_status in ("INSUFFICIENT", "CONFLICTING"):
                insufficiency_count += 1
            if trust is not None and trust < 7:
                low_trust_count += 1
            if item.get("has_unsupported_assertions"):
                unsupported_count += 1

            if not gt_label:
                continue

            gt_upper = str(gt_label).upper().strip()
            if gt_upper == GroundTruthLabel.UNVERIFIED.value:
                unverified_count += 1
                continue
            elif gt_upper == GroundTruthLabel.CONFLICTING.value:
                conflicting_count += 1
                continue
            elif gt_upper not in (GroundTruthLabel.VERIFIED_TP.value, GroundTruthLabel.VERIFIED_FP.value):
                continue

            verified_gt_count += 1
            if gt_upper == GroundTruthLabel.VERIFIED_TP.value:
                tp_gt_count += 1
            elif gt_upper == GroundTruthLabel.VERIFIED_FP.value:
                fp_gt_count += 1

            # Check if system abstained
            if eff_verdict in ("REQUIRES_ANALYST_ATTENTION", "REQUIRES_ATTENTION", "ABSTAIN"):
                analyst_attention += 1
                continue

            # Decisive automated verdict evaluation
            if gt_upper == GroundTruthLabel.VERIFIED_TP.value:
                if eff_verdict == UserVisibleVerdict.TRUE_POSITIVE.value:
                    tp += 1
                else:
                    fn += 1  # Critical error: missed true positive
            elif gt_upper == GroundTruthLabel.VERIFIED_FP.value:
                if eff_verdict == UserVisibleVerdict.FALSE_POSITIVE.value:
                    tn += 1
                else:
                    fp += 1  # False alarm: benign classified as attack

        auto_decision_count = tp + tn + fp + fn
        auto_coverage = round(auto_decision_count / verified_gt_count, 4) if verified_gt_count > 0 else None
        attention_rate = round(analyst_attention / verified_gt_count, 4) if verified_gt_count > 0 else None

        # Precision (PPV): TP / (TP + FP)
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
        precision_ci = cls.calculate_wilson_ci(tp, tp + fp) if (tp + fp) > 0 else None

        # Recall / Sensitivity: TP / (TP + FN)
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
        recall_ci = cls.calculate_wilson_ci(tp, tp + fn) if (tp + fn) > 0 else None

        # Specificity (TNR): TN / (TN + FP)
        specificity = (tn / (tn + fp)) if (tn + fp) > 0 else None
        specificity_ci = cls.calculate_wilson_ci(tn, tn + fp) if (tn + fp) > 0 else None

        # Error rates
        fpr = (fp / (fp + tn)) if (fp + tn) > 0 else None
        fnr = (fn / (tp + fn)) if (tp + fn) > 0 else None

        # Balanced Accuracy & F1 (requires both TP and FP classes with non-zero decisive denominators)
        if verified_gt_count == 0:
            balanced_accuracy = None
            ba_reason = "NOT_CALCULABLE: Zero verified ground-truth cases (N=0)."
        elif auto_decision_count == 0:
            balanced_accuracy = None
            ba_reason = "NOT_CALCULABLE: Zero decisive automated predictions (all abstained)."
        elif recall is None and specificity is None:
            balanced_accuracy = None
            ba_reason = "NOT_CALCULABLE: Zero decisive TP and FP denominators."
        elif recall is None:
            balanced_accuracy = None
            ba_reason = "NOT_CALCULABLE: Missing True Positive class denominator (TP + FN = 0)."
        elif specificity is None:
            balanced_accuracy = None
            ba_reason = "NOT_CALCULABLE: Missing False Positive class denominator (TN + FP = 0)."
        else:
            balanced_accuracy = (recall + specificity) / 2.0
            ba_reason = "CALCULATED: Two-class denominator verified (TP+FN > 0 and TN+FP > 0)."

        overall_acc = ((tp + tn) / auto_decision_count) if auto_decision_count > 0 else None
        auto_error_rate = ((fp + fn) / auto_decision_count) if auto_decision_count > 0 else None

        metric_status = (
            "CALCULATED"
            if balanced_accuracy is not None
            else ("PARTIAL" if overall_acc is not None else "NOT_CALCULABLE")
        )

        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = 2.0 * (precision * recall) / (precision + recall)
        else:
            f1 = None

        return EmpiricalAccuracyMetrics(
            total_evaluated_incidents=total,
            verified_ground_truth_cases=verified_gt_count,
            unverified_cases=unverified_count,
            conflicting_cases=conflicting_count,
            tp_ground_truth_count=tp_gt_count,
            fp_ground_truth_count=fp_gt_count,
            funnel=funnel,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            analyst_attention_count=analyst_attention,
            analyst_attention_rate=attention_rate,
            automatic_decision_count=auto_decision_count,
            automatic_decision_coverage=auto_coverage,
            precision=round(precision, 4) if precision is not None else None,
            precision_ci=precision_ci,
            recall=round(recall, 4) if recall is not None else None,
            recall_ci=recall_ci,
            specificity=round(specificity, 4) if specificity is not None else None,
            specificity_ci=specificity_ci,
            false_positive_rate=round(fpr, 4) if fpr is not None else None,
            false_negative_rate=round(fnr, 4) if fnr is not None else None,
            balanced_accuracy=round(balanced_accuracy, 4) if balanced_accuracy is not None else None,
            f1_score=round(f1, 4) if f1 is not None else None,
            overall_accuracy=round(overall_acc, 4) if overall_acc is not None else None,
            error_rate_among_automatic=round(auto_error_rate, 4) if auto_error_rate is not None else None,
            metric_status=metric_status,
            balanced_accuracy_reason=ba_reason,
            critical_false_negatives=fn,
            unsupported_verdicts=unsupported_count,
            evidence_insufficiency_count=insufficiency_count,
            low_trust_count=low_trust_count,
            risk_coverage_curve=cls.generate_risk_coverage_curve(evaluations) if compute_curve else [],
        )

    @classmethod
    def generate_risk_coverage_curve(
        cls,
        evaluations: List[Dict[str, Any]],
    ) -> List[RiskCoveragePoint]:
        """
        Generates selective classification risk-coverage points for Trust Score thresholds 1 to 10.
        Demonstrates how error rates decline as confidence / trust thresholds increase.
        """
        points: List[RiskCoveragePoint] = []
        total_evals = len(evaluations)
        if total_evals == 0:
            return points

        for thresh in range(1, 11):
            subset = [
                e for e in evaluations
                if e.get("trust_score") is not None and int(e["trust_score"]) >= thresh
            ]
            covered_count = len(subset)
            coverage = covered_count / total_evals

            # Calculate accuracy on covered subset with verified ground truth without recursing
            sub_metrics = cls.evaluate_performance(subset, compute_curve=False)

            points.append(
                RiskCoveragePoint(
                    trust_threshold=thresh,
                    coverage_ratio=round(coverage, 4),
                    selective_accuracy=sub_metrics.overall_accuracy,
                    error_rate=sub_metrics.error_rate_among_automatic,
                    abstention_count=total_evals - covered_count,
                    automatic_count=covered_count,
                )
            )

        return points
