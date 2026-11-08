import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, or_, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.incident import Incident
from app.models.rule import Rule
from app.models.learning import LearningRecord
from app.models.investigation import Investigation
from app.models.audit import AuditLog
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.factory import get_model_provider
from app.services.prompt_studio_service import PromptStudioService, COMMON_SOC_BASELINE


class LocalLLMUnavailableError(Exception):
    """Raised when Server 2 Local LLM is offline or unreachable."""
    pass


class VerdictTriageAgent:
    """
    Agentic SOC Verdict Triage Agent.
    Executes zero-bias incident evaluations with strict ground-truth isolation,
    dynamic prompt synthesis (Level-2 SOC criteria + few-shot RAG),
    and resilient model provider fallback.
    """

    _last_probe_time: float = 0.0
    _is_local_llm_online: Optional[bool] = None

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    async def is_local_llm_available(cls, force_refresh: bool = False) -> bool:
        """Checks if Server 2 LLM endpoint is reachable, caching result for 15s."""
        now = time.time()
        if not force_refresh and cls._is_local_llm_online is not None and (now - cls._last_probe_time) < 15.0:
            return cls._is_local_llm_online

        cls._last_probe_time = now
        provider = get_model_provider("OPENAI_COMPATIBLE")
        try:
            health = await provider.get_health()
            cls._is_local_llm_online = (health.status == "HEALTHY")
        except Exception:
            cls._is_local_llm_online = False
        return cls._is_local_llm_online

    async def get_pending_incident_count(self) -> int:
        """Returns the number of incidents currently awaiting an AI verdict."""
        res = await self.db.execute(
            select(func.count(Incident.id)).where(Incident.ai_verdict.is_(None))
        )
        return res.scalar() or 0

    async def evaluate_incident(
        self,
        incident_id_or_obj: Union[str, Incident],
        username: str = "system",
        model_provider_type: Optional[str] = None,
        allow_simulated_fallback: bool = False,
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

        # 5. Invoke Model Provider with strict offline enforcement
        allow_mock = allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        if model_provider_type:
            chosen_provider_type = model_provider_type
        else:
            is_online = await self.is_local_llm_available()
            if not is_online:
                if allow_mock:
                    chosen_provider_type = "SIMULATED"
                else:
                    raise LocalLLMUnavailableError(
                        "Local LLM (Server 2) is currently offline. AI verdict generation is deferred until Local LLM comes online."
                    )
            else:
                chosen_provider_type = "OPENAI_COMPATIBLE"

        provider = get_model_provider(chosen_provider_type)

        try:
            verdict = await provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            # If OPENAI_COMPATIBLE returned an error/unreachable
            is_connection_error = (
                verdict.verdict == "REQUIRES_ATTENTION"
                and any(err_hint in verdict.reason.lower() for err_hint in ("connect", "exception", "failed", "offline", "degraded", "refused"))
            )
            if is_connection_error:
                self.__class__._is_local_llm_online = False
                if allow_mock:
                    sim_provider = get_model_provider("SIMULATED")
                    verdict = await sim_provider.analyze_incident(
                        incident_payload=payload_dict,
                        rule_spec=rule_spec,
                        prompt_text=prompt_text,
                        prompt_version_number=prompt_ver_num,
                    )
                else:
                    raise LocalLLMUnavailableError(f"Local LLM connection error: {verdict.reason}")
        except Exception as exc:
            self.__class__._is_local_llm_online = False
            if allow_mock and not isinstance(exc, LocalLLMUnavailableError):
                sim_provider = get_model_provider("SIMULATED")
                verdict = await sim_provider.analyze_incident(
                    incident_payload=payload_dict,
                    rule_spec=rule_spec,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )
            else:
                if isinstance(exc, LocalLLMUnavailableError):
                    raise exc
                raise LocalLLMUnavailableError(f"Local LLM inference failed: {str(exc)}") from exc

        p_tokens = getattr(verdict, "prompt_tokens", 0) or 0
        c_tokens = getattr(verdict, "completion_tokens", 0) or 0
        t_tokens = getattr(verdict, "total_tokens", 0) or (p_tokens + c_tokens)
        if t_tokens == 0:
            p_tokens = max(50, len(prompt_text) // 4)
            c_tokens = max(20, len(verdict.reason) // 4)
            t_tokens = p_tokens + c_tokens

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
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": t_tokens,
            "is_simulated": verdict.is_simulated,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": datetime.utcnow().isoformat(),
            "evaluated_by_user": username,
        }

        # 7. Persist AI verdict to incident
        incident.ai_verdict = verdict_data
        self.db.add(incident)

        # 7b. Persist bifurcated TokenUsageRecord on Server 1 for analytics
        from app.models.token_usage import TokenUsageRecord
        token_usage_entry = TokenUsageRecord(
            process_type="INCIDENT_TRIAGE",
            process_id=incident.incident_id,
            incident_id=incident.incident_id,
            rule_id=rule.rule_id if rule else incident.event_type,
            model_identifier=verdict.model_identifier,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=t_tokens,
            latency_ms=verdict.latency_ms,
            is_simulated=verdict.is_simulated,
            executed_by_user=username,
            timestamp=datetime.utcnow(),
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
            },
        )
        self.db.add(token_usage_entry)

        # 7c. Persist Historical Telemetry Timeline milestone on Server 1
        from app.models.telemetry_timeline import TelemetryTimelineRecord
        timeline_entry = TelemetryTimelineRecord(
            incident_id=incident.incident_id,
            event_type="AGENT_TRIAGE_EVALUATED",
            stage="TRIAGE",
            summary=f"Verdict Triage Agent evaluated incident: {verdict.verdict} ({int(verdict.confidence)}% confidence)",
            source="Verdict Triage Agent (Server 2 Inference)",
            severity=incident.severity,
            source_ip=incident.source_ip,
            reporting_device=incident.reporting_device,
            epoch_ms=int(time.time() * 1000),
            token_count=t_tokens,
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "model": verdict.model_identifier,
                "latency_ms": verdict.latency_ms,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
            },
        )
        self.db.add(timeline_entry)

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
        allow_simulated_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates a batch of incidents in sequence.
        Halts immediately if the Local LLM is offline, leaving incidents pending.
        """
        is_online = await self.is_local_llm_available()
        allow_mock = allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        if not is_online and not allow_mock:
            pending_count = await self.get_pending_incident_count()
            return {
                "success": False,
                "total_requested": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "message": f"Local LLM (Server 2) is currently offline. {pending_count} incidents remain queued.",
            }

        stmt = select(Incident).options(
            selectinload(Incident.rule),
            selectinload(Incident.events),
        )

        if incident_ids and len(incident_ids) > 0:
            stmt = stmt.where(Incident.incident_id.in_(incident_ids))
        elif only_pending:
            stmt = stmt.where(Incident.ai_verdict.is_(None))

        stmt = stmt.order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc()).limit(max_batch)
        res = await self.db.execute(stmt)
        incidents = res.scalars().all()
        target_ids = [str(inc.incident_id or inc.id) for inc in incidents]

        results = []
        successful = 0
        failed = 0

        for iid in target_ids:
            # Check LLM online status before processing each incident
            if not await self.is_local_llm_available() and not allow_mock:
                print(f"[Batch AI Verdict] Local LLM went offline at incident {iid}. Stopping batch.")
                break

            try:
                v = await self.evaluate_incident(iid, username=username, allow_simulated_fallback=allow_mock)
                await self.db.commit()
                results.append(v)
                successful += 1
                await asyncio.sleep(0.15)
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

    async def reconcile_pending_triage(
        self,
        max_batch: int = 100,
        username: str = "llm_backlog_worker",
        pause_between_s: float = 0.15,
    ) -> Dict[str, Any]:
        """
        Reconciles pending triage incidents lacking an AI verdict. Once Local LLM is
        online, processes them one by one sequentially with the Verdict Triage Agent.
        If Local LLM is offline or goes offline mid-batch, halts immediately.
        """
        is_online = await self.is_local_llm_available(force_refresh=True)
        allow_mock = getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        pending_total = await self.get_pending_incident_count()

        if not is_online and not allow_mock:
            return {
                "success": False,
                "is_llm_online": False,
                "message": f"Local LLM (Server 2) is currently offline. {pending_total} incidents pending in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": pending_total,
            }

        if pending_total == 0:
            return {
                "success": True,
                "is_llm_online": True,
                "message": "All incidents have AI verdicts. No pending incidents in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": 0,
            }

        # Query pending incident IDs chronologically
        stmt = (
            select(Incident.incident_id)
            .where(Incident.ai_verdict.is_(None))
            .order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc())
            .limit(max_batch)
        )
        res = await self.db.execute(stmt)
        pending_ids = res.scalars().all()

        processed_count = 0
        failed_count = 0

        for iid in pending_ids:
            # Re-check LLM availability before each individual incident
            if not await self.is_local_llm_available() and not allow_mock:
                print(f"[LLM Backlog Processor] Local LLM went offline at incident {iid}. Halting processing.")
                break

            try:
                await self.evaluate_incident(iid, username=username, allow_simulated_fallback=allow_mock)
                await self.db.commit()
                processed_count += 1
                if pause_between_s > 0:
                    await asyncio.sleep(pause_between_s)
            except Exception as exc:
                failed_count += 1
                print(f"[LLM Backlog Processor] Error evaluating incident {iid}: {exc}")

        remaining = await self.get_pending_incident_count()
        return {
            "success": True,
            "is_llm_online": True,
            "processed": processed_count,
            "failed": failed_count,
            "pending_remaining": remaining,
            "message": f"Processed {processed_count} pending incidents one by one ({remaining} remaining).",
        }

    # Backward compatibility alias
    process_pending_incidents = reconcile_pending_triage


# Backward compatibility alias
AIVerdictService = VerdictTriageAgent

