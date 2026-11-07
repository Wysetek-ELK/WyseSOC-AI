import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, or_
from sqlalchemy.orm import selectinload

from app.models.incident import Incident
from app.models.rule import Rule
from app.models.learning import LearningRecord
from app.models.investigation import Investigation
from app.models.audit import AuditLog
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.factory import get_model_provider
from app.services.prompt_studio_service import PromptStudioService, COMMON_SOC_BASELINE


class AIVerdictService:
    """
    Unified AI Verdict Engine.
    Executes zero-bias incident evaluations with strict ground-truth isolation,
    dynamic prompt synthesis (Level-2 SOC criteria + few-shot RAG),
    and resilient model provider fallback.
    """

    _last_probe_time: float = 0.0
    _is_local_llm_online: Optional[bool] = None

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    async def is_local_llm_available(cls) -> bool:
        """Checks if Server 2 LLM endpoint is reachable, caching result for 30s."""
        now = time.time()
        if cls._is_local_llm_online is not None and (now - cls._last_probe_time) < 30.0:
            return cls._is_local_llm_online

        cls._last_probe_time = now
        provider = get_model_provider("OPENAI_COMPATIBLE")
        try:
            health = await provider.get_health()
            cls._is_local_llm_online = (health.status == "HEALTHY")
        except Exception:
            cls._is_local_llm_online = False
        return cls._is_local_llm_online

    async def evaluate_incident(
        self,
        incident_id_or_obj: Union[str, Incident],
        username: str = "system",
        model_provider_type: Optional[str] = None,
        allow_simulated_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluates a single incident with the LLM.
        Auto-provisions detection rules if unmapped, formats allowlisted model telemetry,
        and saves the structured verdict to the database.
        """
        # 1. Resolve incident object cleanly with eager-loaded relationships
        clean_target_id = incident_id_or_obj if isinstance(incident_id_or_obj, str) else str(getattr(incident_id_or_obj, "id", getattr(incident_id_or_obj, "incident_id", "")))
        stmt = (
            select(Incident)
            .where((Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id))
            .options(selectinload(Incident.rule), selectinload(Incident.events))
        )
        res = await self.db.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident '{clean_target_id}' not found.")

        # 2. Auto-resolve Rule if incident is unmapped
        rule = incident.rule
        if not rule and incident.event_type:
            r_q = await self.db.execute(
                select(Rule).where((Rule.event_type == incident.event_type) | (Rule.rule_id == incident.event_type))
            )
            rule = r_q.scalars().first()

            if not rule:
                rule = Rule(
                    rule_id=incident.event_type,
                    name=incident.title if incident.title and incident.title != "No description provided by SIEM." else incident.event_type,
                    event_type=incident.event_type,
                    severity=incident.severity or "MEDIUM",
                    description=f"Auto-mapped SIEM detection rule for {incident.event_type}",
                    status="ACTIVE",
                )
                self.db.add(rule)
                await self.db.flush()

            incident.rule_id = rule.id
            incident.rule = rule
            self.db.add(incident)
            await self.db.flush()

            # Link any sibling unmapped incidents sharing this event_type
            await self.db.execute(
                update(Incident)
                .where(Incident.event_type == incident.event_type, Incident.rule_id.is_(None))
                .values(rule_id=rule.id)
            )

        # 3. Build model-facing payload (strict allowlist - zero ground-truth leakage)
        payload_dict = build_model_facing_payload(
            incident=incident,
            rule=rule,
            events=incident.events or [],
        )

        # 4. Resolve prompt text with Level-2 SOC criteria
        prompt_service = PromptStudioService(self.db)
        prompt_text = COMMON_SOC_BASELINE
        prompt_ver_num = 1

        if rule:
            rp = await prompt_service.get_or_create_rule_prompt(rule.id)
            if rp and rp.versions:
                active_v = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])
                prompt_ver_num = active_v.version_number
                parts = [active_v.common_prompt or COMMON_SOC_BASELINE]
                if active_v.rule_specific_prompt:
                    parts.append(active_v.rule_specific_prompt)
                if active_v.tp_indicators and active_v.tp_indicators not in (active_v.rule_specific_prompt or ""):
                    parts.append(f"### TRUE POSITIVE CRITERIA (MALICIOUS ATTACK):\n{active_v.tp_indicators}")
                if active_v.fp_indicators and active_v.fp_indicators not in (active_v.rule_specific_prompt or ""):
                    parts.append(f"### FALSE POSITIVE CRITERIA (BENIGN / OPERATIONAL NOISE):\n{active_v.fp_indicators}")
                if active_v.required_evidence and active_v.required_evidence not in (active_v.rule_specific_prompt or ""):
                    parts.append(f"### REQUIRED EVIDENCE EVALUATION:\n{active_v.required_evidence}")
                if active_v.missing_info_criteria and active_v.missing_info_criteria not in (active_v.rule_specific_prompt or ""):
                    parts.append(f"### WHEN TO VOTE REQUIRES_ATTENTION:\n{active_v.missing_info_criteria}")
                prompt_text = "\n\n".join(parts)

            # In-Context Learning (Few-Shot RAG from Verified Learning History)
            lr_q = await self.db.execute(
                select(LearningRecord)
                .where(
                    (LearningRecord.rule_id == rule.id) | (LearningRecord.verification_status == "VERIFIED")
                )
                .options(selectinload(LearningRecord.incident))
                .order_by(desc(LearningRecord.feedback_timestamp))
                .limit(3)
            )
            learning_records = lr_q.scalars().all()
            if learning_records:
                few_shot_lines = ["\n\n### VERIFIED HISTORICAL PRECEDENTS (FEW-SHOT EXAMPLES):"]
                for lr in learning_records:
                    prec_title = lr.incident.title if lr.incident else "Historical Alert"
                    few_shot_lines.append(
                        f"- Precedent: {prec_title}\n"
                        f"  Verified Determination: {lr.verified_verdict}\n"
                        f"  Analyst Rationale: {lr.analyst_explanation[:250]}"
                    )
                prompt_text += "\n".join(few_shot_lines)

        rule_spec = {
            "id": rule.id if rule else (incident.rule_id or "UNKNOWN"),
            "name": rule.name if rule else incident.title,
            "severity": rule.severity if rule else incident.severity,
            "description": rule.description if rule else "",
        }

        # 5. Invoke Model Provider with resilient fallback
        if model_provider_type:
            chosen_provider_type = model_provider_type
        else:
            is_online = await self.is_local_llm_available()
            chosen_provider_type = "OPENAI_COMPATIBLE" if is_online else "SIMULATED"

        provider = get_model_provider(chosen_provider_type)

        try:
            verdict = await provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            # If OPENAI_COMPATIBLE returned an error/unreachable and fallback is permitted, switch to SIMULATED
            is_connection_error = (
                verdict.verdict == "REQUIRES_ATTENTION"
                and any(err_hint in verdict.reason.lower() for err_hint in ("connect", "exception", "failed", "offline", "degraded", "refused"))
            )
            if is_connection_error and allow_simulated_fallback:
                self.__class__._is_local_llm_online = False
                sim_provider = get_model_provider("SIMULATED")
                verdict = await sim_provider.analyze_incident(
                    incident_payload=payload_dict,
                    rule_spec=rule_spec,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )
        except Exception as exc:
            if allow_simulated_fallback:
                self.__class__._is_local_llm_online = False
                sim_provider = get_model_provider("SIMULATED")
                verdict = await sim_provider.analyze_incident(
                    incident_payload=payload_dict,
                    rule_spec=rule_spec,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )
            else:
                raise exc

        # 6. Format Structured Verdict
        verdict_data = {
            "incident_id": incident.incident_id,
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "supporting_evidence": verdict.supporting_evidence,
            "missing_evidence": verdict.missing_evidence,
            "analyst_questions": verdict.analyst_questions,
            "latency_ms": verdict.latency_ms,
            "model_identifier": verdict.model_identifier,
            "prompt_tokens": getattr(verdict, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(verdict, "completion_tokens", 0) or 0,
            "total_tokens": getattr(verdict, "total_tokens", 0) or 0,
            "is_simulated": verdict.is_simulated,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": datetime.utcnow().isoformat(),
            "evaluated_by_user": username,
        }

        # 7. Persist AI verdict to incident
        incident.ai_verdict = verdict_data
        self.db.add(incident)

        # 8. Sync with Investigation queue
        inv_q = await self.db.execute(
            select(Investigation).where(Investigation.incident_id == incident.id)
        )
        inv = inv_q.scalars().first()
        if inv and not inv.analyst_verdict:
            note_entry = f"[AI Verdict ({verdict.verdict} - {int(verdict.confidence)}%)]: {verdict.reason}"
            if inv.analyst_notes:
                inv.analyst_notes = f"{inv.analyst_notes}\n\n{note_entry}"
            else:
                inv.analyst_notes = note_entry
            inv.updated_at = datetime.utcnow()
            self.db.add(inv)

        # 9. Audit log
        audit = AuditLog(
            user_id="SYSTEM" if username in ("system", "scheduler") else username,
            username=username,
            action="AI_VERDICT_EVALUATE",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "latency_ms": verdict.latency_ms,
                "model": verdict.model_identifier,
                "is_simulated": verdict.is_simulated,
            },
        )
        self.db.add(audit)
        await self.db.commit()

        return verdict_data

    async def evaluate_batch(
        self,
        incident_ids: Optional[List[str]] = None,
        only_pending: bool = True,
        max_batch: int = 50,
        username: str = "batch_evaluator",
    ) -> Dict[str, Any]:
        """
        Evaluates a batch of incidents in sequence.
        Useful for continuous ingestion or on-demand batch evaluation.
        """
        stmt = select(Incident).options(
            selectinload(Incident.rule),
            selectinload(Incident.events),
        )

        if incident_ids and len(incident_ids) > 0:
            stmt = stmt.where(Incident.incident_id.in_(incident_ids))
        elif only_pending:
            stmt = stmt.where(Incident.ai_verdict.is_(None))

        stmt = stmt.order_by(desc(Incident.created_at_epoch), desc(Incident.created_at)).limit(max_batch)
        res = await self.db.execute(stmt)
        incidents = res.scalars().all()
        target_ids = [str(inc.incident_id or inc.id) for inc in incidents]

        results = []
        successful = 0
        failed = 0

        for iid in target_ids:
            try:
                v = await self.evaluate_incident(iid, username=username)
                results.append(v)
                successful += 1
            except Exception as e:
                failed += 1
                results.append({
                    "incident_id": iid,
                    "error": str(e),
                    "verdict": "ERROR",
                })

        return {
            "success": True,
            "total_requested": len(incidents),
            "processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
            "message": f"Evaluated {successful} incidents with AI Verdict ({failed} failures).",
        }
