from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from app.utils.datetime_utils import utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

from app.models.learning import LearningRecord
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.schemas.learning import (
    LearningRecordResponse,
    SimilarCaseMatch,
    SimilarCaseQuery,
)


class AgentMemoryEngine:
    """
    Agent Memory Engine.
    Manages analyst feedback, precedent matching, few-shot historical retrieval,
    and continuous learning memory records for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        rule_id: Optional[str] = None,
        verification_status: Optional[str] = None,
        verdict: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[LearningRecordResponse], int]:
        query = select(LearningRecord).options(
            selectinload(LearningRecord.rule),
            selectinload(LearningRecord.incident)
        )

        if rule_id:
            query = query.where(LearningRecord.rule_id == rule_id)

        if verification_status:
            query = query.where(LearningRecord.verification_status == verification_status.upper())

        if verdict:
            query = query.where(LearningRecord.verified_verdict == verdict.upper())

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    LearningRecord.analyst_explanation.ilike(search_term),
                    LearningRecord.verified_verdict.ilike(search_term),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one()

        # Order & Paginate
        query = query.order_by(desc(LearningRecord.feedback_timestamp))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        records = result.scalars().all()

        items = []
        for r in records:
            items.append(
                LearningRecordResponse(
                    id=r.id,
                    rule_id=r.rule_id,
                    rule_name=r.rule.name if r.rule else None,
                    incident_id=r.incident_id,
                    incident_vendor_id=r.incident.incident_id if r.incident else None,
                    incident_title=r.incident.title if r.incident else None,
                    verified_verdict=r.verified_verdict,
                    analyst_explanation=r.analyst_explanation,
                    tp_indicators=r.tp_indicators or [],
                    fp_indicators=r.fp_indicators or [],
                    missing_evidence=r.missing_evidence or [],
                    evidence_references=r.evidence_references or [],
                    answered_questions=r.answered_questions or [],
                    verification_status=r.verification_status,
                    feedback_timestamp=r.feedback_timestamp,
                    created_at=r.created_at,
                )
            )

        return items, total

    async def get_record(self, record_id: str) -> Optional[LearningRecordResponse]:
        query = select(LearningRecord).where(LearningRecord.id == record_id).options(
            selectinload(LearningRecord.rule),
            selectinload(LearningRecord.incident)
        )
        res = await self.db.execute(query)
        r = res.scalars().first()
        if not r:
            return None

        return LearningRecordResponse(
            id=r.id,
            rule_id=r.rule_id,
            rule_name=r.rule.name if r.rule else None,
            incident_id=r.incident_id,
            incident_vendor_id=r.incident.incident_id if r.incident else None,
            incident_title=r.incident.title if r.incident else None,
            verified_verdict=r.verified_verdict,
            analyst_explanation=r.analyst_explanation,
            tp_indicators=r.tp_indicators or [],
            fp_indicators=r.fp_indicators or [],
            missing_evidence=r.missing_evidence or [],
            evidence_references=r.evidence_references or [],
            answered_questions=r.answered_questions or [],
            verification_status=r.verification_status,
            feedback_timestamp=r.feedback_timestamp,
            created_at=r.created_at,
        )

    async def update_verification_status(
        self,
        record_id: str,
        status: str,
        reviewer_username: str,
        review_notes: Optional[str] = None,
    ) -> Optional[LearningRecordResponse]:
        """
        Supervisor / Admin verification gate for learning history (REQ-05 / AV-008).
        Ensures unreviewed analyst feedback cannot immediately contaminate AI prompts.
        """
        status_norm = status.strip().upper()
        if status_norm not in ("VERIFIED", "REJECTED", "DISPUTED", "PENDING_REVIEW"):
            raise ValueError(f"Invalid verification status: {status}")

        query = select(LearningRecord).where(LearningRecord.id == record_id).options(
            selectinload(LearningRecord.rule),
            selectinload(LearningRecord.incident)
        )
        res = await self.db.execute(query)
        rec = res.scalars().first()
        if not rec:
            return None

        rec.verification_status = status_norm
        await self.db.commit()
        await self.db.refresh(rec)

        # Trigger Policy Lifecycle Monitor on verified analyst divergence (REQ-10)
        if status_norm == "VERIFIED" and rec.rule_id:
            try:
                from app.services.policy_lifecycle_monitor import PolicyLifecycleMonitor
                model_v = "UNKNOWN"
                inc_vendor_id = str(rec.incident_id)
                if rec.incident:
                    inc_vendor_id = str(rec.incident.incident_id or rec.incident.id)
                    if isinstance(rec.incident.ai_verdict, dict):
                        model_v = str(rec.incident.ai_verdict.get("verdict") or "UNKNOWN")
                monitor = PolicyLifecycleMonitor(self.db)
                await monitor.ingest_verified_analyst_feedback(
                    rule_id=rec.rule_id,
                    incident_id=inc_vendor_id,
                    adjudicated_verdict=rec.verified_verdict,
                    model_verdict=model_v,
                    analyst_notes=rec.analyst_explanation or "",
                    user_id=reviewer_username,
                )
            except Exception as mon_exc:
                import logging
                logging.getLogger(__name__).warning(f"PolicyLifecycleMonitor verified-feedback hook failed: {mon_exc}")

        return LearningRecordResponse(
            id=rec.id,
            rule_id=rec.rule_id,
            rule_name=rec.rule.name if rec.rule else None,
            incident_id=rec.incident_id,
            incident_vendor_id=rec.incident.incident_id if rec.incident else None,
            incident_title=rec.incident.title if rec.incident else None,
            verified_verdict=rec.verified_verdict,
            analyst_explanation=rec.analyst_explanation,
            tp_indicators=rec.tp_indicators or [],
            fp_indicators=rec.fp_indicators or [],
            missing_evidence=rec.missing_evidence or [],
            evidence_references=rec.evidence_references or [],
            answered_questions=rec.answered_questions or [],
            verification_status=rec.verification_status,
            feedback_timestamp=rec.feedback_timestamp,
            created_at=rec.created_at,
        )

    async def find_similar_cases(self, params: SimilarCaseQuery) -> List[SimilarCaseMatch]:
        """
        DETERMINISTIC SIMILARITY ENGINE
        Matches cases based on explicit telemetry overlap:
        - Exact Event Type / Rule ID
        - Source IP match
        - Reporting device match
        - Process command line keyword overlap
        - Title / Category match
        Does NOT claim AI semantic embeddings.
        """
        # If incident_id is passed, load its attributes
        target_incident = None
        if params.incident_id:
            res = await self.db.execute(
                select(Incident).where(Incident.id == params.incident_id).options(
                    selectinload(Incident.events)
                )
            )
            target_incident = res.scalars().first()

        target_rule_id = params.rule_id or (target_incident.rule_id if target_incident else None)
        target_event_type = params.event_type or (target_incident.event_type if target_incident else None)
        target_ip = params.source_ip or (target_incident.source_ip if target_incident else None)

        # Extract target command keywords if incident is present
        target_cmd_tokens = set()
        if target_incident and target_incident.events:
            for ev in target_incident.events:
                if ev.raw_log:
                    for token in ev.raw_log.lower().split():
                        clean = token.strip("\"',;()[]{}")
                        if len(clean) > 3 and not clean.startswith("-"):
                            target_cmd_tokens.add(clean)
                if isinstance(ev.attributes, dict):
                    for k, v in ev.attributes.items():
                        if isinstance(v, str):
                            for token in v.lower().split():
                                clean = token.strip("\"',;()[]{}")
                                if len(clean) > 3 and not clean.startswith("-"):
                                    target_cmd_tokens.add(clean)

        if params.command_substring:
            target_cmd_tokens.add(params.command_substring.lower())

        # Load candidate verified learning records
        query = select(LearningRecord).options(
            selectinload(LearningRecord.incident).selectinload(Incident.events),
            selectinload(LearningRecord.incident).selectinload(Incident.rule),
        ).where(LearningRecord.verification_status == "VERIFIED")

        if target_rule_id:
            query = query.where(LearningRecord.rule_id == target_rule_id)

        res = await self.db.execute(query)
        candidates = res.scalars().all()

        scored_matches: List[Tuple[float, List[str], LearningRecord]] = []

        for cand in candidates:
            inc = cand.incident
            if not inc:
                continue

            # Don't match the same incident
            if target_incident and inc.id == target_incident.id:
                continue

            score = 0.0
            matched_features = []

            # 1. Event Type Match
            if target_event_type and inc.event_type and target_event_type.lower() == inc.event_type.lower():
                score += 0.40
                matched_features.append(f"Matching Event Type ({inc.event_type})")

            # 2. Rule Match
            if target_rule_id and inc.rule_id == target_rule_id:
                score += 0.20
                matched_features.append("Matching SIEM Detection Rule")

            # 3. Source IP Match
            if target_ip and inc.source_ip and target_ip == inc.source_ip:
                score += 0.20
                matched_features.append(f"Matching Source IP ({inc.source_ip})")

            # 4. Command Token Overlap
            if target_cmd_tokens and inc.events:
                cand_tokens = set()
                for cev in inc.events:
                    if cev.raw_log:
                        for ctok in cev.raw_log.lower().split():
                            clean = ctok.strip("\"',;()[]{}")
                            if len(clean) > 3:
                                cand_tokens.add(clean)
                    if isinstance(cev.attributes, dict):
                        for k, v in cev.attributes.items():
                            if isinstance(v, str):
                                for ctok in v.lower().split():
                                    clean = ctok.strip("\"',;()[]{}")
                                    if len(clean) > 3:
                                        cand_tokens.add(clean)
                overlap = target_cmd_tokens.intersection(cand_tokens)
                if overlap:
                    score += min(0.20, len(overlap) * 0.05)
                    matched_features.append(f"Overlapping Command Artifacts: {', '.join(list(overlap)[:3])}")

            # Baseline similarity if candidates exist in same verified bucket
            if score == 0.0:
                score = 0.10
                matched_features.append("Verified Case in Same Knowledge Base")

            score = min(1.0, round(score, 2))
            scored_matches.append((score, matched_features, cand))

        # Sort by score desc
        scored_matches.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, features, cand in scored_matches[:params.top_k]:
            inc = cand.incident
            results.append(
                SimilarCaseMatch(
                    learning_record_id=cand.id,
                    incident_id=cand.incident_id,
                    incident_vendor_id=inc.incident_id if inc else None,
                    title=inc.title if inc else None,
                    verified_verdict=cand.verified_verdict,
                    analyst_explanation=cand.analyst_explanation,
                    match_score=score,
                    matched_features=features,
                    feedback_timestamp=cand.feedback_timestamp,
                )
            )

        return results

    async def seed_verified_cases_from_historical_incidents(self) -> int:
        """
        Initializes learning records from historical incidents that have high-confidence
        verified ground truth resolutions in the database.
        """
        # Get incidents with ground truth
        query = select(Incident).options(
            selectinload(Incident.ground_truth),
            selectinload(Incident.rule),
            selectinload(Incident.events)
        ).join(Incident.ground_truth)

        res = await self.db.execute(query)
        incidents = res.scalars().all()

        added_count = 0
        for inc in incidents:
            gt = inc.ground_truth
            if not gt or not gt.resolution:
                continue

            # Map resolution to verdict
            verdict = "REQUIRES_ATTENTION"
            res_str = gt.resolution.lower()
            if "true positive" in res_str or "malicious" in res_str:
                verdict = "TRUE_POSITIVE"
            elif "false positive" in res_str or "benign" in res_str or "legitimate" in res_str:
                verdict = "FALSE_POSITIVE"

            # Check if record already exists
            existing = await self.db.execute(
                select(LearningRecord).where(LearningRecord.incident_id == inc.id)
            )
            if existing.scalars().first():
                continue

            rule_id = inc.rule_id
            if not rule_id and inc.rule:
                rule_id = inc.rule.id

            if not rule_id:
                # Find rule by event_type
                r_res = await self.db.execute(select(Rule).where(Rule.event_type == inc.event_type))
                r_obj = r_res.scalars().first()
                if r_obj:
                    rule_id = r_obj.id

            if not rule_id:
                continue

            tp_inds = []
            fp_inds = []
            if verdict == "TRUE_POSITIVE":
                tp_inds.append(f"Historical resolution: {gt.resolution}")
                if gt.cleared_reason:
                    tp_inds.append(gt.cleared_reason)
            elif verdict == "FALSE_POSITIVE":
                fp_inds.append(f"Historical resolution: {gt.resolution}")
                if gt.cleared_reason:
                    fp_inds.append(gt.cleared_reason)

            lr = LearningRecord(
                rule_id=rule_id,
                incident_id=inc.id,
                verified_verdict=verdict,
                analyst_explanation=f"Historical verified resolution: {gt.resolution}. {gt.cleared_reason or ''}".strip(),
                tp_indicators=tp_inds,
                fp_indicators=fp_inds,
                missing_evidence=[],
                evidence_references=[f"Incident ID {inc.incident_id}"],
                answered_questions=[],
                verification_status="VERIFIED",
                feedback_timestamp=utc_now(),
            )
            self.db.add(lr)
            added_count += 1

        if added_count > 0:
            await self.db.commit()

        return added_count


# Backward compatibility alias
LearningService = AgentMemoryEngine

