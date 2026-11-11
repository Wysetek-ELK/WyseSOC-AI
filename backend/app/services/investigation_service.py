from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from app.utils.datetime_utils import utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

from app.models.investigation import Investigation, InvestigationQuestion, InvestigationEvidence
from app.models.incident import Incident
from app.models.rule import Rule
from app.models.user import User
from app.models.learning import LearningRecord
from app.models.audit import AuditLog
from app.models.pilot import PilotEvaluationRecord
from app.models.verdict_intelligence import VerdictTrustAssessmentRecord
from app.services.provenance import classify_endpoint_status, classify_execution_provenance
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.schemas.investigation import (
    AIAssuranceSummary,
    InvestigationListItem,
    InvestigationDetailResponse,
    InvestigationQuestionResponse,
    InvestigationEvidenceResponse,
    AnalystVerdictSubmit,
)


class ReviewOrchestrator:
    """
    Review Orchestrator (formerly InvestigationService).
    Manages the Human Review Queue, escalation workflows, analyst verdicts,
    and human-in-the-loop feedback orchestration for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_all_incidents_have_investigations(self) -> int:
        """
        Idempotently creates Investigation records for any incidents that don't have one yet.
        """
        # Find incidents with no investigation
        subq = select(Investigation.incident_id)
        stmt = select(Incident).where(Incident.id.not_in(subq))
        res = await self.db.execute(stmt)
        unassigned_incidents = res.scalars().all()

        created_count = 0
        for inc in unassigned_incidents:
            inv = Investigation(
                incident_id=inc.id,
                status="PENDING_REVIEW",
            )
            self.db.add(inv)
            created_count += 1

        if created_count > 0:
            await self.db.commit()

        return created_count

    async def list_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        assigned_to_user_id: Optional[str] = None,
        analyst_verdict: Optional[str] = None,
        is_disputed: Optional[bool] = None,
        rule_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[InvestigationListItem], int]:
        # Ensure queue is populated
        await self.ensure_all_incidents_have_investigations()

        query = select(Investigation).options(
            selectinload(Investigation.incident).selectinload(Incident.rule),
            selectinload(Investigation.assigned_user),
            selectinload(Investigation.questions),
            selectinload(Investigation.evidence_items),
        )

        if status:
            query = query.where(Investigation.status == status.upper())

        if assigned_to_user_id:
            query = query.where(Investigation.assigned_to_user_id == assigned_to_user_id)

        if analyst_verdict:
            query = query.where(Investigation.analyst_verdict == analyst_verdict.upper())

        if is_disputed is not None:
            query = query.where(Investigation.is_disputed == is_disputed)

        if rule_id:
            query = query.join(Investigation.incident).where(
                or_(Incident.rule_id == rule_id, Incident.event_type == rule_id)
            )

        if search:
            search_term = f"%{search.strip()}%"
            query = query.join(Investigation.incident).where(
                or_(
                    Incident.incident_id.ilike(search_term),
                    Incident.title.ilike(search_term),
                    Incident.description.ilike(search_term),
                    Incident.event_type.ilike(search_term),
                    Incident.source_ip.ilike(search_term),
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one()

        # Paginate & Order by updated_at desc
        query = query.order_by(desc(Investigation.updated_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        invs = result.scalars().all()

        items = []
        for inv in invs:
            inc = inv.incident
            rule = inc.rule if inc else None
            user = inv.assigned_user
            norm_av = VerdictTrustworthinessEngine.normalize_ai_verdict_dict(inc.ai_verdict) if inc else None

            items.append(
                InvestigationListItem(
                    id=inv.id,
                    incident_id=inv.incident_id,
                    incident_vendor_id=inc.incident_id if inc else None,
                    title=inc.title if inc else None,
                    rule_id=rule.id if rule else (inc.rule_id if inc else None),
                    rule_name=rule.name if rule else (inc.event_type if inc else None),
                    severity=inc.severity if inc else None,
                    event_type=inc.event_type if inc else None,
                    status=inv.status,
                    assigned_to_user_id=inv.assigned_to_user_id,
                    assigned_to_username=user.username if user else None,
                    analyst_verdict=inv.analyst_verdict,
                    is_disputed=inv.is_disputed,
                    is_independently_verified=inv.is_independently_verified,
                    question_count=len(inv.questions),
                    evidence_count=len(inv.evidence_items),
                    ai_validated_verdict=norm_av.get("verdict") if isinstance(norm_av, dict) else None,
                    ai_trust_score=norm_av.get("trust_score") if isinstance(norm_av, dict) else None,
                    pilot_mode=norm_av.get("pilot_mode") if isinstance(norm_av, dict) else None,
                    created_at=inv.created_at,
                    updated_at=inv.updated_at,
                )
            )

        return items, total

    async def get_by_incident_id(self, incident_id: str) -> Optional[Investigation]:
        query = select(Investigation).where(Investigation.incident_id == incident_id).options(
            selectinload(Investigation.incident).selectinload(Incident.rule),
            selectinload(Investigation.assigned_user),
            selectinload(Investigation.questions),
            selectinload(Investigation.evidence_items),
        )
        res = await self.db.execute(query)
        inv = res.scalars().first()
        if not inv:
            # Check if incident exists
            inc_res = await self.db.execute(select(Incident).where(Incident.id == incident_id))
            inc = inc_res.scalars().first()
            if inc:
                inv = Investigation(incident_id=inc.id, status="PENDING_REVIEW")
                self.db.add(inv)
                await self.db.commit()
                await self.db.refresh(inv)
                return await self.get_by_incident_id(incident_id)
        return inv

    async def get_by_id(self, investigation_id: str) -> Optional[Investigation]:
        query = select(Investigation).where(Investigation.id == investigation_id).options(
            selectinload(Investigation.incident).selectinload(Incident.rule),
            selectinload(Investigation.assigned_user),
            selectinload(Investigation.questions),
            selectinload(Investigation.evidence_items),
        )
        res = await self.db.execute(query)
        return res.scalars().first()

    async def assign_analyst(self, investigation_id: str, user_id: Optional[str]) -> Optional[Investigation]:
        inv = await self.get_by_id(investigation_id)
        if not inv:
            return None

        inv.assigned_to_user_id = user_id
        if user_id and inv.status == "PENDING_REVIEW":
            inv.status = "ASSIGNED"
        elif not user_id and inv.status == "ASSIGNED":
            inv.status = "PENDING_REVIEW"

        inv.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(inv)
        return inv

    async def update_status(self, investigation_id: str, new_status: str) -> Optional[Investigation]:
        valid_statuses = {"PENDING_REVIEW", "ASSIGNED", "IN_PROGRESS", "AWAITING_INFORMATION", "REVIEWED", "CLOSED_DRY_RUN"}
        normalized_status = new_status.upper().strip()
        if normalized_status not in valid_statuses:
            raise ValueError(f"Invalid investigation status: {new_status}. Allowed: {valid_statuses}")

        inv = await self.get_by_id(investigation_id)
        if not inv:
            return None

        inv.status = normalized_status
        inv.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(inv)
        return inv

    async def add_question(self, investigation_id: str, question: str, asked_by_user_id: Optional[str]) -> InvestigationQuestion:
        inv = await self.get_by_id(investigation_id)
        if not inv:
            raise ValueError("Investigation not found")

        q = InvestigationQuestion(
            investigation_id=investigation_id,
            question=question.strip(),
            asked_by_user_id=asked_by_user_id,
        )
        self.db.add(q)

        # Transition status to AWAITING_INFORMATION if in progress or assigned
        if inv.status in {"ASSIGNED", "IN_PROGRESS"}:
            inv.status = "AWAITING_INFORMATION"
        inv.updated_at = utc_now()

        await self.db.commit()
        await self.db.refresh(q)
        return q

    async def answer_question(self, question_id: str, answer: str, answered_by_user_id: Optional[str]) -> Optional[InvestigationQuestion]:
        query = select(InvestigationQuestion).where(InvestigationQuestion.id == question_id)
        res = await self.db.execute(query)
        q = res.scalars().first()
        if not q:
            return None

        q.answer = answer.strip()
        q.answered_by_user_id = answered_by_user_id
        q.answered_at = utc_now()

        # Update investigation updated_at
        inv = await self.get_by_id(q.investigation_id)
        if inv:
            inv.updated_at = utc_now()
            if inv.status == "AWAITING_INFORMATION":
                inv.status = "IN_PROGRESS"

        await self.db.commit()
        await self.db.refresh(q)
        return q

    async def attach_evidence(
        self,
        investigation_id: str,
        evidence_type: str,
        reference_key: str,
        evidence_content: str,
        analyst_rationale: str
    ) -> InvestigationEvidence:
        inv = await self.get_by_id(investigation_id)
        if not inv:
            raise ValueError("Investigation not found")

        ev = InvestigationEvidence(
            investigation_id=investigation_id,
            evidence_type=evidence_type.upper().strip(),
            reference_key=reference_key.strip(),
            evidence_content=evidence_content.strip(),
            analyst_rationale=analyst_rationale.strip(),
        )
        self.db.add(ev)
        inv.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    async def build_ai_assurance(self, inv: Investigation) -> Optional[AIAssuranceSummary]:
        """Builds read-only AI verdict assurance & pilot provenance snapshot for Human Review Queue."""
        inc = inv.incident
        if not inc:
            return None
        rule = inc.rule
        norm_av = VerdictTrustworthinessEngine.normalize_ai_verdict_dict(inc.ai_verdict) or {}

        pe_res = await self.db.execute(
            select(PilotEvaluationRecord)
            .where(PilotEvaluationRecord.incident_id == inc.incident_id)
            .order_by(desc(PilotEvaluationRecord.created_at))
            .limit(1)
        )
        pe = pe_res.scalar_one_or_none()

        trust_res = await self.db.execute(
            select(VerdictTrustAssessmentRecord)
            .where(VerdictTrustAssessmentRecord.incident_id == inc.incident_id)
            .order_by(desc(VerdictTrustAssessmentRecord.evaluated_at))
            .limit(1)
        )
        trec = trust_res.scalar_one_or_none()

        if not norm_av and not pe and not trec:
            return AIAssuranceSummary(
                incident_summary=inc.description or inc.title or "",
                rule_id=rule.rule_id if rule else inc.rule_id,
                rule_name=rule.name if rule else inc.event_type,
            )

        is_cal = bool(
            pe.is_calibrated if pe is not None
            else (trec.is_calibrated if trec is not None else norm_av.get("is_calibrated", False))
        )
        raw_t = (
            pe.trust_score if pe is not None
            else (trec.trust_score if trec is not None else norm_av.get("trust_score"))
        )
        eff_t, hist_t, cap_applied, _ = VerdictTrustworthinessEngine.cap_uncalibrated_trust_score(
            raw_t, is_calibrated=is_cal
        )
        hist_t = hist_t or norm_av.get("historical_trust_score")
        cap_applied = cap_applied or bool(norm_av.get("trust_cap_applied", False))

        pe_prov_details: Dict[str, Any] = {}
        if pe is not None:
            p_res = await self.db.execute(
                select(AuditLog)
                .where(
                    AuditLog.resource_type == "PILOT_EVALUATION",
                    AuditLog.resource_id == pe.id,
                )
                .order_by(desc(AuditLog.created_at))
                .limit(1)
            )
            alog = p_res.scalar_one_or_none()
            if alog and isinstance(alog.details, dict):
                pe_prov_details = alog.details

        from app.services.ai_verdict_service import VerdictTriageAgent
        try:
            s2_online = await VerdictTriageAgent.is_local_llm_available(force_refresh=True)
        except Exception:
            s2_online = False
        ep_status = classify_endpoint_status(is_healthy=s2_online, raw_status="ONLINE" if s2_online else "OFFLINE")

        is_sim_val = bool(pe.is_simulated if pe is not None else (trec.is_simulated if trec is not None else norm_av.get("is_simulated", False)))
        model_id_val = (pe.model_identifier if pe else None) or (trec.model_identifier if trec else None) or norm_av.get("model_identifier")
        val_status_val = (pe.validation_status if pe else None) or norm_av.get("validation_status")
        prov_info = classify_execution_provenance(
            is_simulated=is_sim_val,
            model_identifier=model_id_val,
            validation_status=val_status_val,
            eligibility_status=pe.eligibility_status if pe else None,
            source_type=pe.source_type if pe else "HISTORICAL",
            error_message=pe.error_message if pe else None,
            recorded_provenance=pe_prov_details.get("execution_provenance") or norm_av.get("execution_provenance"),
            recorded_test_env=pe_prov_details.get("test_environment") or norm_av.get("test_environment"),
            is_historical_context=True,
        )

        return AIAssuranceSummary(
            incident_summary=inc.description or inc.title or "",
            rule_id=rule.rule_id if rule else (pe.rule_id if pe else inc.rule_id),
            rule_name=rule.name if rule else inc.event_type,
            policy_version_number=(
                (pe.policy_version_number if pe else None)
                or (trec.applicable_policy_version if trec else None)
                or norm_av.get("policy_version_number")
            ),
            policy_digest=(pe.policy_digest if pe else None) or norm_av.get("compilation_digest"),
            proposed_verdict=(pe.proposed_verdict if pe else None) or (trec.suggested_verdict if trec else None) or norm_av.get("proposed_verdict"),
            validated_verdict=(pe.validated_verdict if pe else None) or (trec.effective_verdict if trec else None) or norm_av.get("verdict"),
            validation_status=val_status_val,
            abstention_reason=(pe.abstention_reason if pe else None) or (trec.escalation_reason if trec else None) or norm_av.get("abstention_reason"),
            supporting_evidence=list((pe.supporting_evidence if pe else None) or (trec.supporting_evidence if trec else None) or norm_av.get("supporting_evidence") or []),
            contradictory_evidence=list((pe.contradictory_evidence if pe else None) or (trec.contradictory_evidence if trec else None) or norm_av.get("detected_contradictions") or []),
            missing_evidence=list((pe.missing_evidence if pe else None) or (trec.missing_evidence if trec else None) or norm_av.get("missing_evidence") or []),
            trust_score=eff_t,
            historical_trust_score=hist_t,
            trust_cap_applied=cap_applied,
            is_calibrated=is_cal,
            calibration_status="CALIBRATED" if is_cal else "NOT_CALIBRATED",
            historical_sample_count=int(norm_av.get("historical_sample_count") or 0),
            historical_validation_status=str(
                (trec.historical_validation_status if trec else None)
                or norm_av.get("historical_validation_status")
                or "UNCALIBRATED"
            ),
            model_identifier=model_id_val,
            is_simulated=is_sim_val,
            configured_provider=pe_prov_details.get("configured_provider") or norm_av.get("configured_provider") or prov_info["configured_provider"],
            execution_provenance=prov_info["execution_provenance"],
            historical_execution_provenance=prov_info["historical_execution_provenance"],
            current_s2_health=ep_status["current_s2_health"],
            test_environment=prov_info["test_environment"],
            pilot_evaluation_id=pe.id if pe else None,
            pilot_mode=(pe.execution_mode if pe else None) or norm_av.get("pilot_mode"),
            evaluated_at=(pe.created_at.isoformat() if pe else None) or norm_av.get("evaluated_at"),
            analyst_feedback_action=pe.analyst_feedback_action if pe else None,
            supervisor_verified=bool(pe.supervisor_verified) if pe else False,
        )

    async def submit_verdict(
        self,
        investigation_id: str,
        verdict_data: AnalystVerdictSubmit,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Investigation:
        inv = await self.get_by_id(investigation_id)
        if not inv:
            raise ValueError("Investigation not found")

        valid_verdicts = {"TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"}
        verdict_norm = verdict_data.analyst_verdict.upper().strip()
        if verdict_norm not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {verdict_data.analyst_verdict}. Allowed: {valid_verdicts}")

        inv.analyst_verdict = verdict_norm
        inv.verdict_reason = verdict_data.verdict_reason
        inv.analyst_notes = verdict_data.analyst_notes
        inv.insufficient_evidence_reason = verdict_data.insufficient_evidence_reason
        inv.is_disputed = verdict_data.is_disputed
        inv.is_independently_verified = verdict_data.is_independently_verified
        inv.status = verdict_data.status or "REVIEWED"
        inv.updated_at = utc_now()

        # If independently verified and not disputed, sync to LearningRecord for AI training Ground Truth
        if inv.is_independently_verified and not inv.is_disputed:
            inc = inv.incident
            rule_id = inc.rule_id if (inc and inc.rule_id) else None
            if not rule_id and inc:
                # Resolve rule by event_type
                rule_res = await self.db.execute(select(Rule).where(Rule.event_type == inc.event_type))
                rule_obj = rule_res.scalars().first()
                if rule_obj:
                    rule_id = rule_obj.id

            if rule_id:
                # Check if learning record already exists
                lr_query = select(LearningRecord).where(
                    LearningRecord.incident_id == inv.incident_id,
                    LearningRecord.rule_id == rule_id
                )
                lr_res = await self.db.execute(lr_query)
                lr = lr_res.scalars().first()

                # Extract answered questions
                qa_data = [{"question": q.question, "answer": q.answer} for q in inv.questions if q.answer]
                ev_refs = [e.reference_key for e in inv.evidence_items if e.reference_key]

                tp_inds = [inv.verdict_reason] if verdict_norm == "TRUE_POSITIVE" else []
                fp_inds = [inv.verdict_reason] if verdict_norm == "FALSE_POSITIVE" else []
                missing_ev = [inv.insufficient_evidence_reason] if inv.insufficient_evidence_reason else []

                if not lr:
                    lr = LearningRecord(
                        rule_id=rule_id,
                        incident_id=inv.incident_id,
                        verified_verdict=verdict_norm,
                        analyst_explanation=inv.analyst_notes or inv.verdict_reason,
                        tp_indicators=tp_inds,
                        fp_indicators=fp_inds,
                        missing_evidence=missing_ev,
                        evidence_references=ev_refs,
                        answered_questions=qa_data,
                        verification_status="PENDING_REVIEW",
                        feedback_timestamp=utc_now(),
                    )
                    self.db.add(lr)
                else:
                    lr.verified_verdict = verdict_norm
                    lr.analyst_explanation = inv.analyst_notes or inv.verdict_reason
                    lr.tp_indicators = tp_inds
                    lr.fp_indicators = fp_inds
                    lr.missing_evidence = missing_ev
                    lr.evidence_references = ev_refs
                    lr.answered_questions = qa_data
                    lr.verification_status = "PENDING_REVIEW"
                    lr.feedback_timestamp = utc_now()

        # Sync analyst decision to latest PilotEvaluationRecord without overwriting AI verdict
        if inv.incident:
            pe_res = await self.db.execute(
                select(PilotEvaluationRecord)
                .where(PilotEvaluationRecord.incident_id == inv.incident.incident_id)
                .order_by(desc(PilotEvaluationRecord.created_at))
                .limit(1)
            )
            pe_rec = pe_res.scalar_one_or_none()
            if pe_rec:
                explicit_action = (getattr(verdict_data, "action_type", None) or "").upper().strip()
                if explicit_action in ("ACCEPTED", "OVERRIDDEN", "DISPUTED", "REQUESTED_EVIDENCE"):
                    action = explicit_action
                elif inv.is_disputed:
                    action = "DISPUTED"
                elif pe_rec.validated_verdict == verdict_norm:
                    action = "ACCEPTED"
                else:
                    action = "OVERRIDDEN"
                pe_rec.analyst_feedback_action = action
                pe_rec.analyst_decision = verdict_norm
                pe_rec.analyst_override_reason = verdict_data.verdict_reason or verdict_data.analyst_notes
                pe_rec.analyst_user = username or user_id or "analyst"
                pe_rec.analyst_decided_at = utc_now()
                pe_rec.supervisor_verified = False
                pe_rec.updated_at = utc_now()
                self.db.add(pe_rec)

        await self.db.commit()
        await self.db.refresh(inv)
        return inv


# Backward compatibility alias
InvestigationService = ReviewOrchestrator


