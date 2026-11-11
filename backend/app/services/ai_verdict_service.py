import time
import asyncio
from datetime import datetime
from app.utils.datetime_utils import utc_now
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
from app.services.policy_governance import resolve_canonical_rule
from app.services.verdict_pipeline import (
    PipelineLLMUnavailableError,
    run_shared_verdict_pipeline,
)
from app.services.provenance import classify_execution_provenance


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
    _last_probed_base_url: Optional[str] = None
    _incident_locks: Dict[str, asyncio.Lock] = {}

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def _get_incident_lock(cls, incident_key: str) -> asyncio.Lock:
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = 0
        scoped_key = f"{loop_id}:{incident_key}"
        lock = cls._incident_locks.get(scoped_key)
        if lock is None:
            lock = asyncio.Lock()
            cls._incident_locks[scoped_key] = lock
        return lock

    @staticmethod
    def _upsert_ai_verdict_note(inv: Investigation, note_entry: str) -> None:
        """Idempotently inserts or updates automated AI Verdict note without duplicating on reevaluation."""
        if not inv or inv.analyst_verdict:
            return
        existing = inv.analyst_notes or ""
        if note_entry in existing:
            return
        lines = [line for line in existing.split("\n\n") if line.strip() and not line.strip().startswith("[AI Verdict (")]
        lines.append(note_entry)
        inv.analyst_notes = "\n\n".join(lines)
        inv.updated_at = utc_now()

    @staticmethod
    async def _assert_lock_held(db: AsyncSession, lock_key: Optional[str], lock_owner_id: Optional[str]) -> None:
        if lock_key and lock_owner_id:
            from app.services.distributed_lock import DistributedLockManager, DistributedLockLostError
            held = await DistributedLockManager.verify_or_renew(
                db, lock_key=lock_key, owner_id=lock_owner_id, ttl_seconds=120
            )
            if not held:
                await db.rollback()
                raise DistributedLockLostError(
                    f"Distributed lease lost or expired before commit for '{lock_key}' (owner={lock_owner_id})."
                )

    @classmethod
    async def is_local_llm_available(cls, force_refresh: bool = False) -> bool:
        """Checks if Server 2 LLM endpoint is reachable, caching positive status for 30s and offline status for 8s."""
        from app.services.llm_config_service import LLMConfigService
        if LLMConfigService.sync_runtime_settings():
            force_refresh = True

        current_base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        if cls._last_probed_base_url != current_base_url:
            force_refresh = True

        now = time.time()
        cache_ttl = 30.0 if cls._is_local_llm_online else 8.0
        if not force_refresh and cls._is_local_llm_online is not None and (now - cls._last_probe_time) < cache_ttl:
            return cls._is_local_llm_online

        cls._last_probe_time = now
        cls._last_probed_base_url = current_base_url
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
        only_if_pending: bool = False,
        pilot_context: Optional[Dict[str, Any]] = None,
        execution_context: str = "ANALYST_ASSISTED",
        require_autonomous_certification: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates a single incident with the LLM.
        Coordinates across intra-process coroutines and cross-process DB/Redis locks,
        auto-provisions detection rules if unmapped, formats allowlisted model telemetry,
        and saves the structured verdict to the database.
        """
        from app.services.distributed_lock import DistributedLockManager

        clean_target_id = incident_id_or_obj if isinstance(incident_id_or_obj, str) else str(getattr(incident_id_or_obj, "incident_id", None) or getattr(incident_id_or_obj, "id", ""))
        canonical_key = clean_target_id
        if not isinstance(incident_id_or_obj, str) and getattr(incident_id_or_obj, "incident_id", None):
            canonical_key = str(incident_id_or_obj.incident_id)

        pre_stmt = select(Incident.incident_id, Incident.id).where(
            (Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id)
        )
        pre_res = await self.db.execute(pre_stmt)
        pre_row = pre_res.first()
        if not pre_row:
            raise ValueError(f"Incident '{clean_target_id}' not found.")
        canonical_key = str(pre_row[0] or pre_row[1] or clean_target_id)

        inc_lock = self._get_incident_lock(canonical_key)
        async with inc_lock:
            lock_key = f"incident_triage:{canonical_key}"
            async with DistributedLockManager.acquire(
                self.db,
                lock_key=lock_key,
                ttl_seconds=120,
                acquire_timeout_seconds=30.0,
            ) as lock_owner_id:
                # Reload authoritative DB state inside locks to prevent stale snapshots or duplicate triage
                stmt = (
                    select(Incident)
                    .where((Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id))
                    .options(selectinload(Incident.rule), selectinload(Incident.events))
                    .execution_options(populate_existing=True)
                )
                res = await self.db.execute(stmt)
                incident = res.scalar_one_or_none()
                if not incident:
                    raise ValueError(f"Incident '{clean_target_id}' not found.")

                if only_if_pending and not pilot_context and isinstance(incident.ai_verdict, dict):
                    return incident.ai_verdict

                return await self._evaluate_incident_locked(
                    incident=incident,
                    username=username,
                    model_provider_type=model_provider_type,
                    allow_simulated_fallback=allow_simulated_fallback,
                    lock_key=lock_key,
                    lock_owner_id=lock_owner_id,
                    pilot_context=pilot_context,
                    execution_context=execution_context,
                    require_autonomous_certification=require_autonomous_certification,
                )

    async def _evaluate_incident_locked(
        self,
        incident: Incident,
        username: str = "system",
        model_provider_type: Optional[str] = None,
        allow_simulated_fallback: bool = False,
        lock_key: Optional[str] = None,
        lock_owner_id: Optional[str] = None,
        pilot_context: Optional[Dict[str, Any]] = None,
        execution_context: str = "ANALYST_ASSISTED",
        require_autonomous_certification: bool = False,
    ) -> Dict[str, Any]:
        """Protected single-incident evaluation execution under per-incident concurrency lock."""
        is_shadow_pilot = bool(pilot_context and str(pilot_context.get("mode", "")).upper() == "SHADOW")
        if pilot_context and str(pilot_context.get("source_type", "")).upper() == "LIVE":
            allow_simulated_fallback = False
        prev_attempts = 0
        if isinstance(incident.ai_verdict, dict):
            prev_attempts = int(incident.ai_verdict.get("reevaluation_attempts", 0) or 0)

        # 2. Auto-resolve Rule canonically if incident is unmapped
        rule = incident.rule
        if not rule and incident.event_type:
            rule = await resolve_canonical_rule(self.db, incident.event_type)

            if not rule:
                existing_sibs = (
                    await self.db.execute(select(Rule.id).where(Rule.event_type == incident.event_type))
                ).scalars().all()
                if not existing_sibs:
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

            if rule:
                incident.rule_id = rule.id
                incident.rule = rule
                self.db.add(incident)
                await self.db.flush()

                # Link unmapped siblings ONLY when event_type is globally unique in rules
                ev_count = len((await self.db.execute(select(Rule.id).where(Rule.event_type == incident.event_type))).scalars().all())
                if ev_count == 1:
                    await self.db.execute(
                        update(Incident)
                        .where(Incident.event_type == incident.event_type, Incident.rule_id.is_(None))
                        .values(rule_id=rule.id)
                    )

        # 3-6. Execute unified AIS 2.1 safeguards pipeline (Normalization -> Allowlist -> Governance
        #      -> Preflight -> Compiler -> RAG -> TokenBudget -> LLM -> Claim Grounding -> Validator -> Trust)
        from app.services.policy_simulation_service import PolicySimulationService

        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        prompt_service = PromptStudioService(self.db)
        active_v = None
        candidate_v = None
        if rule:
            rp = await prompt_service.get_or_create_rule_prompt(rule.id)
            if rp and rp.active_version_id and rp.versions:
                cand = next((v for v in rp.versions if v.id == rp.active_version_id), None)
                if cand and cand.status == "APPROVED":
                    active_v = cand
            if rp and rp.versions:
                candidate_v = rp.versions[0]

        hist_stats = await PolicySimulationService(self.db).get_rule_calibration_stats(
            rule.id if rule else None
        )

        def _set_online_state(val: bool) -> None:
            self.__class__._is_local_llm_online = val

        try:
            pipe_res = await run_shared_verdict_pipeline(
                db=self.db,
                incident=incident,
                rule=rule,
                prompt_version=candidate_v,
                active_approved_version=active_v,
                model_provider_type=model_provider_type,
                allow_simulated_fallback=allow_simulated_fallback,
                is_simulation=False,
                is_prod=is_prod,
                execution_context=execution_context,
                require_autonomous_certification=require_autonomous_certification,
                username=username,
                pilot_context=pilot_context,
                historical_stats=hist_stats,
                prev_attempts=prev_attempts,
                check_llm_available=self.is_local_llm_available,
                set_llm_online=_set_online_state,
                provider_factory=get_model_provider,
            )
        except PipelineLLMUnavailableError as llm_err:
            raise LocalLLMUnavailableError(str(llm_err)) from llm_err

        verdict_data = pipe_res.verdict_data
        norm_result = pipe_res.norm_result

        if pipe_res.early_exit:
            await self._assert_lock_held(self.db, lock_key, lock_owner_id)
            if pipe_res.early_exit_kind == "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION":
                if not is_shadow_pilot:
                    incident.ai_verdict = verdict_data
                    self.db.add(incident)
                audit = AuditLog(
                    user_id="SYSTEM" if username in ("system", "scheduler") else username,
                    username=username,
                    action="AI_VERDICT_AUTONOMOUS_BLOCKED",
                    resource_type="INCIDENT",
                    resource_id=incident.incident_id,
                    details={
                        "verdict": "REQUIRES_ATTENTION",
                        "validation_status": verdict_data.get("validation_status"),
                        "governance_reasons": verdict_data.get("governance_reasons"),
                        "reason": verdict_data.get("reason"),
                    },
                )
                self.db.add(audit)
                await self.db.commit()
                return verdict_data

            if not is_shadow_pilot:
                incident.ai_verdict = verdict_data
                self.db.add(incident)
                if pipe_res.early_exit_kind in ("POLICY_NOT_APPROVED", "PREFLIGHT_ABSTENTION"):
                    inv_q = await self.db.execute(
                        select(Investigation).where(Investigation.incident_id == incident.id)
                    )
                    inv = inv_q.scalars().first()
                    if inv and not inv.analyst_verdict:
                        note_entry = f"[AI Verdict (REQUIRES_ATTENTION - 0%)]: {verdict_data['reason']}"
                        self._upsert_ai_verdict_note(inv, note_entry)
                        self.db.add(inv)

            if pipe_res.early_exit_kind in ("POLICY_NOT_APPROVED", "PREFLIGHT_ABSTENTION"):
                audit = AuditLog(
                    user_id="SYSTEM" if username in ("system", "scheduler") else username,
                    username=username,
                    action="AI_VERDICT_EVALUATE",
                    resource_type="INCIDENT",
                    resource_id=incident.incident_id,
                    details={
                        "verdict": "REQUIRES_ATTENTION",
                        "confidence": 0.0,
                        "validation_status": verdict_data.get("validation_status"),
                        "reason": verdict_data.get("reason"),
                    },
                )
                self.db.add(audit)
            await self.db.commit()
            return verdict_data

        verdict = pipe_res.verdict_obj
        trust_res = pipe_res.trust_res
        val_res = pipe_res.val_res
        contract = pipe_res.contract
        compiled_policy = pipe_res.compiled_policy
        p_tokens = pipe_res.prompt_tokens
        c_tokens = pipe_res.completion_tokens
        t_tokens = pipe_res.total_tokens
        token_usage_source = pipe_res.token_usage_source
        final_auth_verdict = pipe_res.effective_verdict
        final_confidence_display = verdict_data["confidence"]
        final_validation_status = verdict_data["validation_status"]
        verdict_prov = pipe_res.verdict_prov

        if pilot_context:
            verdict_data["pilot_mode"] = pilot_context.get("mode")
            verdict_data["pilot_id"] = pilot_context.get("pilot_id")
            verdict_data["pilot_version"] = pilot_context.get("pilot_version")

        # Verify distributed lock lease is still owned by this worker before staging any DB writes
        await self._assert_lock_held(self.db, lock_key, lock_owner_id)

        # Persist AIS 2.1 assessment records alongside live verdict
        from app.models.verdict_intelligence import (
            EvidenceSufficiencyAssessmentRecord,
            VerdictTrustAssessmentRecord,
        )
        if trust_res.evidence_sufficiency is not None:
            suff = trust_res.evidence_sufficiency
            self.db.add(EvidenceSufficiencyAssessmentRecord(
                incident_id=incident.incident_id,
                rule_id=rule.id if rule else incident.event_type,
                archetype=suff.archetype,
                overall_sufficiency_score=suff.overall_sufficiency_score,
                required_coverage_score=suff.required_coverage_score,
                integrity_provenance_score=suff.integrity_provenance_score,
                consistency_corroboration_score=suff.consistency_corroboration_score,
                freshness_relevance_score=suff.freshness_relevance_score,
                evidence_status=suff.evidence_status.value,
                mandatory_fields_present=suff.mandatory_fields_present,
                mandatory_fields_missing=suff.mandatory_fields_missing,
                conditional_fields_evaluated=suff.conditional_fields_evaluated,
                optional_enrichment_present=suff.optional_enrichment_present,
                unsupported_fields_requested=suff.unsupported_fields_requested,
                contradictions_detected=suff.contradictions_detected,
                evaluated_at=utc_now(),
            ))

        self.db.add(VerdictTrustAssessmentRecord(
            incident_id=incident.incident_id,
            rule_id=rule.id if rule else incident.event_type,
            archetype=trust_res.archetype,
            suggested_verdict=trust_res.suggested_verdict,
            effective_verdict=trust_res.effective_verdict.value,
            trust_score=trust_res.trust_score,
            raw_trust_score=trust_res.raw_trust_score,
            evidence_sufficiency_score=trust_res.evidence_sufficiency_score,
            evidence_status=trust_res.evidence_status.value,
            score_dimensions=trust_res.score_dimensions.model_dump(),
            supporting_evidence=trust_res.supporting_evidence,
            contradictory_evidence=trust_res.contradictory_evidence,
            missing_evidence=trust_res.missing_evidence,
            confidence_limitations=trust_res.confidence_limitations,
            historical_validation_status=trust_res.historical_validation_status,
            is_calibrated=trust_res.is_calibrated,
            applicable_policy_version=compiled_policy.version_number,
            applicable_contract_version=contract.status,
            escalation_reason=str(trust_res.escalation_reason)[:256] if trust_res.escalation_reason else None,
            human_readable_explanation=trust_res.human_readable_explanation,
            model_identifier=verdict.model_identifier,
            is_simulated=verdict.is_simulated,
            evaluated_at=utc_now(),
        ))

        # 7. Persist AI verdict to incident (unless SHADOW pilot mode keeps authoritative incident clean)
        if not is_shadow_pilot:
            incident.ai_verdict = verdict_data
            self.db.add(incident)

        # 7b. Persist bifurcated TokenUsageRecord on Server 1 for analytics (records authoritative outcome)
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
            timestamp=utc_now(),
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "token_usage_source": token_usage_source,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
            },
        )
        self.db.add(token_usage_entry)

        # 7c. Persist Historical Telemetry Timeline milestone on Server 1 with authoritative verdict
        from app.models.telemetry_timeline import TelemetryTimelineRecord
        timeline_entry = TelemetryTimelineRecord(
            incident_id=incident.incident_id,
            event_type="AGENT_TRIAGE_EVALUATED",
            stage="TRIAGE",
            summary=f"Verdict Triage Agent evaluated incident: {final_auth_verdict} ({int(final_confidence_display)}% confidence, trust={trust_res.trust_score}/10)",
            source="Verdict Triage Agent (Server 2 Inference)",
            severity=incident.severity,
            source_ip=incident.source_ip,
            reporting_device=incident.reporting_device,
            epoch_ms=int(time.time() * 1000),
            token_count=t_tokens,
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "validation_status": final_validation_status,
                "model": verdict.model_identifier,
                "latency_ms": verdict.latency_ms,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
            },
        )
        self.db.add(timeline_entry)

        # 8. Sync with Investigation queue using authoritative validated verdict (idempotent; skipped in SHADOW pilot mode)
        if not is_shadow_pilot:
            inv_q = await self.db.execute(
                select(Investigation).where(Investigation.incident_id == incident.id)
            )
            inv = inv_q.scalars().first()
            if inv and not inv.analyst_verdict:
                note_entry = f"[AI Verdict ({final_auth_verdict} - {int(final_confidence_display)}%)]: {verdict_data['reason']}"
                self._upsert_ai_verdict_note(inv, note_entry)
                self.db.add(inv)

        # 9. Audit log with authoritative outcome and model proposal provenance
        audit = AuditLog(
            user_id="SYSTEM" if username in ("system", "scheduler") else username,
            username=username,
            action="AI_VERDICT_EVALUATE",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "validation_status": final_validation_status,
                "latency_ms": verdict.latency_ms,
                "model": verdict.model_identifier,
                "is_simulated": verdict.is_simulated,
                "execution_provenance": verdict_prov["execution_provenance"],
                "configured_provider": verdict_prov["configured_provider"],
                "test_environment": verdict_prov["test_environment"],
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
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        allow_mock = False if is_prod else (allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False))
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
            # If flagged offline from a failure, verify if recovered before continuing batch
            if self.__class__._is_local_llm_online is False:
                if not await self.is_local_llm_available(force_refresh=True) and not allow_mock:
                    print(f"[Batch AI Verdict] Local LLM is offline at incident {iid}. Stopping batch.")
                    break

            try:
                v = await self.evaluate_incident(
                    iid,
                    username=username,
                    allow_simulated_fallback=allow_mock,
                    only_if_pending=only_pending,
                )
                await self.db.commit()
                results.append(v)
                successful += 1
                await asyncio.sleep(0.15)
            except Exception as e:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
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
        include_reevaluation_eligible: bool = False,
        rule_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reconciles pending triage incidents lacking an AI verdict, plus bounded
        reevaluation of recoverable abstentions (e.g., POLICY_NOT_APPROVED once
        a rule policy is approved) when include_reevaluation_eligible=True.
        If Local LLM is offline or goes offline mid-batch, halts immediately.
        """
        from app.services.llm_config_service import LLMConfigService
        LLMConfigService.sync_runtime_settings()
        is_online = await self.is_local_llm_available(force_refresh=True)
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        allow_mock = False if is_prod else getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        pending_total = await self.get_pending_incident_count()

        # Query pending incident IDs chronologically
        stmt = (
            select(Incident.incident_id)
            .where(Incident.ai_verdict.is_(None))
            .order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc())
            .limit(max_batch)
        )
        if rule_id:
            stmt = stmt.where(Incident.rule_id == rule_id)
        res = await self.db.execute(stmt)
        pending_ids = list(res.scalars().all())

        # Bounded discovery of reevaluation-eligible deferred incidents
        if include_reevaluation_eligible and len(pending_ids) < max_batch:
            rem_cap = max_batch - len(pending_ids)
            re_q = select(Incident).where(Incident.ai_verdict.isnot(None))
            if rule_id:
                re_q = re_q.where(Incident.rule_id == rule_id)
            re_q = re_q.order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc()).limit(rem_cap * 3)
            re_res = await self.db.execute(re_q)
            for inc_obj in re_res.scalars().all():
                if len(pending_ids) >= max_batch:
                    break
                av = inc_obj.ai_verdict
                if isinstance(av, dict) and av.get("reevaluation_eligible") is True and int(av.get("reevaluation_attempts", 0) or 0) < 3:
                    iid = str(inc_obj.incident_id)
                    if iid not in pending_ids:
                        pending_ids.append(iid)

        if not is_online and not allow_mock:
            return {
                "success": False,
                "is_llm_online": False,
                "message": f"Local LLM (Server 2) is currently offline. {pending_total} incidents pending in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": pending_total,
            }

        if not pending_ids:
            return {
                "success": True,
                "is_llm_online": True,
                "message": "All incidents have AI verdicts. No pending incidents in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": 0,
            }

        processed_count = 0
        failed_count = 0

        for iid in pending_ids:
            # If flagged offline from a failure, verify if recovered before processing incident
            if self.__class__._is_local_llm_online is False:
                if not await self.is_local_llm_available(force_refresh=True) and not allow_mock:
                    print(f"[LLM Backlog Processor] Local LLM is offline at incident {iid}. Halting processing.")
                    break

            try:
                await self.evaluate_incident(
                    iid,
                    username=username,
                    allow_simulated_fallback=allow_mock,
                    only_if_pending=not include_reevaluation_eligible,
                )
                await self.db.commit()
                processed_count += 1
                if pause_between_s > 0:
                    await asyncio.sleep(pause_between_s)
            except Exception as exc:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
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

