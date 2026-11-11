import io
import csv
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload

from app.models.dry_run import DryRunJob, DryRunResult
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.schemas.evaluation import (
    EvaluationMetricsResponse,
    ConfusionMatrixData,
    RulePerformanceSummary,
    PromptComparisonItem,
)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


class VerdictEvaluationEngine:
    """
    Verdict Evaluation Engine (formerly EvaluationService).
    Computes evaluation metrics, confusion matrices, accuracy, precision,
    recall, F1-scores, and trust reporting for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_job_metrics(self, job_id: str) -> EvaluationMetricsResponse:
        query = select(DryRunJob).where(DryRunJob.id == job_id).options(
            selectinload(DryRunJob.results).selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
            selectinload(DryRunJob.results).selectinload(DryRunResult.incident).selectinload(Incident.rule),
        )
        res = await self.db.execute(query)
        job = res.scalars().first()
        if not job:
            raise ValueError(f"Dry run job {job_id} not found")

        matrix = ConfusionMatrixData()
        rule_stats: Dict[str, Dict[str, Any]] = {}
        total_latency = 0
        total_items = len(job.results)

        resolved_count = 0
        abstention_count = 0
        error_count = 0

        for r in job.results:
            total_latency += (r.latency_ms or 0)
            if r.validation_status != "VALID":
                error_count += 1

            inc = r.incident
            gt_obj = inc.ground_truth if inc else None
            gt_label = None

            if gt_obj and gt_obj.resolution:
                gt_raw = gt_obj.resolution.lower()
                if "true positive" in gt_raw or "malicious" in gt_raw:
                    gt_label = "TRUE_POSITIVE"
                elif "false positive" in gt_raw or "benign" in gt_raw:
                    gt_label = "FALSE_POSITIVE"

            pred = r.predicted_verdict.upper().strip()
            rule_id = inc.rule_id if (inc and inc.rule_id) else (inc.event_type if inc else "UNKNOWN")
            rule_name = inc.rule.name if (inc and inc.rule) else (inc.event_type if inc else "Unknown Rule")

            if rule_id not in rule_stats:
                rule_stats[rule_id] = {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "total": 0,
                    "tp_agree": 0,
                    "fp_agree": 0,
                    "tp_as_fp": 0,
                    "fp_as_tp": 0,
                    "abstains": 0,
                }

            r_stat = rule_stats[rule_id]
            r_stat["total"] += 1

            if pred == "REQUIRES_ATTENTION":
                abstention_count += 1
                r_stat["abstains"] += 1
                if gt_label == "TRUE_POSITIVE":
                    matrix.true_positive_as_abstain += 1
                elif gt_label == "FALSE_POSITIVE":
                    matrix.false_positive_as_abstain += 1
            elif pred == "TRUE_POSITIVE":
                resolved_count += 1
                if gt_label == "TRUE_POSITIVE":
                    matrix.true_positive_as_tp += 1
                    r_stat["tp_agree"] += 1
                elif gt_label == "FALSE_POSITIVE":
                    matrix.false_positive_as_tp += 1
                    r_stat["fp_as_tp"] += 1
            elif pred == "FALSE_POSITIVE":
                resolved_count += 1
                if gt_label == "FALSE_POSITIVE":
                    matrix.false_positive_as_fp += 1
                    r_stat["fp_agree"] += 1
                elif gt_label == "TRUE_POSITIVE":
                    matrix.true_positive_as_fp += 1
                    r_stat["tp_as_fp"] += 1

        # Calculate mathematical metrics
        # Verdict accuracy on resolved TP/FP predictions
        total_agree = matrix.true_positive_as_tp + matrix.false_positive_as_fp
        verdict_accuracy = _safe_divide(total_agree, resolved_count)

        # TP Precision & Recall
        pred_tp_total = matrix.true_positive_as_tp + matrix.false_positive_as_tp
        actual_tp_total = matrix.true_positive_as_tp + matrix.true_positive_as_fp
        tp_precision = _safe_divide(matrix.true_positive_as_tp, pred_tp_total)
        tp_recall = _safe_divide(matrix.true_positive_as_tp, actual_tp_total)

        # FP Precision & Recall
        pred_fp_total = matrix.false_positive_as_fp + matrix.true_positive_as_fp
        actual_fp_total = matrix.false_positive_as_fp + matrix.false_positive_as_tp
        fp_precision = _safe_divide(matrix.false_positive_as_fp, pred_fp_total)
        fp_recall = _safe_divide(matrix.false_positive_as_fp, actual_fp_total)

        # F1 Score
        if tp_precision + tp_recall > 0:
            f1_score = round(2 * (tp_precision * tp_recall) / (tp_precision + tp_recall), 2)
        else:
            f1_score = 0.0

        # Coverage (percentage of alerts resolved without abstaining)
        coverage = _safe_divide(resolved_count, total_items)
        avg_latency = round(total_latency / total_items, 1) if total_items > 0 else 0.0

        # Per-rule breakdown
        breakdown = []
        for r_id, s in rule_stats.items():
            r_resolved = s["tp_agree"] + s["fp_agree"] + s["tp_as_fp"] + s["fp_as_tp"]
            r_agree = s["tp_agree"] + s["fp_agree"]
            r_acc = _safe_divide(r_agree, r_resolved)
            r_cov = _safe_divide(r_resolved, s["total"])
            breakdown.append({
                "rule_id": s["rule_id"],
                "rule_name": s["rule_name"],
                "total_incidents": s["total"],
                "resolved_count": r_resolved,
                "accuracy": r_acc,
                "coverage": r_cov,
                "tp_agreements": s["tp_agree"],
                "fp_agreements": s["fp_agree"],
            })

        return EvaluationMetricsResponse(
            job_id=job.id,
            job_status=job.status,
            is_simulated=job.is_simulated,
            total_evaluated=total_items,
            resolved_predictions=resolved_count,
            abstention_count=abstention_count,
            error_count=error_count,
            verdict_accuracy=verdict_accuracy,
            tp_precision=tp_precision,
            tp_recall=tp_recall,
            fp_precision=fp_precision,
            fp_recall=fp_recall,
            f1_score=f1_score,
            abstention_coverage=coverage,
            confusion_matrix=matrix,
            rule_breakdown=breakdown,
            average_latency_ms=avg_latency,
            generated_at=utc_now(),
        )

    async def compare_prompt_versions(self, rule_id: str) -> List[PromptComparisonItem]:
        # Resolve target rule by id (UUID), rule_id, or event_type
        rule_query = select(Rule).where(
            or_(
                Rule.id == rule_id,
                Rule.rule_id == rule_id,
                Rule.event_type == rule_id,
            )
        )
        rule_res = await self.db.execute(rule_query)
        rule_obj = rule_res.scalars().first()

        target_rule_id = rule_obj.id if rule_obj else rule_id

        # Get all prompt versions for this rule
        pv_query = (
            select(PromptVersion)
            .join(PromptVersion.prompt)
            .where(
                or_(
                    RulePrompt.rule_id == target_rule_id,
                    RulePrompt.id == target_rule_id,
                )
            )
            .order_by(PromptVersion.version_number.asc())
        )
        pv_res = await self.db.execute(pv_query)
        versions = pv_res.scalars().all()

        from app.models.verdict_intelligence import (
            HistoricalEvaluationRunRecord,
            HistoricalEvaluationResultRecord,
        )
        from app.services.policy_governance import SIMULATED_PROVIDER_TOKENS

        comparisons = []
        for v in versions:
            # 1. Prefer canonical HistoricalEvaluationRunRecord/ResultRecord linked to this policy_version_id
            canon_runs_res = await self.db.execute(
                select(HistoricalEvaluationRunRecord).where(
                    HistoricalEvaluationRunRecord.policy_version_id == str(v.id),
                    HistoricalEvaluationRunRecord.status == "COMPLETED",
                )
            )
            canon_runs = list(canon_runs_res.scalars().all())
            non_sim_runs = [
                r for r in canon_runs
                if not (
                    (r.config_snapshot or {}).get("is_simulated") is True
                    or str((r.config_snapshot or {}).get("provider_type") or "").upper() in SIMULATED_PROVIDER_TOKENS
                )
            ]
            use_runs = non_sim_runs if non_sim_runs else canon_runs
            if use_runs:
                run_ids = [r.id for r in use_runs]
                canon_res_rows = list((await self.db.execute(
                    select(HistoricalEvaluationResultRecord).where(
                        HistoricalEvaluationResultRecord.run_id.in_(run_ids)
                    )
                )).scalars().all())
                c_eval = len(canon_res_rows)
                if c_eval > 0:
                    c_resolved = 0
                    c_agree = 0
                    c_tp_agree = 0
                    c_pred_tp = 0
                    c_fp_agree = 0
                    c_pred_fp = 0
                    for cr in canon_res_rows:
                        pred = str(cr.effective_verdict or "").upper()
                        gt_lbl = str(cr.ground_truth_label or "").upper()
                        gt_tp = gt_lbl == "VERIFIED_TP"
                        gt_fp = gt_lbl == "VERIFIED_FP"
                        if pred == "TRUE_POSITIVE":
                            c_resolved += 1
                            c_pred_tp += 1
                            if gt_tp:
                                c_tp_agree += 1
                                c_agree += 1
                        elif pred == "FALSE_POSITIVE":
                            c_resolved += 1
                            c_pred_fp += 1
                            if gt_fp:
                                c_fp_agree += 1
                                c_agree += 1
                    comparisons.append(
                        PromptComparisonItem(
                            prompt_version_number=v.version_number,
                            prompt_version_id=v.id,
                            is_template_draft=v.is_template_draft,
                            status=v.status,
                            evaluated_cases=c_eval,
                            verdict_accuracy=_safe_divide(c_agree, c_resolved),
                            tp_precision=_safe_divide(c_tp_agree, c_pred_tp),
                            fp_precision=_safe_divide(c_fp_agree, c_pred_fp),
                            coverage=_safe_divide(c_resolved, c_eval),
                            average_latency_ms=0.0,
                        )
                    )
                    continue

            # 2. Fallback to legacy DryRunResult rows tested with this prompt version number
            res_query = (
                select(DryRunResult)
                .where(DryRunResult.prompt_version_number == v.version_number)
                .options(selectinload(DryRunResult.incident).selectinload(Incident.ground_truth))
            )
            res_rows = await self.db.execute(res_query)
            all_results = res_rows.scalars().all()

            if rule_obj:
                results = [
                    r for r in all_results
                    if r.incident and (r.incident.rule_id == rule_obj.id or r.incident.event_type == rule_obj.event_type)
                ]
            else:
                results = all_results

            evaluated = len(results)
            if evaluated == 0:
                comparisons.append(
                    PromptComparisonItem(
                        prompt_version_number=v.version_number,
                        prompt_version_id=v.id,
                        is_template_draft=v.is_template_draft,
                        status=v.status,
                        evaluated_cases=0,
                        verdict_accuracy=0.0,
                        tp_precision=0.0,
                        fp_precision=0.0,
                        coverage=0.0,
                        average_latency_ms=0.0,
                    )
                )
                continue

            resolved = 0
            agree = 0
            tp_agree = 0
            pred_tp = 0
            fp_agree = 0
            pred_fp = 0
            total_latency = 0

            for r in results:
                total_latency += (r.latency_ms or 0)
                gt = ""
                if r.incident and r.incident.ground_truth and r.incident.ground_truth.resolution:
                    gt = r.incident.ground_truth.resolution.lower()
                gt_tp = ("true positive" in gt)
                gt_fp = ("false positive" in gt)

                pred = (r.predicted_verdict or "").upper()
                if pred == "TRUE_POSITIVE":
                    resolved += 1
                    pred_tp += 1
                    if gt_tp:
                        tp_agree += 1
                        agree += 1
                elif pred == "FALSE_POSITIVE":
                    resolved += 1
                    pred_fp += 1
                    if gt_fp:
                        fp_agree += 1
                        agree += 1

            comparisons.append(
                PromptComparisonItem(
                    prompt_version_number=v.version_number,
                    prompt_version_id=v.id,
                    is_template_draft=v.is_template_draft,
                    status=v.status,
                    evaluated_cases=evaluated,
                    verdict_accuracy=_safe_divide(agree, resolved),
                    tp_precision=_safe_divide(tp_agree, pred_tp),
                    fp_precision=_safe_divide(fp_agree, pred_fp),
                    coverage=_safe_divide(resolved, evaluated),
                    average_latency_ms=round(total_latency / evaluated, 1) if evaluated > 0 else 0.0,
                )
            )

        return comparisons

    async def export_job_results_csv(self, job_id: str) -> str:
        query = select(DryRunJob).where(DryRunJob.id == job_id).options(
            selectinload(DryRunJob.results).selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
            selectinload(DryRunJob.results).selectinload(DryRunResult.incident).selectinload(Incident.rule),
        )
        res = await self.db.execute(query)
        job = res.scalars().first()
        if not job:
            raise ValueError("Job not found")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Incident ID",
            "SIEM Rule",
            "Event Type",
            "Severity",
            "Ground Truth Verdict",
            "Predicted Verdict",
            "Agreement",
            "Confidence (%)",
            "Latency (ms)",
            "Model ID",
            "Validation Status",
            "Is Simulated",
            "Reasoning",
        ])

        for r in job.results:
            inc = r.incident
            gt = inc.ground_truth.resolution if (inc and inc.ground_truth) else "Unlabeled"
            rule_name = inc.rule.name if (inc and inc.rule) else (inc.event_type if inc else "")

            # Check agreement
            is_agree = False
            pred = r.predicted_verdict.upper()
            if "true positive" in gt.lower() and pred == "TRUE_POSITIVE":
                is_agree = True
            elif "false positive" in gt.lower() and pred == "FALSE_POSITIVE":
                is_agree = True

            writer.writerow([
                inc.incident_id if inc else r.incident_id,
                rule_name,
                inc.event_type if inc else "",
                inc.severity if inc else "",
                gt,
                r.predicted_verdict,
                "AGREE" if is_agree else ("ABSTAIN" if pred == "REQUIRES_ATTENTION" else "DISAGREE"),
                r.confidence,
                r.latency_ms,
                r.model_identifier,
                r.validation_status,
                r.is_simulated,
                r.reasoning.replace("\n", " "),
            ])

        return output.getvalue()


# Backward compatibility alias
EvaluationService = VerdictEvaluationEngine


