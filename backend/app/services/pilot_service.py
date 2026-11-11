import asyncio
import hashlib
import json
import logging
import math
import time
import uuid
from datetime import datetime, timedelta
from app.utils.datetime_utils import utc_now
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.audit import AuditLog
from app.models.incident import HistoricalGroundTruth, Incident
from app.models.investigation import Investigation
from app.models.pilot import PilotConfigHistory, PilotConfiguration, PilotEvaluationRecord
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.task_queue import QueuedTask
from app.schemas.pilot import (
    PilotActivateRequest,
    PilotBatchRunRequest,
    PilotConfigUpdateRequest,
    PilotFeedbackRequest,
    PilotMode,
    PilotSupervisorVerifyRequest,
)
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.audit_service import AuditService, compute_audit_signature
from app.services.provenance import classify_endpoint_status, classify_execution_provenance
from app.services.distributed_lock import DistributedLockManager
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.gpu_manager import gpu_workload_manager
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine

logger = logging.getLogger("ai_verdict.pilot")


class PilotService:
    """
    Controlled SOC Pilot Orchestration, Safety Governance & Telemetry Service (Phase 9).
    Supports DISABLED, SHADOW, and ANALYST_ASSISTED modes with strict human authority,
    zero external SIEM writeback, zero autonomous incident closure, and full audit provenance.
    """

    _consecutive_errors: int = 0

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _config_to_snapshot(cfg: PilotConfiguration) -> Dict[str, Any]:
        return {
            "id": cfg.id,
            "pilot_name": cfg.pilot_name,
            "description": cfg.description,
            "version_number": cfg.version_number,
            "mode": cfg.mode,
            "is_paused": cfg.is_paused,
            "selected_rule_ids": list(cfg.selected_rule_ids or []),
            "selected_archetypes": list(cfg.selected_archetypes or []),
            "included_severities": list(cfg.included_severities or []),
            "ingestion_source": cfg.ingestion_source,
            "daily_evaluation_budget": cfg.daily_evaluation_budget,
            "hourly_evaluation_budget": cfg.hourly_evaluation_budget,
            "max_concurrent_inference": cfg.max_concurrent_inference,
            "request_timeout_seconds": cfg.request_timeout_seconds,
            "require_analyst_review": cfg.require_analyst_review,
            "require_approved_policy": cfg.require_approved_policy,
            "allow_external_writeback": False,
            "allow_auto_incident_closure": False,
            "error_handling_policy": cfg.error_handling_policy,
            "consecutive_error_pause_threshold": cfg.consecutive_error_pause_threshold,
            "reporting_schedule": cfg.reporting_schedule,
        }

    async def get_or_create_config(self) -> PilotConfiguration:
        res = await self.db.execute(
            select(PilotConfiguration)
            .where(PilotConfiguration.is_active_config == True)
            .order_by(desc(PilotConfiguration.updated_at))
            .limit(1)
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            return cfg

        cfg = PilotConfiguration(
            pilot_name="Default SOC Pilot",
            description="Controlled SOC Pilot (Disabled by default until explicitly activated by Admin/SOC Lead).",
            version_number=1,
            is_active_config=True,
            mode=PilotMode.DISABLED.value,
            is_paused=False,
            selected_rule_ids=[],
            selected_archetypes=[],
            included_severities=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            ingestion_source="ALL",
            daily_evaluation_budget=500,
            hourly_evaluation_budget=100,
            max_concurrent_inference=2,
            request_timeout_seconds=float(getattr(settings, "LOCAL_LLM_TIMEOUT", 60.0) or 60.0),
            require_analyst_review=True,
            require_approved_policy=True,
            allow_external_writeback=False,
            allow_auto_incident_closure=False,
            error_handling_policy="ABSTAIN_AND_LOG",
            consecutive_error_pause_threshold=5,
            reporting_schedule="HOURLY",
            created_by="system",
            updated_by="system",
        )
        self.db.add(cfg)
        await self.db.flush()

        hist = PilotConfigHistory(
            pilot_id=cfg.id,
            version_number=1,
            action="PILOT_INITIALIZED",
            mode=cfg.mode,
            is_paused=cfg.is_paused,
            config_snapshot=self._config_to_snapshot(cfg),
            change_reason="Initial safe default configuration (DISABLED)",
            changed_by="system",
        )
        self.db.add(hist)
        await self.db.commit()
        await self.db.refresh(cfg)
        return cfg

    async def _record_history_and_audit(
        self,
        cfg: PilotConfiguration,
        action: str,
        actor: str,
        reason: str,
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        snap = self._config_to_snapshot(cfg)
        hist = PilotConfigHistory(
            pilot_id=cfg.id,
            version_number=cfg.version_number,
            action=action,
            mode=cfg.mode,
            is_paused=cfg.is_paused,
            config_snapshot=snap,
            change_reason=reason,
            changed_by=actor,
        )
        self.db.add(hist)
        await self.db.flush()

        details = {"version": cfg.version_number, "mode": cfg.mode, "is_paused": cfg.is_paused, "reason": reason}
        if extra_details:
            details.update(extra_details)

        audit = AuditService(self.db)
        await audit.log(
            action=action,
            user_id=actor,
            username=actor,
            entity_type="PILOT_CONFIG",
            entity_id=cfg.id,
            details=details,
        )

    async def update_config(self, req: PilotConfigUpdateRequest, actor: str) -> PilotConfiguration:
        cfg = await self.get_or_create_config()
        cfg.pilot_name = req.pilot_name.strip()
        cfg.description = req.description.strip()
        cfg.mode = req.mode.value
        if cfg.mode == PilotMode.DISABLED.value:
            cfg.is_paused = False
        cfg.selected_rule_ids = [str(r).strip() for r in req.selected_rule_ids if str(r).strip()]
        cfg.selected_archetypes = [str(a).strip().upper() for a in req.selected_archetypes if str(a).strip()]
        cfg.included_severities = list(req.included_severities)
        cfg.ingestion_source = req.ingestion_source.value
        cfg.daily_evaluation_budget = req.daily_evaluation_budget
        cfg.hourly_evaluation_budget = req.hourly_evaluation_budget
        cfg.max_concurrent_inference = req.max_concurrent_inference
        cfg.request_timeout_seconds = req.request_timeout_seconds
        cfg.require_analyst_review = bool(req.require_analyst_review)
        cfg.require_approved_policy = bool(req.require_approved_policy)
        cfg.allow_external_writeback = False
        cfg.allow_auto_incident_closure = False
        cfg.error_handling_policy = req.error_handling_policy
        cfg.consecutive_error_pause_threshold = req.consecutive_error_pause_threshold
        cfg.reporting_schedule = req.reporting_schedule
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()

        self.db.add(cfg)
        await self._record_history_and_audit(cfg, "PILOT_CONFIG_UPDATED", actor, req.change_reason)
        await self.db.refresh(cfg)
        return cfg

    async def activate_pilot(self, req: PilotActivateRequest, actor: str) -> PilotConfiguration:
        cfg = await self.get_or_create_config()
        if req.mode == PilotMode.DISABLED:
            return await self.disable_pilot(req.change_reason, actor)

        cfg.mode = req.mode.value
        cfg.is_paused = False
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()
        PilotService._consecutive_errors = 0
        self.db.add(cfg)
        await self._record_history_and_audit(cfg, f"PILOT_ACTIVATED_{cfg.mode}", actor, req.change_reason)
        await self.db.refresh(cfg)
        return cfg

    async def pause_pilot(self, reason: str, actor: str) -> PilotConfiguration:
        cfg = await self.get_or_create_config()
        cfg.is_paused = True
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()
        self.db.add(cfg)
        await self._record_history_and_audit(cfg, "PILOT_PAUSED", actor, reason)
        await self.db.refresh(cfg)
        return cfg

    async def resume_pilot(self, reason: str, actor: str) -> PilotConfiguration:
        cfg = await self.get_or_create_config()
        if cfg.mode == PilotMode.DISABLED.value:
            raise ValueError("Cannot resume a DISABLED pilot. Activate SHADOW or ANALYST_ASSISTED mode first.")
        cfg.is_paused = False
        PilotService._consecutive_errors = 0
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()
        self.db.add(cfg)
        await self._record_history_and_audit(cfg, "PILOT_RESUMED", actor, reason)
        await self.db.refresh(cfg)
        return cfg

    async def disable_pilot(self, reason: str, actor: str) -> PilotConfiguration:
        """
        Safely disables the pilot without deleting any analyst decisions, verdicts,
        audit logs, evaluation records, or historical incident data.
        """
        cfg = await self.get_or_create_config()
        prev_mode = cfg.mode
        cfg.mode = PilotMode.DISABLED.value
        cfg.is_paused = False
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()
        self.db.add(cfg)
        await self._record_history_and_audit(
            cfg,
            "PILOT_DISABLED",
            actor,
            reason,
            extra_details={"previous_mode": prev_mode, "data_preserved": True},
        )
        await self.db.refresh(cfg)
        return cfg

    async def rollback_config(self, target_version: int, reason: str, actor: str) -> PilotConfiguration:
        cfg = await self.get_or_create_config()
        res = await self.db.execute(
            select(PilotConfigHistory)
            .where(
                PilotConfigHistory.pilot_id == cfg.id,
                PilotConfigHistory.version_number == target_version,
            )
            .order_by(desc(PilotConfigHistory.changed_at))
            .limit(1)
        )
        target_hist = res.scalar_one_or_none()
        if not target_hist:
            raise ValueError(f"Pilot configuration version {target_version} not found.")

        snap = target_hist.config_snapshot or {}
        cfg.pilot_name = snap.get("pilot_name", cfg.pilot_name)
        cfg.description = snap.get("description", cfg.description)
        cfg.mode = snap.get("mode", PilotMode.DISABLED.value)
        cfg.is_paused = bool(snap.get("is_paused", False))
        cfg.selected_rule_ids = list(snap.get("selected_rule_ids") or [])
        cfg.selected_archetypes = list(snap.get("selected_archetypes") or [])
        cfg.included_severities = list(snap.get("included_severities") or ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        cfg.ingestion_source = snap.get("ingestion_source", "ALL")
        cfg.daily_evaluation_budget = int(snap.get("daily_evaluation_budget", 500))
        cfg.hourly_evaluation_budget = int(snap.get("hourly_evaluation_budget", 100))
        cfg.max_concurrent_inference = int(snap.get("max_concurrent_inference", 2))
        cfg.request_timeout_seconds = float(snap.get("request_timeout_seconds", 60.0))
        cfg.require_analyst_review = bool(snap.get("require_analyst_review", True))
        cfg.require_approved_policy = bool(snap.get("require_approved_policy", True))
        cfg.allow_external_writeback = False
        cfg.allow_auto_incident_closure = False
        cfg.error_handling_policy = snap.get("error_handling_policy", "ABSTAIN_AND_LOG")
        cfg.consecutive_error_pause_threshold = int(snap.get("consecutive_error_pause_threshold", 5))
        cfg.reporting_schedule = snap.get("reporting_schedule", "HOURLY")
        cfg.version_number += 1
        cfg.updated_by = actor
        cfg.updated_at = utc_now()

        self.db.add(cfg)
        await self._record_history_and_audit(
            cfg,
            "PILOT_CONFIG_ROLLED_BACK",
            actor,
            reason,
            extra_details={"rolled_back_to_version": target_version, "data_preserved": True},
        )
        await self.db.refresh(cfg)
        return cfg

    async def get_history(self, limit: int = 50) -> List[PilotConfigHistory]:
        cfg = await self.get_or_create_config()
        res = await self.db.execute(
            select(PilotConfigHistory)
            .where(PilotConfigHistory.pilot_id == cfg.id)
            .order_by(desc(PilotConfigHistory.version_number), desc(PilotConfigHistory.changed_at))
            .limit(limit)
        )
        return list(res.scalars().all())

    async def _get_budget_usage(self, pilot_id: str) -> Tuple[int, int]:
        now = utc_now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)

        q_hr = await self.db.execute(
            select(func.count(PilotEvaluationRecord.id)).where(
                PilotEvaluationRecord.pilot_id == pilot_id,
                PilotEvaluationRecord.eligibility_status == "EVALUATED",
                PilotEvaluationRecord.created_at >= hour_ago,
            )
        )
        q_day = await self.db.execute(
            select(func.count(PilotEvaluationRecord.id)).where(
                PilotEvaluationRecord.pilot_id == pilot_id,
                PilotEvaluationRecord.eligibility_status == "EVALUATED",
                PilotEvaluationRecord.created_at >= day_ago,
            )
        )
        return int(q_hr.scalar() or 0), int(q_day.scalar() or 0)

    async def check_incident_eligibility(
        self,
        cfg: PilotConfiguration,
        incident: Incident,
        rule: Optional[Rule],
        archetype: str,
        source_type: str = "LIVE",
    ) -> Tuple[bool, Optional[str]]:
        if cfg.mode == PilotMode.DISABLED.value:
            return False, "PILOT_DISABLED"
        if cfg.is_paused:
            return False, "PILOT_PAUSED"

        if cfg.ingestion_source != "ALL" and cfg.ingestion_source != source_type.upper():
            return False, f"SOURCE_EXCLUDED:{source_type}"

        selected_rules = set(cfg.selected_rule_ids or [])
        if selected_rules:
            rule_candidates = {str(incident.rule_id or ""), str(incident.event_type or "")}
            if rule:
                rule_candidates.update({str(rule.id), str(rule.rule_id), str(rule.event_type)})
            if not selected_rules.intersection(rule_candidates):
                return False, "RULE_NOT_IN_PILOT_SCOPE"

        selected_archs = {str(a).upper() for a in (cfg.selected_archetypes or [])}
        if selected_archs and archetype.upper() not in selected_archs:
            return False, f"ARCHETYPE_NOT_IN_PILOT_SCOPE:{archetype}"

        inc_sev = str(incident.severity or "MEDIUM").upper()
        allowed_sevs = {str(s).upper() for s in (cfg.included_severities or [])}
        if allowed_sevs and inc_sev not in allowed_sevs:
            return False, f"SEVERITY_EXCLUDED:{inc_sev}"

        hr_used, day_used = await self._get_budget_usage(cfg.id)
        if hr_used >= cfg.hourly_evaluation_budget:
            return False, "HOURLY_BUDGET_EXCEEDED"
        if day_used >= cfg.daily_evaluation_budget:
            return False, "DAILY_BUDGET_EXCEEDED"

        return True, None

    async def evaluate_incident_for_pilot(
        self,
        incident_id: str,
        source_type: str = "LIVE",
        actor: str = "pilot_worker",
        allow_simulated: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes controlled pilot triage for one incident reusing VerdictTriageAgent.
        - Never uses simulated fallback for LIVE jobs.
        - Never auto-closes incidents or writes back to FortiSIEM.
        - Preserves per-incident idempotency and distributed locking.
        """
        cfg = await self.get_or_create_config()
        if cfg.mode == PilotMode.DISABLED.value:
            return {"status": "SKIPPED", "reason": "PILOT_DISABLED", "incident_id": incident_id}
        if cfg.is_paused:
            return {"status": "SKIPPED", "reason": "PILOT_PAUSED", "incident_id": incident_id}

        clean_source = source_type.upper().strip()
        if clean_source == "LIVE":
            allow_simulated = False

        inc_res = await self.db.execute(
            select(Incident)
            .where((Incident.incident_id == incident_id) | (Incident.id == incident_id))
            .options(selectinload(Incident.rule), selectinload(Incident.events))
        )
        inc = inc_res.scalar_one_or_none()
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found.")

        rule = inc.rule
        from app.services.policy_governance import resolve_canonical_rule

        if not rule and inc.event_type:
            rule = await resolve_canonical_rule(self.db, inc.event_type)

        archetype = "UNKNOWN"
        if rule:
            snap_res = await self.db.execute(
                select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
            )
            snap = snap_res.scalars().first()
            if snap and snap.primary_archetype:
                archetype = snap.primary_archetype

        eligible, reason = await self.check_incident_eligibility(cfg, inc, rule, archetype, source_type=clean_source)
        if not eligible:
            return {"status": "SKIPPED", "reason": reason, "incident_id": inc.incident_id}

        idem_key = f"{cfg.id}:{cfg.mode}:{inc.incident_id}"
        existing_res = await self.db.execute(
            select(PilotEvaluationRecord).where(PilotEvaluationRecord.idempotency_key == idem_key)
        )
        existing = existing_res.scalar_one_or_none()
        if existing and existing.eligibility_status in ("EVALUATED", "ABSTAINED"):
            return {
                "status": "IDEMPOTENT_SKIP",
                "evaluation_id": existing.id,
                "incident_id": inc.incident_id,
                "validated_verdict": existing.validated_verdict,
                "execution_mode": existing.execution_mode,
            }

        norm = EvidenceNormalizationService.normalize_incident_evidence(inc, inc.events or [])
        ev_hash = hashlib.sha256(
            json.dumps([r.model_dump() for r in norm.records], sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        # Resolve active approved policy metadata for provenance
        policy_version_id = None
        policy_version_number = None
        policy_digest = None
        if rule:
            rp_res = await self.db.execute(
                select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
            )
            rp = rp_res.scalars().first()
            if rp and rp.active_version_id and rp.versions:
                act_v = next((v for v in rp.versions if v.id == rp.active_version_id and v.status == "APPROVED"), None)
                if act_v:
                    policy_version_id = act_v.id
                    policy_version_number = act_v.version_number
                    policy_digest = PolicyQualityValidator.compute_policy_digest(act_v)

        # Snapshot scalar attributes before entering try/rollback blocks to avoid AsyncSession expired-attribute errors
        pilot_id = str(cfg.id)
        pilot_version = int(cfg.version_number)
        pilot_mode = str(cfg.mode)
        err_policy = str(cfg.error_handling_policy)
        err_thresh = int(cfg.consecutive_error_pause_threshold)
        inc_id = str(inc.incident_id)
        inc_db_id = str(inc.id)
        inc_sev = str(inc.severity or "MEDIUM")
        rule_id_str = str(rule.rule_id if rule else (inc.rule_id or inc.event_type))
        req_timeout = float(cfg.request_timeout_seconds)
        requires_autonomous = bool(
            cfg.allow_auto_incident_closure
            or cfg.allow_external_writeback
            or str(pilot_mode).upper() in ("AUTONOMOUS", "FULL_AUTO", "AUTO_RESPONSE")
        )

        from app.services.ai_verdict_service import LocalLLMUnavailableError, VerdictTriageAgent

        triage_agent = VerdictTriageAgent(self.db)
        lock_key = f"pilot_eval:{pilot_id}:{inc_id}"
        async with DistributedLockManager.acquire(self.db, lock_key=lock_key, ttl_seconds=120, acquire_timeout_seconds=15.0):
            try:
                verdict_data = await triage_agent.evaluate_incident(
                    incident_id_or_obj=inc_id,
                    username=actor,
                    allow_simulated_fallback=allow_simulated,
                    execution_context=("AUTONOMOUS" if requires_autonomous else "ANALYST_ASSISTED"),
                    require_autonomous_certification=requires_autonomous,
                    pilot_context={
                        "pilot_id": pilot_id,
                        "pilot_version": pilot_version,
                        "mode": pilot_mode,
                        "source_type": clean_source,
                        "request_timeout_seconds": req_timeout,
                    },
                )
                PilotService._consecutive_errors = 0

                val_status = str(verdict_data.get("validation_status") or "VALIDATED")
                eff_verdict = str(verdict_data.get("verdict") or "REQUIRES_ATTENTION")
                elig_status = "ABSTAINED" if eff_verdict == "REQUIRES_ATTENTION" and val_status in (
                    "POLICY_NOT_APPROVED",
                    "POLICY_NOT_EMPIRICALLY_CERTIFIED",
                    "INSUFFICIENT_EVIDENCE",
                    "CONTEXT_WINDOW_EXCEEDED",
                    "GUARDRAIL_ABSTAINED",
                    "INVALID_MODEL_OUTPUT",
                    "REJECTED",
                ) else "EVALUATED"

                existing_res2 = await self.db.execute(
                    select(PilotEvaluationRecord).where(PilotEvaluationRecord.idempotency_key == idem_key)
                )
                rec = existing_res2.scalar_one_or_none() or PilotEvaluationRecord(
                    idempotency_key=idem_key,
                    pilot_id=pilot_id,
                    pilot_version=pilot_version,
                    incident_id=inc_id,
                    incident_db_id=inc_db_id,
                    rule_id=rule_id_str,
                    archetype=archetype,
                    severity=inc_sev,
                    execution_mode=pilot_mode,
                    source_type=clean_source,
                )
                rec.eligibility_status = elig_status
                rec.proposed_verdict = verdict_data.get("proposed_verdict")
                rec.validated_verdict = eff_verdict
                rec.validation_status = val_status
                rec.abstention_reason = verdict_data.get("abstention_reason")
                rec.trust_score = verdict_data.get("trust_score")
                rec.raw_trust_score = verdict_data.get("raw_trust_score")
                rec.is_calibrated = bool(verdict_data.get("is_calibrated", False))
                rec.evidence_completeness = verdict_data.get("evidence_completeness")
                rec.grounding_ratio = verdict_data.get("grounding_ratio")
                rec.supporting_evidence = list(verdict_data.get("supporting_evidence") or [])
                rec.contradictory_evidence = list(verdict_data.get("detected_contradictions") or [])
                rec.missing_evidence = list(verdict_data.get("missing_evidence") or [])
                rec.policy_version_id = policy_version_id
                rec.policy_version_number = verdict_data.get("policy_version_number") or policy_version_number
                rec.policy_digest = verdict_data.get("compilation_digest") or policy_digest
                rec.model_identifier = str(verdict_data.get("model_identifier") or "")
                rec.is_simulated = bool(verdict_data.get("is_simulated", False))
                rec.latency_ms = int(verdict_data.get("latency_ms") or 0)
                rec.prompt_tokens = int(verdict_data.get("prompt_tokens") or 0)
                rec.completion_tokens = int(verdict_data.get("completion_tokens") or 0)
                rec.total_tokens = int(verdict_data.get("total_tokens") or 0)
                rec.evidence_snapshot_hash = ev_hash
                rec.error_message = None
                rec.updated_at = utc_now()

                eval_prov = classify_execution_provenance(
                    is_simulated=rec.is_simulated,
                    model_identifier=rec.model_identifier,
                    validation_status=rec.validation_status,
                    eligibility_status=rec.eligibility_status,
                    source_type=rec.source_type,
                    recorded_provenance=verdict_data.get("execution_provenance"),
                    recorded_test_env=verdict_data.get("test_environment"),
                    base_url=settings.LOCAL_LLM_BASE_URL,
                )

                self.db.add(rec)
                await self.db.flush()
                now_ts = utc_now()
                prov_details = {
                    "execution_provenance": eval_prov["execution_provenance"],
                    "configured_provider": eval_prov["configured_provider"],
                    "historical_execution_provenance": eval_prov["historical_execution_provenance"],
                    "source_type": rec.source_type,
                    "model_identifier": rec.model_identifier,
                    "is_simulated": rec.is_simulated,
                    "test_environment": eval_prov["test_environment"],
                }
                self.db.add(
                    AuditLog(
                        user_id=actor,
                        username=actor,
                        action="PILOT_EVALUATION_RECORDED",
                        resource_type="PILOT_EVALUATION",
                        resource_id=rec.id,
                        details=prov_details,
                        created_at=now_ts,
                        signature=compute_audit_signature(actor, "PILOT_EVALUATION_RECORDED", "PILOT_EVALUATION", rec.id, now_ts, prov_details),
                        key_id=AuditService.KEY_ID,
                    )
                )
                await self.db.commit()
                await self.db.refresh(rec)
                return {
                    "status": elig_status,
                    "evaluation_id": rec.id,
                    "incident_id": rec.incident_id,
                    "execution_mode": rec.execution_mode,
                    "proposed_verdict": rec.proposed_verdict,
                    "validated_verdict": rec.validated_verdict,
                    "validation_status": val_status,
                    "trust_score": rec.trust_score,
                    "is_simulated": rec.is_simulated,
                    "execution_provenance": eval_prov["execution_provenance"],
                    "configured_provider": eval_prov["configured_provider"],
                    "test_environment": eval_prov["test_environment"],
                    "policy_governance_mode": verdict_data.get("policy_governance_mode"),
                    "autonomous_operation_eligible": bool(verdict_data.get("autonomous_operation_eligible", False)),
                    "autonomous_action_blocked": bool(verdict_data.get("autonomous_action_blocked", True)),
                }

            except LocalLLMUnavailableError as llm_err:
                await self.db.rollback()
                return await self._handle_pilot_failure(
                    pilot_id=pilot_id,
                    pilot_version=pilot_version,
                    pilot_mode=pilot_mode,
                    err_policy=err_policy,
                    err_thresh=err_thresh,
                    inc_id=inc_id,
                    inc_db_id=inc_db_id,
                    inc_sev=inc_sev,
                    rule_id_str=rule_id_str,
                    archetype=archetype,
                    idem_key=idem_key,
                    clean_source=clean_source,
                    ev_hash=ev_hash,
                    err_msg=f"SERVER2_OFFLINE: {llm_err}",
                    actor=actor,
                )
            except Exception as exc:
                await self.db.rollback()
                return await self._handle_pilot_failure(
                    pilot_id=pilot_id,
                    pilot_version=pilot_version,
                    pilot_mode=pilot_mode,
                    err_policy=err_policy,
                    err_thresh=err_thresh,
                    inc_id=inc_id,
                    inc_db_id=inc_db_id,
                    inc_sev=inc_sev,
                    rule_id_str=rule_id_str,
                    archetype=archetype,
                    idem_key=idem_key,
                    clean_source=clean_source,
                    ev_hash=ev_hash,
                    err_msg=f"INFERENCE_ERROR: {exc}",
                    actor=actor,
                )

    async def _handle_pilot_failure(
        self,
        pilot_id: str,
        pilot_version: int,
        pilot_mode: str,
        err_policy: str,
        err_thresh: int,
        inc_id: str,
        inc_db_id: str,
        inc_sev: str,
        rule_id_str: str,
        archetype: str,
        idem_key: str,
        clean_source: str,
        ev_hash: str,
        err_msg: str,
        actor: str,
    ) -> Dict[str, Any]:
        PilotService._consecutive_errors += 1
        rec = PilotEvaluationRecord(
            idempotency_key=f"{idem_key}:err:{uuid.uuid4().hex[:8]}",
            pilot_id=pilot_id,
            pilot_version=pilot_version,
            incident_id=inc_id,
            incident_db_id=inc_db_id,
            rule_id=rule_id_str,
            archetype=archetype,
            severity=inc_sev,
            execution_mode=pilot_mode,
            source_type=clean_source,
            eligibility_status="FAILED",
            proposed_verdict="REQUIRES_ATTENTION",
            validated_verdict="REQUIRES_ATTENTION",
            validation_status="PROVIDER_UNAVAILABLE",
            abstention_reason=err_msg,
            model_identifier=settings.LOCAL_LLM_MODEL_NAME,
            is_simulated=False,
            evidence_snapshot_hash=ev_hash,
            error_message=err_msg[:2000],
        )
        self.db.add(rec)
        await self.db.flush()
        fail_prov = classify_execution_provenance(
            is_simulated=False,
            model_identifier=rec.model_identifier,
            validation_status=rec.validation_status,
            eligibility_status="FAILED",
            source_type=clean_source,
            error_message=err_msg,
        )
        now_fail = utc_now()
        fail_details = {
            "execution_provenance": fail_prov["execution_provenance"],
            "configured_provider": fail_prov["configured_provider"],
            "historical_execution_provenance": fail_prov["historical_execution_provenance"],
            "source_type": clean_source,
            "model_identifier": rec.model_identifier,
            "is_simulated": False,
            "test_environment": fail_prov["test_environment"],
        }
        self.db.add(
            AuditLog(
                user_id=actor,
                username=actor,
                action="PILOT_EVALUATION_FAILED",
                resource_type="PILOT_EVALUATION",
                resource_id=rec.id,
                details=fail_details,
                created_at=now_fail,
                signature=compute_audit_signature(actor, "PILOT_EVALUATION_FAILED", "PILOT_EVALUATION", rec.id, now_fail, fail_details),
                key_id=AuditService.KEY_ID,
            )
        )

        auto_paused = False
        if (
            err_policy == "PAUSE_ON_CONSECUTIVE_ERRORS"
            and PilotService._consecutive_errors >= err_thresh
        ):
            cfg_res = await self.db.execute(select(PilotConfiguration).where(PilotConfiguration.id == pilot_id))
            live_cfg = cfg_res.scalar_one_or_none()
            if live_cfg and not live_cfg.is_paused:
                live_cfg.is_paused = True
                live_cfg.version_number += 1
                live_cfg.updated_by = "pilot_circuit_guard"
                live_cfg.updated_at = utc_now()
                self.db.add(live_cfg)
                await self._record_history_and_audit(
                    live_cfg,
                    "PILOT_AUTO_PAUSED_ERRORS",
                    actor,
                    f"Auto-paused after {PilotService._consecutive_errors} consecutive provider errors: {err_msg[:200]}",
                )
                auto_paused = True

        await self.db.commit()
        return {
            "status": "FAILED",
            "evaluation_id": rec.id,
            "incident_id": inc_id,
            "error": err_msg,
            "auto_paused": auto_paused,
        }

    async def run_pilot_batch(self, req: PilotBatchRunRequest, actor: str) -> Dict[str, Any]:
        cfg = await self.get_or_create_config()
        if cfg.mode == PilotMode.DISABLED.value:
            return {"status": "SKIPPED", "reason": "PILOT_DISABLED", "processed": 0, "results": []}
        if cfg.is_paused:
            return {"status": "SKIPPED", "reason": "PILOT_PAUSED", "processed": 0, "results": []}

        if req.incident_ids:
            inc_ids = list(req.incident_ids[: req.max_batch])
        else:
            q = select(Incident.incident_id).order_by(desc(Incident.created_at)).limit(req.max_batch)
            res = await self.db.execute(q)
            inc_ids = list(res.scalars().all())

        results = []
        evaluated = 0
        abstained = 0
        failed = 0
        skipped = 0

        for iid in inc_ids:
            out = await self.evaluate_incident_for_pilot(
                incident_id=iid,
                source_type=req.source_type,
                actor=actor,
                allow_simulated=(req.allow_simulated and req.source_type != "LIVE"),
            )
            results.append(out)
            st = out.get("status")
            if st == "EVALUATED":
                evaluated += 1
            elif st == "ABSTAINED":
                abstained += 1
            elif st == "FAILED":
                failed += 1
            else:
                skipped += 1

        return {
            "status": "COMPLETED",
            "pilot_mode": cfg.mode,
            "source_type": req.source_type,
            "requested": len(inc_ids),
            "evaluated": evaluated,
            "abstained": abstained,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }

    async def record_analyst_feedback(
        self,
        eval_id: str,
        req: PilotFeedbackRequest,
        analyst_username: str,
    ) -> PilotEvaluationRecord:
        res = await self.db.execute(select(PilotEvaluationRecord).where(PilotEvaluationRecord.id == eval_id))
        rec = res.scalar_one_or_none()
        if not rec:
            raise ValueError(f"Pilot evaluation '{eval_id}' not found.")

        # Never overwrite original AI proposed_verdict / validated_verdict / trust_score
        rec.analyst_feedback_action = req.action
        rec.analyst_decision = req.analyst_decision
        rec.analyst_override_reason = req.reason.strip()
        rec.analyst_user = analyst_username
        rec.analyst_decided_at = utc_now()
        rec.supervisor_verified = False  # Requires independent supervisor verification
        rec.updated_at = utc_now()
        self.db.add(rec)

        audit = AuditService(self.db)
        await audit.log(
            action="PILOT_ANALYST_FEEDBACK",
            user_id=analyst_username,
            username=analyst_username,
            entity_type="PILOT_EVALUATION",
            entity_id=rec.id,
            details={
                "incident_id": rec.incident_id,
                "ai_validated_verdict": rec.validated_verdict,
                "analyst_action": req.action,
                "analyst_decision": req.analyst_decision,
            },
        )
        await self.db.refresh(rec)
        return rec

    async def supervisor_verify_feedback(
        self,
        eval_id: str,
        req: PilotSupervisorVerifyRequest,
        supervisor_username: str,
    ) -> PilotEvaluationRecord:
        res = await self.db.execute(select(PilotEvaluationRecord).where(PilotEvaluationRecord.id == eval_id))
        rec = res.scalar_one_or_none()
        if not rec:
            raise ValueError(f"Pilot evaluation '{eval_id}' not found.")
        if not rec.analyst_decision:
            raise ValueError("Cannot verify feedback before an analyst has recorded a disposition.")
        if rec.analyst_user and rec.analyst_user == supervisor_username:
            raise ValueError("SELF_VERIFICATION_PROHIBITED: Supervisor verification requires an independent reviewer.")

        rec.supervisor_verified = bool(req.approved)
        rec.supervisor_user = supervisor_username
        rec.supervisor_verified_at = utc_now()
        rec.supervisor_notes = req.notes.strip()
        rec.updated_at = utc_now()
        self.db.add(rec)

        audit = AuditService(self.db)
        await audit.log(
            action="PILOT_SUPERVISOR_VERIFICATION",
            user_id=supervisor_username,
            username=supervisor_username,
            entity_type="PILOT_EVALUATION",
            entity_id=rec.id,
            details={
                "incident_id": rec.incident_id,
                "approved": bool(req.approved),
                "analyst_user": rec.analyst_user,
                "analyst_decision": rec.analyst_decision,
            },
        )
        await self.db.refresh(rec)
        return rec

    async def get_pilot_metrics(self) -> Dict[str, Any]:
        cfg = await self.get_or_create_config()

        total_incidents_q = await self.db.execute(select(func.count(Incident.id)))
        total_incidents = int(total_incidents_q.scalar() or 0)

        evals_res = await self.db.execute(
            select(PilotEvaluationRecord)
            .where(PilotEvaluationRecord.pilot_id == cfg.id)
            .order_by(desc(PilotEvaluationRecord.created_at))
        )
        evals = list(evals_res.scalars().all())

        # Queue backlog (pending triage incidents + active task queue)
        pending_inc_q = await self.db.execute(select(func.count(Incident.id)).where(Incident.ai_verdict.is_(None)))
        pending_incidents = int(pending_inc_q.scalar() or 0)
        queued_q = await self.db.execute(
            select(func.count(QueuedTask.id)).where(QueuedTask.status.in_(["PENDING", "PROCESSING", "RETRYING"]))
        )
        queue_backlog = int(queued_q.scalar() or 0)

        # Strictly separate live/real vs simulated evaluations
        live_evals = [e for e in evals if not e.is_simulated]
        sim_evals = [e for e in evals if e.is_simulated]

        evaluated_live = [e for e in live_evals if e.eligibility_status in ("EVALUATED", "ABSTAINED")]
        failed_live = [e for e in live_evals if e.eligibility_status == "FAILED"]

        tp_recs = sum(1 for e in evaluated_live if e.validated_verdict == "TRUE_POSITIVE")
        fp_recs = sum(1 for e in evaluated_live if e.validated_verdict == "FALSE_POSITIVE")
        ra_recs = sum(1 for e in evaluated_live if e.validated_verdict == "REQUIRES_ATTENTION")

        latencies = sorted([int(e.latency_ms) for e in evaluated_live if e.latency_ms and e.latency_ms > 0])
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
        p50_latency = latencies[len(latencies) // 2] if latencies else None
        p95_idx = min(len(latencies) - 1, math.floor(0.95 * len(latencies))) if latencies else None
        p95_latency = latencies[p95_idx] if p95_idx is not None else None

        live_prompt_tok = sum(int(e.prompt_tokens or 0) for e in live_evals)
        live_comp_tok = sum(int(e.completion_tokens or 0) for e in live_evals)
        live_total_tok = sum(int(e.total_tokens or 0) for e in live_evals)

        sim_total_tok = sum(int(e.total_tokens or 0) for e in sim_evals)

        # Provider health
        from app.services.ai_verdict_service import VerdictTriageAgent

        try:
            provider_available = await VerdictTriageAgent.is_local_llm_available(force_refresh=True)
        except Exception:
            provider_available = False
        ep_prov = classify_endpoint_status(
            is_healthy=provider_available,
            raw_status="ONLINE" if provider_available else "OFFLINE",
            base_url=settings.LOCAL_LLM_BASE_URL,
            metrics_available=False,
            configured_provider="OPENAI_COMPATIBLE",
        )
        gpu_telem = gpu_workload_manager.get_telemetry()
        cb_state = gpu_telem.get("circuit_breaker", {}).get("state", "CLOSED")

        # Count live_evals by persisted execution_provenance from AuditLog so HTTP_MOCK is never merged with verified GPU inference
        eval_ids = [e.id for e in evals]
        prov_map: Dict[str, Dict[str, Any]] = {}
        if eval_ids:
            p_res = await self.db.execute(
                select(AuditLog)
                .where(
                    AuditLog.resource_type == "PILOT_EVALUATION",
                    AuditLog.resource_id.in_(eval_ids),
                )
                .order_by(desc(AuditLog.created_at))
            )
            for alog in p_res.scalars().all():
                if alog.resource_id and alog.resource_id not in prov_map and isinstance(alog.details, dict):
                    prov_map[alog.resource_id] = alog.details

        http_mock_cnt = 0
        live_provider_cnt = 0
        historical_cnt = 0
        guard_cnt = 0
        for e in live_evals:
            det = prov_map.get(e.id, {})
            p_cls = classify_execution_provenance(
                is_simulated=e.is_simulated,
                model_identifier=e.model_identifier,
                validation_status=e.validation_status,
                eligibility_status=e.eligibility_status,
                source_type=e.source_type,
                error_message=e.error_message,
                recorded_provenance=det.get("execution_provenance"),
                recorded_test_env=det.get("test_environment"),
            )["execution_provenance"]
            if p_cls == "HTTP_MOCK":
                http_mock_cnt += 1
            elif p_cls == "LIVE_PROVIDER":
                live_provider_cnt += 1
            elif p_cls == "HISTORICAL":
                historical_cnt += 1
            elif p_cls in ("POLICY_GUARD", "PREFLIGHT_GUARD", "TOKEN_BUDGET_GUARD", "VALIDATION_GUARD"):
                guard_cnt += 1

        hr_used, day_used = await self._get_budget_usage(cfg.id)

        # Verdict Reliability over live evaluated records
        n_eval = len(evaluated_live)
        guardrail_accepted = sum(1 for e in evaluated_live if e.validated_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"))
        unsupported_cnt = sum(1 for e in evaluated_live if "UNSUPPORTED" in str(e.validation_status or "") or "CLAIM" in str(e.abstention_reason or "").upper())
        contradiction_cnt = sum(1 for e in evaluated_live if bool(e.contradictory_evidence))
        completeness_vals = [float(e.evidence_completeness) for e in evaluated_live if e.evidence_completeness is not None]
        avg_completeness = round(sum(completeness_vals) / len(completeness_vals), 4) if completeness_vals else None

        analyst_reviewed = [e for e in evaluated_live if e.analyst_decision]
        disagreements = sum(
            1 for e in analyst_reviewed
            if e.validated_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE") and e.analyst_decision != e.validated_verdict
        )

        failure_dist: Dict[str, int] = {}
        for e in live_evals:
            if e.eligibility_status in ("ABSTAINED", "FAILED") or e.validated_verdict == "REQUIRES_ATTENTION":
                code = str(e.validation_status or e.eligibility_status or "UNKNOWN")
                failure_dist[code] = failure_dist.get(code, 0) + 1

        # Empirical Accuracy ONLY over non-simulated evaluations joined against VERIFIED independent ground truth
        gt_res = await self.db.execute(
            select(Incident, HistoricalGroundTruth)
            .join(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
            .options(selectinload(Incident.events))
        )
        gt_by_inc: Dict[str, Tuple[Incident, HistoricalGroundTruth]] = {
            str(i.incident_id): (i, g) for i, g in gt_res.all()
        }

        emp_rows: List[Dict[str, Any]] = []
        for e in evaluated_live:
            pair = gt_by_inc.get(e.incident_id)
            if not pair:
                continue
            inc_obj, gt_obj = pair
            rp = inc_obj.raw_payload if isinstance(inc_obj.raw_payload, dict) else {}
            if HistoricalGroundTruthValidator.is_synthetic_fixture(inc_obj, rp, gt_obj):
                continue
            adj, _, _ = HistoricalGroundTruthValidator.adjudicate_label(
                raw_resolution=gt_obj.resolution,
                analyst_comments=gt_obj.comments,
                is_ml_generated=gt_obj.is_ml_generated,
                cleared_reason=getattr(gt_obj, "cleared_reason", None),
                cleared_user=getattr(gt_obj, "cleared_user", None),
            )
            if adj not in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                continue
            eff_v = (
                "REQUIRES_ANALYST_ATTENTION"
                if e.validated_verdict == "REQUIRES_ATTENTION"
                else (e.validated_verdict or "REQUIRES_ANALYST_ATTENTION")
            )
            eff_trust, _, _, _ = VerdictTrustworthinessEngine.cap_uncalibrated_trust_score(
                e.trust_score, is_calibrated=bool(e.is_calibrated)
            )
            emp_rows.append(
                {
                    "effective_verdict": eff_v,
                    "ground_truth_label": adj.value,
                    "trust_score": eff_trust,
                    "evidence_status": "CONFLICTING" if e.contradictory_evidence else "SUFFICIENT",
                }
            )

        emp_metrics = EmpiricalAccuracyEvaluator.evaluate_performance(emp_rows, compute_curve=True)
        from app.services.calibration_evaluator import CalibrationEvaluator

        calib_report = CalibrationEvaluator.evaluate_calibration(emp_rows)

        return {
            "pilot": self._config_to_snapshot(cfg),
            "population_notice": (
                "Operational and accuracy metrics strictly isolate LIVE non-simulated inference from simulated runs "
                "and include only verified human ground-truth labels in empirical accuracy calculations."
            ),
            "operational": {
                "total_incidents_received": total_incidents,
                "eligible_pilot_incidents": len(live_evals),
                "incidents_evaluated": len(evaluated_live),
                "simulated_evaluations_excluded_count": len(sim_evals),
                "pending_incidents": pending_incidents,
                "tp_recommendations": tp_recs,
                "fp_recommendations": fp_recs,
                "requires_attention": ra_recs,
                "inference_failures": len(failed_live),
                "avg_latency_ms": avg_latency,
                "p50_latency_ms": p50_latency,
                "p95_latency_ms": p95_latency,
                "token_consumption_live": {
                    "prompt_tokens": live_prompt_tok,
                    "completion_tokens": live_comp_tok,
                    "total_tokens": live_total_tok,
                },
                "token_consumption_simulated_isolated": {
                    "total_tokens": sim_total_tok,
                },
                "hourly_budget_used": hr_used,
                "hourly_budget_limit": cfg.hourly_evaluation_budget,
                "daily_budget_used": day_used,
                "daily_budget_limit": cfg.daily_evaluation_budget,
                "queue_backlog": queue_backlog,
                "provider_available": provider_available,
                "configured_provider": ep_prov["configured_provider"],
                "endpoint_provenance": ep_prov["endpoint_provenance"],
                "current_s2_health": ep_prov["current_s2_health"],
                "gpu_telemetry_verified": ep_prov["gpu_telemetry_verified"],
                "test_environment": ep_prov["test_environment"],
                "live_provider_evaluations_count": live_provider_cnt,
                "http_mock_evaluations_count": http_mock_cnt,
                "historical_evaluations_count": historical_cnt,
                "guard_abstention_evaluations_count": guard_cnt,
                "circuit_breaker_state": cb_state,
            },
            "reliability": {
                "sample_size": n_eval,
                "guardrail_acceptance_rate": round(guardrail_accepted / n_eval, 4) if n_eval > 0 else None,
                "unsupported_claim_rate": round(unsupported_cnt / n_eval, 4) if n_eval > 0 else None,
                "contradiction_rate": round(contradiction_cnt / n_eval, 4) if n_eval > 0 else None,
                "evidence_completeness_avg": avg_completeness,
                "abstention_rate": round(ra_recs / n_eval, 4) if n_eval > 0 else None,
                "analyst_reviewed_count": len(analyst_reviewed),
                "analyst_disagreement_rate": round(disagreements / len(analyst_reviewed), 4) if analyst_reviewed else None,
                "policy_failure_distribution": failure_dist,
            },
            "empirical_accuracy": {
                "verified_tp_cases": emp_metrics.tp_ground_truth_count,
                "verified_fp_cases": emp_metrics.fp_ground_truth_count,
                "verified_total_cases": emp_metrics.verified_ground_truth_cases,
                "tp_precision": emp_metrics.precision,
                "tp_precision_ci": emp_metrics.precision_ci.model_dump() if emp_metrics.precision_ci else None,
                "tp_recall": emp_metrics.recall,
                "tp_recall_ci": emp_metrics.recall_ci.model_dump() if emp_metrics.recall_ci else None,
                "fp_specificity": emp_metrics.specificity,
                "fp_specificity_ci": emp_metrics.specificity_ci.model_dump() if emp_metrics.specificity_ci else None,
                "balanced_accuracy": emp_metrics.balanced_accuracy,
                "selective_accuracy": emp_metrics.overall_accuracy,
                "decision_coverage": emp_metrics.automatic_decision_coverage,
                "false_negatives": emp_metrics.false_negatives,
                "metric_status": emp_metrics.metric_status,
                "balanced_accuracy_reason": emp_metrics.balanced_accuracy_reason,
                "calibration_status": calib_report.status,
                "is_calibrated": calib_report.is_calibrated,
                "trust_scale_label": "Calibrated" if calib_report.is_calibrated else "Uncalibrated Ordinal (Capped <= 6/10)",
                "risk_coverage_curve": [pt.model_dump() for pt in emp_metrics.risk_coverage_curve],
            },
        }
