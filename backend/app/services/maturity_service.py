from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.maturity import RuleMaturityEvaluation
from app.models.rule import Rule
from app.models.user import User
from app.models.dry_run import DryRunResult, DryRunJob
from app.models.incident import Incident, HistoricalGroundTruth
from app.schemas.evaluation import RuleMaturityResponse


class RuleMaturityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_evaluation(self, rule_id: str) -> RuleMaturityEvaluation:
        query = select(RuleMaturityEvaluation).where(RuleMaturityEvaluation.rule_id == rule_id).options(
            selectinload(RuleMaturityEvaluation.rule)
        )
        res = await self.db.execute(query)
        eval_record = res.scalars().first()

        if not eval_record:
            rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
            rule = rule_res.scalars().first()
            if not rule:
                raise ValueError(f"Rule {rule_id} not found")

            eval_record = RuleMaturityEvaluation(
                rule_id=rule.id,
                maturity_status="NOT_TESTED",
                recommendation_explanation="SIEM detection rule ingested. Awaiting baseline dry-run replay test execution.",
            )
            self.db.add(eval_record)
            await self.db.commit()
            await self.db.refresh(eval_record)

        return eval_record

    async def list_all_evaluations(self) -> List[RuleMaturityResponse]:
        # Ensure evaluations exist for all ingested rules
        rules_res = await self.db.execute(select(Rule))
        all_rules = rules_res.scalars().all()
        for r in all_rules:
            await self.get_or_create_evaluation(r.id)

        query = select(RuleMaturityEvaluation).options(
            selectinload(RuleMaturityEvaluation.rule)
        ).order_by(RuleMaturityEvaluation.maturity_status.asc())
        res = await self.db.execute(query)
        evals = res.scalars().all()

        results = []
        for e in evals:
            rule = e.rule
            user_res = None
            if e.approved_by_user_id:
                u_res = await self.db.execute(select(User).where(User.id == e.approved_by_user_id))
                user_res = u_res.scalars().first()

            results.append(
                RuleMaturityResponse(
                    id=e.id,
                    rule_id=e.rule_id,
                    rule_name=rule.name if rule else None,
                    event_type=rule.event_type if rule else None,
                    maturity_status=e.maturity_status,
                    precision_score=round(e.precision_score * 100.0, 1),
                    recall_score=round(e.recall_score * 100.0, 1),
                    f1_score=round(e.f1_score * 100.0, 1),
                    coverage_score=round(e.coverage_score * 100.0, 1),
                    sample_size=e.sample_size,
                    unresolved_evidence_gaps=e.unresolved_evidence_gaps or [],
                    recommendation_explanation=e.recommendation_explanation,
                    is_admin_approved=e.is_admin_approved,
                    approved_by_username=user_res.username if user_res else None,
                    approved_at=e.approved_at,
                    approval_notes=e.approval_notes,
                    latest_test_date=e.latest_test_date,
                )
            )

        return results

    async def update_rule_maturity_from_results(self, rule_id: str) -> RuleMaturityEvaluation:
        eval_record = await self.get_or_create_evaluation(rule_id)

        # Query all dry-run results tested for incidents belonging to this rule
        query = select(DryRunResult).join(DryRunResult.incident).where(
            Incident.rule_id == rule_id
        ).options(
            selectinload(DryRunResult.incident).selectinload(Incident.ground_truth)
        )
        res = await self.db.execute(query)
        results = res.scalars().all()

        if not results:
            eval_record.maturity_status = "NOT_TESTED"
            eval_record.recommendation_explanation = "No dry-run replay test runs executed yet for this detection rule."
            await self.db.commit()
            return eval_record

        # Calculate metrics
        tp_agree = 0
        fp_agree = 0
        pred_tp = 0
        actual_tp = 0
        resolved = 0
        evidence_gaps = set()

        for r in results:
            pred = r.predicted_verdict.upper()
            gt = r.incident.ground_truth.resolution.lower() if (r.incident and r.incident.ground_truth) else ""
            gt_is_tp = ("true positive" in gt)
            gt_is_fp = ("false positive" in gt)

            if r.missing_evidence:
                for gap in r.missing_evidence:
                    if gap:
                        evidence_gaps.add(gap)

            if gt_is_tp:
                actual_tp += 1

            if pred == "TRUE_POSITIVE":
                resolved += 1
                pred_tp += 1
                if gt_is_tp:
                    tp_agree += 1
            elif pred == "FALSE_POSITIVE":
                resolved += 1
                if gt_is_fp:
                    fp_agree += 1

        sample_size = len(results)
        precision = (tp_agree / pred_tp) if pred_tp > 0 else 0.0
        recall = (tp_agree / actual_tp) if actual_tp > 0 else 0.0
        coverage = (resolved / sample_size) if sample_size > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        eval_record.precision_score = precision
        eval_record.recall_score = recall
        eval_record.coverage_score = coverage
        eval_record.f1_score = f1
        eval_record.sample_size = sample_size
        eval_record.unresolved_evidence_gaps = list(evidence_gaps)[:5]
        eval_record.latest_test_date = datetime.utcnow()
        eval_record.updated_at = datetime.utcnow()

        # Conservative state machine:
        # If already approved by admin, preserve state unless precision dropped severely
        if eval_record.is_admin_approved:
            if precision < 0.90:
                eval_record.maturity_status = "UNDER_EVALUATION"
                eval_record.is_admin_approved = False
                eval_record.recommendation_explanation = "Automation approval revoked: Precision dropped below 90% in recent dry-run test."
            else:
                eval_record.maturity_status = "APPROVED_FOR_AUTOMATION"
                eval_record.recommendation_explanation = "Production automation active. Approved by SOC Administration."
        else:
            # Check Candidate thresholds: Precision >= 95%, Recall >= 90%, Coverage >= 80%, N >= 5
            if precision >= 0.95 and recall >= 0.90 and coverage >= 0.80 and sample_size >= 5:
                eval_record.maturity_status = "CANDIDATE_FOR_AUTOMATION"
                eval_record.recommendation_explanation = (
                    f"Candidate for automation: Achieved {round(precision*100, 1)}% Precision and "
                    f"{round(recall*100, 1)}% Recall across {sample_size} cases. Awaiting mandatory Administrator approval."
                )
            else:
                eval_record.maturity_status = "UNDER_EVALUATION"
                eval_record.recommendation_explanation = (
                    f"Under evaluation: Precision ({round(precision*100, 1)}%) or Recall ({round(recall*100, 1)}%) "
                    "below automation threshold (95% Precision / 90% Recall required)."
                )

        await self.db.commit()
        await self.db.refresh(eval_record)
        return eval_record

    async def approve_rule_for_automation(
        self,
        rule_id: str,
        user_id: str,
        approval_notes: str
    ) -> RuleMaturityEvaluation:
        eval_record = await self.get_or_create_evaluation(rule_id)

        eval_record.maturity_status = "APPROVED_FOR_AUTOMATION"
        eval_record.is_admin_approved = True
        eval_record.approved_by_user_id = user_id
        eval_record.approved_at = datetime.utcnow()
        eval_record.approval_notes = approval_notes.strip()
        eval_record.recommendation_explanation = (
            f"Approved for production automation by Administrator. Notes: {approval_notes.strip()}"
        )
        eval_record.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(eval_record)
        return eval_record

