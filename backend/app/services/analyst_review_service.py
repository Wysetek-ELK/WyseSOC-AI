import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.learning import LearningRecord
from app.models.analyst_feedback import AnalystVerdictReview, AnalystReviewAdjudication
from app.services.rule_learning_service import RuleLearningService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.analyst_review")


class AnalystReviewService:
    """
    Orchestrates double-blind and standard human analyst determinations,
    calculates post-submission agreement vs disagreement, and updates verified ground truth.
    """

    @classmethod
    async def get_pending_reviews(
        cls,
        db: AsyncSession,
        customer: str = "DEFAULT",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Retrieves incidents awaiting human analyst review.
        In double-blind mode, the AI verdict is masked from the analyst payload.
        """
        # Query incidents joined with investigations
        query = (
            select(Incident, Investigation)
            .outerjoin(Investigation, Incident.id == Investigation.incident_id)
            .where(Incident.customer == customer)
            .order_by(desc(Incident.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await db.execute(query)
        rows = res.all()

        count_q = select(func.count(Incident.id)).where(Incident.customer == customer)
        # Note: func imported below
        from sqlalchemy import func
        total = (await db.execute(select(func.count(Incident.id)).where(Incident.customer == customer))).scalar() or 0

        items = []
        for inc, inv in rows:
            items.append({
                "incident_id": inc.incident_id,
                "db_id": inc.id,
                "title": inc.title,
                "event_type": inc.event_type,
                "severity": inc.severity,
                "customer": inc.customer,
                "source_ip": inc.source_ip,
                "reporting_device": inc.reporting_device,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "investigation_status": inv.status if inv else "PENDING_REVIEW",
                "analyst_verdict": inv.analyst_verdict if inv else None,
                "is_blind_mode": True,  # AI verdict remains hidden in pending queue
            })
        return total, items

    @classmethod
    async def submit_analyst_review(
        cls,
        db: AsyncSession,
        incident_id: str,
        reviewer_id: str,
        analyst_verdict: str,
        analyst_notes: str = "",
        correction_reason: Optional[str] = None,
        evidence_references: Optional[List[str]] = None,
        blind_mode_active: bool = True,
        customer: str = "DEFAULT",
    ) -> Dict[str, Any]:
        """
        Submits an analyst's independent verdict, reveals the stored AI verdict,
        evaluates agreement/disagreement, updates investigations, and notifies RuleLearningService.
        """
        # 1. Lookup incident
        inc_stmt = select(Incident).where(
            and_(Incident.incident_id == incident_id, Incident.customer == customer)
        )
        inc_res = await db.execute(inc_stmt)
        incident = inc_res.scalar_one_or_none()
        if not incident:
            # Fallback search by internal DB id
            inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
            incident = inc_res.scalar_one_or_none()
            if not incident:
                raise ValueError(f"Incident {incident_id} not found")

        # 2. Extract stored AI verdict
        ai_verdict_data = incident.ai_verdict or {}
        revealed_ai_verdict = ai_verdict_data.get("verdict") or ai_verdict_data.get("effective_verdict")

        # 3. Classify agreement vs disagreement
        comparison_outcome, disagreement_reason = cls._classify_outcome(
            analyst_verdict=analyst_verdict,
            ai_verdict=revealed_ai_verdict
        )

        # 4. Check investigation record or create
        inv_stmt = select(Investigation).where(Investigation.incident_id == incident.id)
        inv_res = await db.execute(inv_stmt)
        investigation = inv_res.scalar_one_or_none()
        if not investigation:
            investigation = Investigation(
                incident_id=incident.id,
                status="REVIEWED",
                analyst_verdict=analyst_verdict,
                verdict_reason=analyst_notes,
                is_independently_verified=True,
            )
            db.add(investigation)
            await db.flush()
        else:
            investigation.status = "REVIEWED"
            investigation.analyst_verdict = analyst_verdict
            investigation.verdict_reason = analyst_notes
            investigation.is_independently_verified = True
            db.add(investigation)

        # 5. Persist immutable AnalystVerdictReview
        review = AnalystVerdictReview(
            incident_id=incident.id,
            investigation_id=investigation.id,
            rule_id=incident.rule_id or incident.event_type,
            customer=customer,
            reviewer_id=reviewer_id,
            analyst_verdict=analyst_verdict,
            analyst_notes=analyst_notes,
            correction_reason=correction_reason,
            evidence_references=evidence_references or [],
            blind_mode_active=blind_mode_active,
            revealed_ai_verdict=revealed_ai_verdict,
            comparison_outcome=comparison_outcome,
            ground_truth_status="VERIFIED",
        )
        db.add(review)
        await db.flush()

        # 6. Create / Update verified LearningRecord
        if incident.rule_id:
            learn_stmt = select(LearningRecord).where(
                and_(
                    LearningRecord.rule_id == incident.rule_id,
                    LearningRecord.incident_id == incident.id
                )
            )
            learn_res = await db.execute(learn_stmt)
            learn_rec = learn_res.scalar_one_or_none()
            if not learn_rec:
                learn_rec = LearningRecord(
                    rule_id=incident.rule_id,
                    incident_id=incident.id,
                    verified_verdict=analyst_verdict,
                    analyst_explanation=analyst_notes,
                    verification_status="VERIFIED",
                    evidence_references=evidence_references or [],
                )
                db.add(learn_rec)
            else:
                learn_rec.verified_verdict = analyst_verdict
                learn_rec.analyst_explanation = analyst_notes
                learn_rec.verification_status = "VERIFIED"
                db.add(learn_rec)

            # 7. Update RuleLearningProfile metrics
            profile = await RuleLearningService.get_or_create_profile(
                db=db,
                rule_id=incident.rule_id,
                customer=customer
            )
            await RuleLearningService.record_analyst_feedback(
                db=db,
                profile_id=profile.id,
                analyst_verdict=analyst_verdict,
                ai_verdict=revealed_ai_verdict,
                comparison_outcome=comparison_outcome
            )

        return {
            "review_id": review.id,
            "incident_id": incident.incident_id,
            "analyst_verdict": analyst_verdict,
            "revealed_ai_verdict": revealed_ai_verdict,
            "comparison_outcome": comparison_outcome,
            "disagreement_reason": disagreement_reason,
            "ground_truth_status": "VERIFIED",
            "reviewed_at": review.created_at.isoformat(),
        }

    @classmethod
    def _classify_outcome(
        cls,
        analyst_verdict: str,
        ai_verdict: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        """Determines agreement outcome classification."""
        if not ai_verdict:
            return "ANALYST_ONLY_INITIAL_BENCHMARK", None

        norm_analyst = analyst_verdict.upper().strip()
        norm_ai = ai_verdict.upper().strip()

        if norm_analyst == norm_ai:
            if norm_analyst == "TRUE_POSITIVE":
                return "AGREEMENT_TP", None
            if norm_analyst == "FALSE_POSITIVE":
                return "AGREEMENT_FP", None
            return "AGREEMENT_REQUIRES_ATTENTION", None

        # Disagreements
        if norm_analyst == "FALSE_POSITIVE" and norm_ai == "TRUE_POSITIVE":
            return "AI_FALSE_ALARM", "Analyst determined incident was benign, overturning AI True Positive."

        if norm_analyst == "TRUE_POSITIVE" and norm_ai == "FALSE_POSITIVE":
            return "CRITICAL_MISSED_TP", "CRITICAL WARNING: AI proposed False Positive on confirmed malicious True Positive."

        if norm_ai == "REQUIRES_ATTENTION":
            return "ANALYST_RESOLVED_ABSTENTION", f"AI safely abstained; analyst confirmed {norm_analyst}."

        return "DISPUTED", f"Analyst ({norm_analyst}) diverged from AI ({norm_ai})."

    @classmethod
    async def adjudicate_review(
        cls,
        db: AsyncSession,
        review_id: str,
        adjudicator_id: str,
        final_verdict: str,
        rationale: str
    ) -> Dict[str, Any]:
        """
        Binding L2 adjudication for disputed reviews.
        """
        rev_stmt = select(AnalystVerdictReview).where(AnalystVerdictReview.id == review_id)
        rev_res = await db.execute(rev_stmt)
        review = rev_res.scalar_one_or_none()
        if not review:
            raise ValueError(f"Review {review_id} not found")

        adjudication = AnalystReviewAdjudication(
            review_id=review.id,
            incident_id=review.incident_id,
            adjudicator_user_id=adjudicator_id,
            final_verdict=final_verdict,
            adjudication_rationale=rationale,
            original_dispute_reason=review.analyst_notes
        )
        db.add(adjudication)

        review.analyst_verdict = final_verdict
        review.ground_truth_status = "ADJUDICATED"
        db.add(review)
        await db.flush()

        return {
            "adjudication_id": adjudication.id,
            "review_id": review.id,
            "final_verdict": final_verdict,
            "adjudicator": adjudicator_id,
            "adjudicated_at": adjudication.created_at.isoformat()
        }

