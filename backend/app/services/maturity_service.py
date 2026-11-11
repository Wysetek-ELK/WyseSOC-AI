from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.maturity import RuleMaturityEvaluation
from app.models.rule import Rule
from app.models.user import User
from app.models.prompt import RulePrompt
from app.models.dry_run import DryRunResult, DryRunJob
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.verdict_intelligence import (
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.schemas.evaluation import RuleMaturityResponse
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.policy_governance import (
    SIMULATED_PROVIDER_TOKENS,
    assess_policy_runtime_certification,
    resolve_canonical_rule,
)


class RuleMaturityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_evaluation(self, rule_id: str) -> RuleMaturityEvaluation:
        canonical = await resolve_canonical_rule(self.db, rule_id)
        target_id = canonical.id if canonical else rule_id
        query = select(RuleMaturityEvaluation).where(RuleMaturityEvaluation.rule_id == target_id).options(
            selectinload(RuleMaturityEvaluation.rule)
        )
        res = await self.db.execute(query)
        eval_record = res.scalars().first()

        if not eval_record:
            if not canonical:
                raise ValueError(f"Rule {rule_id} not found")

            eval_record = RuleMaturityEvaluation(
                rule_id=canonical.id,
                maturity_status="NOT_TESTED",
                recommendation_explanation="SIEM detection rule ingested. Awaiting canonical AIS policy simulation.",
            )
            self.db.add(eval_record)
            await self.db.commit()
            await self.db.refresh(eval_record)

        return eval_record

    async def _get_runtime_certification_context(self, rule: Optional[Rule]) -> Tuple[bool, Optional[str], str]:
        """Reads authoritative canonical certification + latest run source without mutating state."""
        if not rule:
            return False, "No canonical Rule record found.", "NONE"

        rp_res = await self.db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rp = rp_res.scalars().first()
        active_ver = None
        if rp and rp.versions:
            active_ver = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])

        cert = await assess_policy_runtime_certification(self.db, rule, active_ver)
        runs_res = await self.db.execute(
            select(HistoricalEvaluationRunRecord)
            .where(HistoricalEvaluationRunRecord.rule_id == rule.id)
            .order_by(desc(HistoricalEvaluationRunRecord.started_at))
            .limit(5)
        )
        runs = list(runs_res.scalars().all())
        source = "HISTORICAL_EVALUATION_RUN" if runs else "LEGACY_DRY_RUN"
        note = (
            "AIS G1-G8 empirical non-simulated certification PASSED."
            if cert.autonomous_operation_eligible
            else ("; ".join(cert.blocking_reasons) or "Awaiting empirical non-simulated G8 certification.")
        )
        return bool(cert.autonomous_operation_eligible), note, source

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

            auto_ok, gate_note, eval_src = await self._get_runtime_certification_context(rule)

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
                    evaluation_source=eval_src,
                    autonomous_runtime_eligible=auto_ok,
                    governance_gate_note=gate_note,
                )
            )

        return results

    @staticmethod
    def _is_run_simulated(run_rec: HistoricalEvaluationRunRecord) -> bool:
        cfg = getattr(run_rec, "config_snapshot", None) or {}
        if cfg.get("is_simulated") is True:
            return True
        ptype = str(cfg.get("provider_type") or "").upper().strip()
        prov = str(cfg.get("execution_provenance") or "").upper().strip()
        return bool(ptype in SIMULATED_PROVIDER_TOKENS or prov in SIMULATED_PROVIDER_TOKENS)

    async def update_rule_maturity_from_results(self, rule_id: str) -> RuleMaturityEvaluation:
        """
        Recomputes rule maturity metrics prioritizing authoritative canonical
        HistoricalEvaluationRunRecord / HistoricalEvaluationResultRecord runs
        (real non-simulated runs first, then canonical simulated runs, and falling
        back to legacy DryRunResult rows only when no canonical run exists).
        """
        eval_record = await self.get_or_create_evaluation(rule_id)
        target_rule_id = eval_record.rule_id

        tp_agree = 0
        pred_tp = 0
        actual_tp = 0
        resolved = 0
        sample_size = 0
        evidence_gaps = set()
        used_canonical_real = False
        used_canonical_any = False

        # 1. Authoritative canonical HistoricalEvaluationRunRecord results
        runs_res = await self.db.execute(
            select(HistoricalEvaluationRunRecord)
            .where(
                HistoricalEvaluationRunRecord.rule_id == target_rule_id,
                HistoricalEvaluationRunRecord.status == "COMPLETED",
            )
            .order_by(desc(HistoricalEvaluationRunRecord.completed_at))
        )
        completed_runs = list(runs_res.scalars().all())
        non_sim_runs = [r for r in completed_runs if not self._is_run_simulated(r)]
        selected_runs = non_sim_runs if non_sim_runs else completed_runs

        if selected_runs:
            used_canonical_any = True
            used_canonical_real = bool(non_sim_runs)
            run_ids = [r.id for r in selected_runs]
            res_q = await self.db.execute(
                select(HistoricalEvaluationResultRecord).where(
                    HistoricalEvaluationResultRecord.run_id.in_(run_ids)
                )
            )
            canon_rows = list(res_q.scalars().all())
            for r in canon_rows:
                gt_lbl = str(r.ground_truth_label or "").upper()
                if gt_lbl not in (GroundTruthLabel.VERIFIED_TP.value, GroundTruthLabel.VERIFIED_FP.value):
                    continue
                sample_size += 1
                pred = str(r.effective_verdict or "REQUIRES_ATTENTION").upper().strip()
                gt_is_tp = (gt_lbl == GroundTruthLabel.VERIFIED_TP.value)
                if gt_is_tp:
                    actual_tp += 1
                if pred == "TRUE_POSITIVE":
                    resolved += 1
                    pred_tp += 1
                    if gt_is_tp:
                        tp_agree += 1
                elif pred == "FALSE_POSITIVE":
                    resolved += 1
                if r.escalation_reason:
                    evidence_gaps.add(r.escalation_reason[:80])

        # 2. Legacy DryRunResult fallback ONLY if zero canonical rows exist
        if sample_size == 0 and not used_canonical_any:
            query = (
                select(DryRunResult)
                .join(DryRunResult.incident)
                .where(Incident.rule_id == target_rule_id)
                .options(
                    selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
                )
            )
            res = await self.db.execute(query)
            legacy_results = list(res.scalars().all())

            if not legacy_results:
                eval_record.maturity_status = "NOT_TESTED"
                eval_record.recommendation_explanation = "No dry-run or canonical policy simulation runs executed yet for this detection rule."
                await self.db.commit()
                return eval_record

            inv_map: Dict[str, Investigation] = {}
            leg_inc_ids = [r.incident_id for r in legacy_results if r.incident_id]
            if leg_inc_ids:
                inv_q = await self.db.execute(
                    select(Investigation).where(Investigation.incident_id.in_(leg_inc_ids))
                )
                for inv_row in inv_q.scalars().all():
                    inv_map[inv_row.incident_id] = inv_row

            for r in legacy_results:
                inc_obj = r.incident
                gt_obj = inc_obj.ground_truth if inc_obj else None
                inv_obj = inv_map.get(inc_obj.id) if inc_obj else None
                # Respect disputed / ML exclusions cleanly while staying compatible with minimal test fixtures
                if inv_obj is not None and bool(getattr(inv_obj, "is_disputed", False)):
                    continue
                if gt_obj is not None and bool(getattr(gt_obj, "is_ml_generated", False)):
                    if not (inv_obj is not None and bool(getattr(inv_obj, "is_independently_verified", False))):
                        continue

                pred = str(r.predicted_verdict or "").upper().strip()
                gt_txt = str(gt_obj.resolution or "").lower() if gt_obj else ""
                gt_is_tp = ("true positive" in gt_txt or gt_txt == "verified_tp")
                gt_is_fp = ("false positive" in gt_txt or gt_txt == "verified_fp")

                if r.missing_evidence:
                    for gap in r.missing_evidence:
                        if gap:
                            evidence_gaps.add(gap)

                sample_size += 1
                if gt_is_tp:
                    actual_tp += 1
                if pred == "TRUE_POSITIVE":
                    resolved += 1
                    pred_tp += 1
                    if gt_is_tp:
                        tp_agree += 1
                elif pred == "FALSE_POSITIVE":
                    resolved += 1
                elif not gt_is_tp and not gt_is_fp:
                    pass

        if sample_size == 0:
            eval_record.maturity_status = "NOT_TESTED"
            eval_record.recommendation_explanation = "No eligible ground-truth evaluation samples recorded yet for this rule."
            await self.db.commit()
            return eval_record

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
        eval_record.latest_test_date = utc_now()
        eval_record.updated_at = utc_now()

        prov_tag = (
            "Canonical empirical (real LLM)"
            if used_canonical_real
            else ("Canonical simulated-only" if used_canonical_any else "Legacy dry-run")
        )

        # Conservative state machine
        if eval_record.is_admin_approved:
            if precision < 0.90:
                eval_record.maturity_status = "UNDER_EVALUATION"
                eval_record.is_admin_approved = False
                eval_record.recommendation_explanation = (
                    f"{prov_tag}: Automation approval revoked because precision dropped below 90% ({round(precision*100, 1)}%)."
                )
            else:
                eval_record.maturity_status = "APPROVED_FOR_AUTOMATION"
                eval_record.recommendation_explanation = (
                    f"{prov_tag}: Admin signoff recorded. Runtime autonomous execution remains governed by AIS G1-G8 certification."
                )
        else:
            if precision >= 0.95 and recall >= 0.90 and coverage >= 0.80 and sample_size >= 5:
                eval_record.maturity_status = "CANDIDATE_FOR_AUTOMATION"
                eval_record.recommendation_explanation = (
                    f"{prov_tag}: Candidate for automation — achieved {round(precision*100, 1)}% Precision and "
                    f"{round(recall*100, 1)}% Recall across {sample_size} cases. Awaiting mandatory Administrator & AIS G8 signoff."
                )
            else:
                eval_record.maturity_status = "UNDER_EVALUATION"
                eval_record.recommendation_explanation = (
                    f"{prov_tag}: Under evaluation — Precision ({round(precision*100, 1)}%), Recall ({round(recall*100, 1)}%), "
                    f"or sample size ({sample_size}) below candidate threshold (95% Precision / 90% Recall / N>=5)."
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
        rule = eval_record.rule or await resolve_canonical_rule(self.db, eval_record.rule_id)
        auto_ok, gate_note, _ = await self._get_runtime_certification_context(rule)

        eval_record.maturity_status = "APPROVED_FOR_AUTOMATION"
        eval_record.is_admin_approved = True
        eval_record.approved_by_user_id = user_id
        eval_record.approved_at = utc_now()
        eval_record.approval_notes = approval_notes.strip()
        if auto_ok:
            eval_record.recommendation_explanation = (
                f"Approved for production automation by Administrator (AIS G1-G8 certified). Notes: {approval_notes.strip()}"
            )
        else:
            eval_record.recommendation_explanation = (
                f"Administrator maturity signoff recorded; runtime autonomous closure REMAINS GATED until AIS G1-G8 empirical "
                f"certification passes ({gate_note}). Notes: {approval_notes.strip()}"
            )
        eval_record.updated_at = utc_now()

        await self.db.commit()
        await self.db.refresh(eval_record)
        return eval_record

