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
    async def _resolve_rule_aliases(cls, db: AsyncSession, rule_ref: Optional[str]) -> Tuple[Optional[str], List[str]]:
        """Resolves a rule UUID, rule_id, or event_type into (canonical_uuid, all_matching_tokens)."""
        if not rule_ref or not str(rule_ref).strip():
            return None, []
        from sqlalchemy import or_
        from app.models.rule import Rule

        clean = str(rule_ref).strip()
        stmt = select(Rule).where(
            or_(Rule.id == clean, Rule.rule_id == clean, Rule.event_type == clean)
        )
        rule_obj = (await db.execute(stmt)).scalars().first()
        if not rule_obj:
            return None, [clean]
        tokens = list({t for t in (clean, rule_obj.id, rule_obj.rule_id, rule_obj.event_type) if t})
        return rule_obj.id, tokens

    @classmethod
    async def get_pending_reviews(
        cls,
        db: AsyncSession,
        customer: Optional[str] = None,
        rule_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        reviewer_id: Optional[str] = None,
        include_reviewed: bool = False,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Retrieves incidents awaiting human analyst review.
        In double-blind mode, all AI verdict fields are strictly excluded from the payload.
        Resolves rule UUID/event_type aliases and filters out already-reviewed incidents by default.
        """
        from sqlalchemy import func, or_, not_, exists
        from sqlalchemy.orm import selectinload
        from app.services.evidence_normalization_service import SRC_IP_RE, DST_PORT_RE

        query = (
            select(Incident, Investigation)
            .outerjoin(Investigation, Incident.id == Investigation.incident_id)
            .options(selectinload(Incident.events))
        )
        count_q = (
            select(func.count(Incident.id))
            .outerjoin(Investigation, Incident.id == Investigation.incident_id)
        )

        if customer and customer.upper() not in ("ALL", "GLOBAL"):
            if customer == "DEFAULT":
                query = query.where(or_(Incident.customer == "DEFAULT", Incident.customer == "", Incident.customer.is_(None)))
                count_q = count_q.where(or_(Incident.customer == "DEFAULT", Incident.customer == "", Incident.customer.is_(None)))
            else:
                query = query.where(Incident.customer == customer)
                count_q = count_q.where(Incident.customer == customer)

        if rule_id:
            _, rule_tokens = await cls._resolve_rule_aliases(db, rule_id)
            rule_filter = or_(Incident.rule_id.in_(rule_tokens), Incident.event_type.in_(rule_tokens))
            query = query.where(rule_filter)
            count_q = count_q.where(rule_filter)

        if not include_reviewed:
            if reviewer_id:
                reviewed_exists = exists().where(
                    and_(
                        AnalystVerdictReview.incident_id == Incident.id,
                        AnalystVerdictReview.reviewer_id == str(reviewer_id),
                    )
                )
            else:
                reviewed_exists = exists().where(AnalystVerdictReview.incident_id == Incident.id)
            query = query.where(not_(reviewed_exists))
            count_q = count_q.where(not_(reviewed_exists))

        query = query.order_by(desc(Incident.created_at)).limit(limit).offset(offset)
        res = await db.execute(query)
        rows = res.all()
        total = (await db.execute(count_q)).scalar() or 0

        items = []
        for inc, inv in rows:
            raw_p = inc.raw_payload if isinstance(inc.raw_payload, dict) else {}
            src_ip = (inc.source_ip or "").strip()
            if not src_ip and raw_p.get("incidentSrc"):
                m_src = SRC_IP_RE.search(str(raw_p.get("incidentSrc")))
                src_ip = m_src.group(1).strip() if m_src else str(raw_p.get("incidentSrc")).strip()

            dest_port = ""
            if raw_p.get("incidentTarget"):
                m_pt = DST_PORT_RE.search(str(raw_p.get("incidentTarget")))
                dest_port = m_pt.group(1).strip() if m_pt else ""

            rpt_dev = (inc.reporting_device or raw_p.get("incidentRptDevName") or raw_p.get("incidentRptIp") or "").strip()
            inc_detail = str(raw_p.get("incidentDetail") or inc.detail or "").strip()
            evts = getattr(inc, "events", None) or []

            items.append({
                "incident_id": inc.incident_id,
                "db_id": inc.id,
                "rule_id": inc.rule_id or inc.event_type,
                "title": inc.title,
                "event_type": inc.event_type,
                "severity": inc.severity,
                "customer": inc.customer,
                "source_ip": src_ip,
                "destination_port": dest_port,
                "incident_detail": inc_detail,
                "reporting_device": rpt_dev,
                "raw_events_count": len(evts),
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "investigation_status": inv.status if inv else "PENDING_REVIEW",
                "analyst_verdict": inv.analyst_verdict if inv else None,
                "is_disputed": bool(getattr(inv, "is_disputed", False)) if inv else False,
                "is_blind_mode": True,  # AI verdict, confidence, and rationale strictly excluded
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
        customer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submits an analyst's independent verdict, reveals the stored AI verdict,
        evaluates agreement/disagreement, updates investigations, and notifies RuleLearningService.
        """
        from sqlalchemy import or_, cast, String
        # 1. Lookup incident by id or incident_id (both string and integer)
        inc_stmt = select(Incident).where(
            or_(
                Incident.id == incident_id,
                cast(Incident.incident_id, String) == str(incident_id)
            )
        )
        if customer and customer.upper() not in ("ALL", "GLOBAL"):
            if customer == "DEFAULT":
                inc_stmt = inc_stmt.where(
                    or_(
                        Incident.customer == "DEFAULT",
                        Incident.customer == "",
                        Incident.customer.is_(None)
                    )
                )
            else:
                inc_stmt = inc_stmt.where(Incident.customer == customer)

        inc_res = await db.execute(inc_stmt)
        incident = inc_res.scalars().first()
        if not incident:
            # Check if incident exists in another customer tenant to reject cross-tenant reviews
            other_stmt = select(Incident).where(
                or_(
                    Incident.id == incident_id,
                    cast(Incident.incident_id, String) == str(incident_id)
                )
            )
            other_inc = (await db.execute(other_stmt)).scalars().first()
            if other_inc:
                raise ValueError(
                    f"Access denied: Incident {incident_id} belongs to customer '{other_inc.customer}', but user is restricted to '{customer}'."
                )
            raise ValueError(f"Incident {incident_id} not found")

        effective_customer = incident.customer or customer or "DEFAULT"

        # 2. Extract stored AI verdict and validate analyst verdict
        norm_verdict = analyst_verdict.upper().strip()
        if norm_verdict == "INCONCLUSIVE":
            norm_verdict = "INSUFFICIENT_EVIDENCE"
        if norm_verdict not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "INSUFFICIENT_EVIDENCE"):
            raise ValueError(
                f"Invalid analyst verdict '{analyst_verdict}'. Allowed values are strictly: TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE, INCONCLUSIVE. "
                "Derived outcomes (e.g. AGREEMENT_TP, AI_FALSE_ALARM) are computed post-submission."
            )

        ai_verdict_data = incident.ai_verdict or {}
        revealed_ai_verdict = ai_verdict_data.get("verdict") or ai_verdict_data.get("effective_verdict")

        # 3. Classify agreement vs disagreement
        comparison_outcome, disagreement_reason = cls._classify_outcome(
            analyst_verdict=analyst_verdict,
            ai_verdict=revealed_ai_verdict
        )

        ground_truth_status = "INSUFFICIENT_EVIDENCE" if analyst_verdict == "INSUFFICIENT_EVIDENCE" else "VERIFIED"
        raw_rule_ref = incident.rule_id or incident.event_type or "DEFAULT_RULE"
        canonical_rule_uuid, _ = await cls._resolve_rule_aliases(db, raw_rule_ref)
        target_rule = canonical_rule_uuid or raw_rule_ref

        # 4. Check existing reviews for THIS incident (exact-once per-incident counting + dispute detection)
        all_inc_revs_stmt = select(AnalystVerdictReview).where(
            AnalystVerdictReview.incident_id == incident.id
        ).order_by(AnalystVerdictReview.created_at.asc())
        all_inc_revs = list((await db.execute(all_inc_revs_stmt)).scalars().all())
        existing_rev = next((r for r in all_inc_revs if str(r.reviewer_id) == str(reviewer_id)), None)
        other_revs = [r for r in all_inc_revs if str(r.reviewer_id) != str(reviewer_id)]

        if existing_rev:
            if existing_rev.analyst_verdict == analyst_verdict:
                # Exact duplicate submission: idempotent return without double-counting metrics
                return {
                    "review_id": existing_rev.id,
                    "incident_id": incident.incident_id,
                    "analyst_verdict": existing_rev.analyst_verdict,
                    "revealed_ai_verdict": existing_rev.revealed_ai_verdict,
                    "revealed_ai_confidence": ai_verdict_data.get("confidence"),
                    "revealed_ai_rationale": ai_verdict_data.get("reasoning") or ai_verdict_data.get("summary") or ai_verdict_data.get("explanation"),
                    "comparison_outcome": existing_rev.comparison_outcome,
                    "disagreement_reason": disagreement_reason,
                    "ground_truth_status": existing_rev.ground_truth_status,
                    "reviewed_at": existing_rev.created_at.isoformat(),
                    "is_duplicate": True,
                }
            else:
                # Analyst updated/corrected determination
                old_verdict = existing_rev.analyst_verdict
                old_outcome = existing_rev.comparison_outcome
                existing_rev.analyst_verdict = analyst_verdict
                existing_rev.analyst_notes = analyst_notes
                existing_rev.correction_reason = correction_reason
                existing_rev.evidence_references = evidence_references or []
                existing_rev.revealed_ai_verdict = revealed_ai_verdict
                existing_rev.comparison_outcome = comparison_outcome
                existing_rev.ground_truth_status = ground_truth_status
                existing_rev.review_version += 1
                db.add(existing_rev)

                # Update investigation
                inv_stmt = select(Investigation).where(Investigation.incident_id == incident.id)
                inv_res = await db.execute(inv_stmt)
                investigation = inv_res.scalar_one_or_none()
                if investigation:
                    investigation.analyst_verdict = analyst_verdict
                    investigation.verdict_reason = analyst_notes
                    db.add(investigation)

                # Update LearningRecord
                learn_stmt = select(LearningRecord).where(
                    and_(
                        LearningRecord.rule_id == target_rule,
                        LearningRecord.incident_id == incident.id
                    )
                )
                learn_res = await db.execute(learn_stmt)
                learn_rec = learn_res.scalar_one_or_none()
                if learn_rec:
                    learn_rec.verified_verdict = analyst_verdict
                    learn_rec.analyst_explanation = analyst_notes
                    learn_rec.verification_status = ground_truth_status
                    db.add(learn_rec)

                # Recalibrate profile metrics safely
                profile = await RuleLearningService.get_or_create_profile(
                    db=db,
                    rule_id=target_rule,
                    customer=effective_customer
                )
                await RuleLearningService.adjust_analyst_feedback(
                    db=db,
                    profile_id=profile.id,
                    old_verdict=old_verdict,
                    old_outcome=old_outcome,
                    new_verdict=analyst_verdict,
                    new_outcome=comparison_outcome
                )

                return {
                    "review_id": existing_rev.id,
                    "incident_id": incident.incident_id,
                    "analyst_verdict": analyst_verdict,
                    "revealed_ai_verdict": revealed_ai_verdict,
                    "revealed_ai_confidence": ai_verdict_data.get("confidence"),
                    "revealed_ai_rationale": ai_verdict_data.get("reasoning") or ai_verdict_data.get("summary") or ai_verdict_data.get("explanation"),
                    "comparison_outcome": comparison_outcome,
                    "disagreement_reason": disagreement_reason,
                    "ground_truth_status": ground_truth_status,
                    "reviewed_at": existing_rev.created_at.isoformat(),
                    "is_updated": True,
                }

        # Check multi-analyst dispute if another reviewer already submitted a conflicting verdict
        is_second_reviewer = len(other_revs) > 0
        prior_verdicts = {r.analyst_verdict for r in other_revs if r.analyst_verdict}
        has_inter_analyst_dispute = bool(is_second_reviewer and any(pv != analyst_verdict for pv in prior_verdicts))
        if has_inter_analyst_dispute:
            ground_truth_status = "DISPUTED"
            comparison_outcome = "DISPUTED"
            disagreement_reason = f"Inter-analyst dispute: reviewer '{reviewer_id}' ({analyst_verdict}) disagreed with prior review ({', '.join(sorted(prior_verdicts))}). Requires L2 adjudication."
            for prev_r in other_revs:
                prev_r.ground_truth_status = "DISPUTED"
                db.add(prev_r)

        # 5. First-time review by this reviewer: check investigation record or create
        inv_stmt = select(Investigation).where(Investigation.incident_id == incident.id)
        inv_res = await db.execute(inv_stmt)
        investigation = inv_res.scalar_one_or_none()
        if not investigation:
            investigation = Investigation(
                incident_id=incident.id,
                status="DISPUTED" if has_inter_analyst_dispute else "REVIEWED",
                analyst_verdict=analyst_verdict,
                verdict_reason=analyst_notes,
                is_independently_verified=not has_inter_analyst_dispute,
            )
            if hasattr(investigation, "is_disputed"):
                investigation.is_disputed = has_inter_analyst_dispute
            db.add(investigation)
            await db.flush()
        else:
            investigation.status = "DISPUTED" if has_inter_analyst_dispute else "REVIEWED"
            investigation.analyst_verdict = analyst_verdict
            investigation.verdict_reason = analyst_notes
            investigation.is_independently_verified = not has_inter_analyst_dispute
            if hasattr(investigation, "is_disputed"):
                investigation.is_disputed = has_inter_analyst_dispute
            db.add(investigation)

        # 6. Persist immutable AnalystVerdictReview
        review = AnalystVerdictReview(
            incident_id=incident.id,
            investigation_id=investigation.id,
            rule_id=target_rule,
            customer=effective_customer,
            reviewer_id=reviewer_id,
            analyst_verdict=analyst_verdict,
            analyst_notes=analyst_notes,
            correction_reason=correction_reason,
            evidence_references=evidence_references or [],
            blind_mode_active=blind_mode_active,
            revealed_ai_verdict=revealed_ai_verdict,
            comparison_outcome=comparison_outcome,
            ground_truth_status=ground_truth_status,
        )
        db.add(review)
        await db.flush()

        # 7. Create / Update LearningRecord (only VERIFIED TP/FP enter verified RAG pool; DISPUTED/INSUFFICIENT excluded)
        if target_rule and canonical_rule_uuid:
            learn_stmt = select(LearningRecord).where(
                and_(
                    LearningRecord.rule_id == canonical_rule_uuid,
                    LearningRecord.incident_id == incident.id
                )
            )
            learn_res = await db.execute(learn_stmt)
            learn_rec = learn_res.scalar_one_or_none()
            if not learn_rec:
                learn_rec = LearningRecord(
                    rule_id=canonical_rule_uuid,
                    incident_id=incident.id,
                    verified_verdict=analyst_verdict,
                    analyst_explanation=analyst_notes,
                    verification_status=ground_truth_status,
                    evidence_references=evidence_references or [],
                )
                db.add(learn_rec)
            else:
                learn_rec.verified_verdict = analyst_verdict
                learn_rec.analyst_explanation = analyst_notes
                learn_rec.verification_status = ground_truth_status
                db.add(learn_rec)

        # 8. Update RuleLearningProfile metrics STRICTLY ONCE per incident (never double-count 2nd reviewer)
        if target_rule and not is_second_reviewer:
            profile = await RuleLearningService.get_or_create_profile(
                db=db,
                rule_id=target_rule,
                customer=effective_customer
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
            "revealed_ai_confidence": ai_verdict_data.get("confidence"),
            "revealed_ai_rationale": ai_verdict_data.get("reasoning") or ai_verdict_data.get("summary") or ai_verdict_data.get("explanation"),
            "raw_model_verdict": ai_verdict_data.get("raw_verdict") or ai_verdict_data.get("verdict"),
            "effective_verdict": ai_verdict_data.get("effective_verdict") or revealed_ai_verdict,
            "policy_version": ai_verdict_data.get("policy_version") or ai_verdict_data.get("policy_version_number"),
            "model_name": ai_verdict_data.get("model") or ai_verdict_data.get("model_name"),
            "grounding_status": ai_verdict_data.get("grounding_status") or ai_verdict_data.get("validation_status"),
            "comparison_outcome": comparison_outcome,
            "disagreement_reason": disagreement_reason,
            "ground_truth_status": ground_truth_status,
            "is_second_reviewer": is_second_reviewer,
            "is_disputed": has_inter_analyst_dispute,
            "reviewed_at": review.created_at.isoformat(),
        }

    @classmethod
    def _classify_outcome(
        cls,
        analyst_verdict: str,
        ai_verdict: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        """Determines agreement outcome classification."""
        norm_analyst = analyst_verdict.upper().strip()
        norm_ai = ai_verdict.upper().strip() if ai_verdict else None

        if norm_analyst in ("INSUFFICIENT_EVIDENCE", "ABSTAIN", "INCONCLUSIVE"):
            return "ANALYST_INSUFFICIENT_EVIDENCE", "Analyst determined evidence is insufficient to verify ground truth."

        if not norm_ai:
            return "ANALYST_ONLY_INITIAL_BENCHMARK", None

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

        if norm_ai in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE"):
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
        Binding L2 adjudication for disputed or disagreed reviews.
        Recalculates comparison outcome, updates LearningRecord, resolves disputes,
        and recalibrates RuleLearningProfile metrics (including critical missed TP suspension).
        """
        rev_stmt = select(AnalystVerdictReview).where(AnalystVerdictReview.id == review_id)
        rev_res = await db.execute(rev_stmt)
        review = rev_res.scalar_one_or_none()
        if not review:
            raise ValueError(f"Review {review_id} not found")

        norm_final = final_verdict.upper().strip()
        old_verdict = review.analyst_verdict
        old_outcome = review.comparison_outcome

        new_outcome, _ = cls._classify_outcome(
            analyst_verdict=norm_final,
            ai_verdict=review.revealed_ai_verdict,
        )
        new_gt_status = "INSUFFICIENT_EVIDENCE" if norm_final == "INSUFFICIENT_EVIDENCE" else "ADJUDICATED"

        adjudication = AnalystReviewAdjudication(
            review_id=review.id,
            incident_id=review.incident_id,
            adjudicator_user_id=adjudicator_id,
            final_verdict=norm_final,
            adjudication_rationale=rationale,
            original_dispute_reason=review.analyst_notes
        )
        db.add(adjudication)

        review.analyst_verdict = norm_final
        review.comparison_outcome = new_outcome
        review.ground_truth_status = new_gt_status
        db.add(review)

        # Resolve any sibling disputed reviews on the same incident
        sib_res = await db.execute(
            select(AnalystVerdictReview).where(
                and_(
                    AnalystVerdictReview.incident_id == review.incident_id,
                    AnalystVerdictReview.id != review.id,
                    AnalystVerdictReview.ground_truth_status == "DISPUTED",
                )
            )
        )
        for sib in sib_res.scalars().all():
            sib.ground_truth_status = "SUPERSEDED_BY_ADJUDICATION"
            db.add(sib)

        # Update Investigation
        inv_res = await db.execute(select(Investigation).where(Investigation.incident_id == review.incident_id))
        inv = inv_res.scalar_one_or_none()
        if inv:
            inv.status = "REVIEWED"
            inv.analyst_verdict = norm_final
            inv.verdict_reason = rationale
            inv.is_independently_verified = (norm_final != "INSUFFICIENT_EVIDENCE")
            if hasattr(inv, "is_disputed"):
                inv.is_disputed = False
            db.add(inv)

        # Update LearningRecord
        canonical_uuid, _ = await cls._resolve_rule_aliases(db, review.rule_id)
        if canonical_uuid:
            learn_res = await db.execute(
                select(LearningRecord).where(
                    and_(
                        LearningRecord.rule_id == canonical_uuid,
                        LearningRecord.incident_id == review.incident_id,
                    )
                )
            )
            learn_rec = learn_res.scalar_one_or_none()
            lr_status = "VERIFIED" if norm_final in ("TRUE_POSITIVE", "FALSE_POSITIVE") else "INSUFFICIENT_EVIDENCE"
            if learn_rec:
                learn_rec.verified_verdict = norm_final
                learn_rec.analyst_explanation = rationale
                learn_rec.verification_status = lr_status
                db.add(learn_rec)
            else:
                db.add(LearningRecord(
                    rule_id=canonical_uuid,
                    incident_id=review.incident_id,
                    verified_verdict=norm_final,
                    analyst_explanation=rationale,
                    verification_status=lr_status,
                ))

        # Recalibrate RuleLearningProfile metrics cleanly
        if review.rule_id:
            profile = await RuleLearningService.get_or_create_profile(
                db=db,
                rule_id=review.rule_id,
                customer=review.customer or "DEFAULT",
            )
            await RuleLearningService.adjust_analyst_feedback(
                db=db,
                profile_id=profile.id,
                old_verdict=old_verdict,
                old_outcome=old_outcome,
                new_verdict=norm_final,
                new_outcome=new_outcome,
            )

        await db.flush()

        return {
            "adjudication_id": adjudication.id,
            "review_id": review.id,
            "final_verdict": norm_final,
            "comparison_outcome": new_outcome,
            "ground_truth_status": new_gt_status,
            "adjudicator": adjudicator_id,
            "adjudicated_at": adjudication.created_at.isoformat()
        }

