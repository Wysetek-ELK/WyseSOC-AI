import asyncio
import logging
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import selectinload

from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.verdict_intelligence import (
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.schemas.dry_run import DryRunConfigCreate
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.policy_governance import resolve_canonical_rule
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.verdict_pipeline import (
    PipelineLLMUnavailableError,
    run_shared_verdict_pipeline,
)

logger = logging.getLogger("ai_verdict.dry_run_service")


class ValidationEngine:
    """
    Validation Engine (formerly DryRunService).
    Executes controlled dry-run simulation, offline replay, batch validation,
    and benchmarking experiments for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_config(self, data: DryRunConfigCreate, user_id: Optional[str] = None) -> DryRunConfig:
        config = DryRunConfig(
            name=data.name.strip(),
            description=data.description.strip(),
            rule_id=data.rule_id,
            prompt_version_id=data.prompt_version_id,
            provider_type=data.provider_type.upper().strip(),
            split_strategy=data.split_strategy.upper().strip(),
            dataset_filters=data.dataset_filters,
            created_by_user_id=user_id,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def list_configs(self) -> List[DryRunConfig]:
        query = select(DryRunConfig).options(selectinload(DryRunConfig.rule)).order_by(desc(DryRunConfig.created_at))
        res = await self.db.execute(query)
        return res.scalars().all()

    async def get_config(self, config_id: str) -> Optional[DryRunConfig]:
        query = select(DryRunConfig).where(DryRunConfig.id == config_id).options(
            selectinload(DryRunConfig.rule),
            selectinload(DryRunConfig.jobs)
        )
        res = await self.db.execute(query)
        return res.scalars().first()

    async def split_dataset(
        self,
        strategy: str,
        rule_id: Optional[str] = None,
        custom_limit: Optional[int] = None
    ) -> List[Incident]:
        """
        Splits dataset to ensure testing integrity and prevent data leakage:
        - ALL: All matching incidents.
        - CHRONOLOGICAL_70_30: Orders by created_at_epoch asc, takes the most recent 30% for dry-run testing.
        - GROUP_AWARE_HOST: Groups incidents by reporting device / host to prevent co-occurring alert leakage.
        """
        query = select(Incident).options(
            selectinload(Incident.events),
            selectinload(Incident.rule),
            selectinload(Incident.ground_truth),
        )

        if rule_id:
            canonical_rule = await resolve_canonical_rule(self.db, rule_id)
            if canonical_rule:
                query = query.where(
                    or_(
                        Incident.rule_id == canonical_rule.id,
                        and_(
                            Incident.rule_id.is_(None),
                            Incident.event_type == canonical_rule.event_type,
                        ),
                    )
                )
            else:
                query = query.where(or_(Incident.rule_id == rule_id, Incident.event_type == rule_id))

        query = query.order_by(Incident.created_at_epoch.asc())
        res = await self.db.execute(query)
        all_incidents = list(res.scalars().all())

        if not all_incidents:
            return []

        strategy_norm = strategy.upper().strip()

        if strategy_norm == "CHRONOLOGICAL_70_30":
            split_idx = int(len(all_incidents) * 0.70)
            selected = all_incidents[split_idx:] if split_idx < len(all_incidents) else all_incidents
        elif strategy_norm == "GROUP_AWARE_HOST":
            # Group by reporting_device
            groups: Dict[str, List[Incident]] = {}
            for inc in all_incidents:
                dev = inc.reporting_device or "UNKNOWN"
                groups.setdefault(dev, []).append(inc)

            # Assign approximately 40% of unique hosts to test set
            selected = []
            hosts = list(groups.keys())
            test_hosts = set(hosts[int(len(hosts) * 0.60):])
            if not test_hosts:
                test_hosts = set(hosts[-1:])

            for h in test_hosts:
                selected.extend(groups[h])
        else:
            selected = all_incidents

        if custom_limit and custom_limit > 0:
            selected = selected[:custom_limit]

        return selected

    _SCHEMA_ERROR_STATUSES = {
        "INVALID_SCHEMA",
        "HTTP_ERROR",
        "UNEXPECTED_VERDICT",
        "LLM_UNAVAILABLE",
        "CIRCUIT_OPEN",
        "CONTEXT_WINDOW_EXCEEDED",
        "CONTEXT_BUDGET_EXCEEDED",
        "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION",
    }

    @classmethod
    def _normalize_legacy_verdict(cls, raw_verdict: str) -> str:
        up = str(raw_verdict or "REQUIRES_ATTENTION").upper().strip()
        if up == "REQUIRES_ANALYST_ATTENTION":
            return "REQUIRES_ATTENTION"
        if up in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"):
            return up
        return "REQUIRES_ATTENTION"

    async def execute_dry_run_job(self, config_id: str, custom_sample_limit: Optional[int] = None) -> DryRunJob:
        """
        Backward-compatible ValidationEngine / DryRunService entrypoint.
        Delegates incident evaluation through the canonical `PolicySimulationService` +
        `run_shared_verdict_pipeline` execution path and records both canonical
        `HistoricalEvaluationRunRecord`/`HistoricalEvaluationResultRecord` entries and
        legacy `DryRunJob`/`DryRunResult` rows with full provenance isolation.
        """
        from app.services.policy_simulation_service import PolicySimulationService

        config = await self.get_config(config_id)
        if not config:
            raise ValueError(f"Dry run configuration {config_id} not found")

        provider_upper = (config.provider_type or "SIMULATED").upper().strip()
        is_simulated = (provider_upper != "OPENAI_COMPATIBLE")

        target_pv = None
        target_rule = None
        if config.prompt_version_id:
            pv_res = await self.db.execute(select(PromptVersion).where(PromptVersion.id == config.prompt_version_id))
            target_pv = pv_res.scalars().first()
        if config.rule_id:
            target_rule = await resolve_canonical_rule(self.db, config.rule_id)
            if not target_pv and target_rule:
                rp_res = await self.db.execute(
                    select(RulePrompt)
                    .where(RulePrompt.rule_id == target_rule.id)
                    .options(selectinload(RulePrompt.versions))
                )
                rp = rp_res.scalars().first()
                if rp and rp.versions:
                    target_pv = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])

        if not target_rule and target_pv:
            rp_q = await self.db.execute(
                select(RulePrompt).where(RulePrompt.id == target_pv.prompt_id).options(selectinload(RulePrompt.rule))
            )
            rp_obj = rp_q.scalars().first()
            if rp_obj:
                target_rule = rp_obj.rule

        prompt_ver_num = target_pv.version_number if target_pv else 1
        policy_digest = PolicyQualityValidator.compute_policy_digest(target_pv) if target_pv else None

        incidents_to_test = await self.split_dataset(
            strategy=config.split_strategy,
            rule_id=(target_rule.id if target_rule else config.rule_id),
            custom_limit=custom_sample_limit,
        )

        sim_service = PolicySimulationService(self.db)
        hist_stats = await sim_service.get_rule_calibration_stats(target_rule.id if target_rule else None)

        inv_map: Dict[str, Investigation] = {}
        inc_db_ids = [inc.id for inc in incidents_to_test]
        if inc_db_ids:
            inv_q = await self.db.execute(
                select(Investigation).where(Investigation.incident_id.in_(inc_db_ids))
            )
            for inv_row in inv_q.scalars().all():
                inv_map[inv_row.incident_id] = inv_row

        job = DryRunJob(
            config_id=config.id,
            status="RUNNING",
            total_items=len(incidents_to_test),
            processed_items=0,
            error_count=0,
            is_simulated=is_simulated,
            started_at=utc_now(),
        )
        self.db.add(job)
        await self.db.flush()

        canonical_run = HistoricalEvaluationRunRecord(
            run_name=f"DryRun Adapter: {config.name}",
            rule_id=(target_rule.id if target_rule else config.rule_id),
            policy_version_id=(target_pv.id if target_pv else None),
            status="RUNNING",
            total_cases=len(incidents_to_test),
            evaluated_cases=0,
            verified_ground_truth_cases=0,
            validation_state="INCONCLUSIVE",
            config_snapshot={
                "adapter": "LEGACY_DRY_RUN_ADAPTER",
                "legacy_dry_run_job_id": job.id,
                "legacy_dry_run_config_id": config.id,
                "provider_type": provider_upper,
                "execution_provenance": "SIMULATED" if is_simulated else "REAL_LOCAL_LLM",
                "is_simulated": is_simulated,
                "split_strategy": config.split_strategy,
                "policy_version_id": target_pv.id if target_pv else None,
                "policy_digest": policy_digest,
            },
            started_at=job.started_at,
        )
        self.db.add(canonical_run)
        await self.db.commit()
        await self.db.refresh(job)

        from app.models.token_usage import TokenUsageRecord

        verified_gt_count = 0

        for inc in incidents_to_test:
            status_check = await self.db.execute(select(DryRunJob.status).where(DryRunJob.id == job.id))
            if status_check.scalar_one_or_none() == "CANCELLED":
                job.status = "CANCELLED"
                job.completed_at = utc_now()
                canonical_run.status = "CANCELLED"
                canonical_run.completed_at = job.completed_at
                await self.db.commit()
                return job

            inc_rule = inc.rule or target_rule
            inc_pv = target_pv
            if inc_rule and (not target_rule or inc_rule.id != target_rule.id) and not config.prompt_version_id:
                rp_q = await self.db.execute(
                    select(RulePrompt).where(RulePrompt.rule_id == inc_rule.id).options(selectinload(RulePrompt.versions))
                )
                rp_row = rp_q.scalars().first()
                if rp_row and rp_row.versions:
                    inc_pv = next((v for v in rp_row.versions if v.id == rp_row.active_version_id), rp_row.versions[0])

            try:
                pipe_res = await run_shared_verdict_pipeline(
                    db=self.db,
                    incident=inc,
                    rule=inc_rule,
                    prompt_version=inc_pv,
                    active_approved_version=inc_pv,
                    model_provider_type=provider_upper,
                    allow_simulated_fallback=False,
                    is_simulation=True,
                    is_prod=False,
                    execution_context="SIMULATION",
                    require_autonomous_certification=False,
                    username="simulation_engine",
                    historical_stats=hist_stats,
                    simulated_output_fn=sim_service._simulate_model_output if is_simulated else None,
                )

                vdata = pipe_res.verdict_data
                eff_verdict = str(pipe_res.effective_verdict or vdata.get("verdict") or "REQUIRES_ATTENTION")
                legacy_pred = self._normalize_legacy_verdict(eff_verdict)
                raw_val_status = str(vdata.get("validation_status") or "VALID")
                legacy_val_status = raw_val_status if raw_val_status in self._SCHEMA_ERROR_STATUSES else "VALID"
                latency_ms = int(vdata.get("latency_ms") or 0)
                model_ident = str(vdata.get("model_identifier") or ("simulated-v2.2-policy-aware" if is_simulated else "OPENAI_COMPATIBLE"))
                p_tok = int(pipe_res.prompt_tokens or vdata.get("prompt_tokens") or 0)
                c_tok = int(pipe_res.completion_tokens or vdata.get("completion_tokens") or 0)
                t_tok = int(pipe_res.total_tokens or vdata.get("total_tokens") or (p_tok + c_tok))
                pv_num_used = int(vdata.get("prompt_version_number") or (inc_pv.version_number if inc_pv else prompt_ver_num))

                # Adjudicate ground truth cleanly via HistoricalGroundTruthValidator (never leaks into prompt)
                gt_obj = getattr(inc, "ground_truth", None)
                inv_obj = inv_map.get(inc.id)
                gt_label_str: Optional[str] = None
                is_eligible_gt = False
                is_correct: Optional[bool] = None
                is_abstained = (legacy_pred == "REQUIRES_ATTENTION")
                is_critical_error = False
                gt_prov_src = "NONE"
                if gt_obj is not None or inv_obj is not None:
                    adj_label, excl_code, _detail, _rel, gt_prov_src = (
                        HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                            ground_truth=gt_obj,
                            investigation=inv_obj,
                            incident=inc,
                        )
                    )
                    gt_label_str = adj_label.value
                    is_eligible_gt = (
                        excl_code is None
                        and adj_label in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP)
                    )
                    if is_eligible_gt:
                        verified_gt_count += 1
                        expected = "TRUE_POSITIVE" if adj_label == GroundTruthLabel.VERIFIED_TP else "FALSE_POSITIVE"
                        if not is_abstained:
                            is_correct = (legacy_pred == expected)
                            if adj_label == GroundTruthLabel.VERIFIED_TP and legacy_pred == "FALSE_POSITIVE":
                                is_critical_error = True

                result_entry = DryRunResult(
                    job_id=job.id,
                    incident_id=inc.id,
                    predicted_verdict=legacy_pred,
                    confidence=int(round(float(vdata.get("confidence", 0.0)))),
                    reasoning=str(vdata.get("reason") or ""),
                    supporting_evidence=list(vdata.get("supporting_evidence") or []),
                    missing_evidence=list(vdata.get("missing_evidence") or []),
                    analyst_questions=list(vdata.get("analyst_questions") or []),
                    latency_ms=latency_ms,
                    model_identifier=model_ident,
                    prompt_version_number=pv_num_used,
                    validation_status=legacy_val_status,
                    is_simulated=is_simulated,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                )

                canon_res = HistoricalEvaluationResultRecord(
                    run_id=canonical_run.id,
                    incident_id=str(inc.incident_id or inc.id),
                    rule_id=(inc_rule.id if inc_rule else (target_rule.id if target_rule else "UNKNOWN")),
                    suggested_verdict=str(vdata.get("proposed_verdict") or eff_verdict),
                    effective_verdict=eff_verdict,
                    ground_truth_label=gt_label_str,
                    trust_score=pipe_res.trust_score,
                    raw_trust_score=float(pipe_res.raw_trust_score or 0.0),
                    evidence_sufficiency_score=float(vdata.get("evidence_sufficiency_score") or 0.0),
                    evidence_status=str(pipe_res.evidence_status or "INSUFFICIENT"),
                    is_correct=is_correct,
                    is_abstained=is_abstained,
                    is_critical_error=is_critical_error,
                    claims_summary={
                        "adapter": "LEGACY_DRY_RUN_ADAPTER",
                        "legacy_dry_run_job_id": job.id,
                        "is_simulated": is_simulated,
                        "provider_type": provider_upper,
                        "model_identifier": model_ident,
                        "policy_digest": policy_digest,
                        "validation_status": raw_val_status,
                        "proposal_validation_outcome": vdata.get("proposal_validation_outcome"),
                        "is_eligible_ground_truth": is_eligible_gt,
                        "ground_truth_provenance": gt_prov_src,
                    },
                    escalation_reason=str(pipe_res.escalation_reason)[:256] if pipe_res.escalation_reason else None,
                )

                tok_rec = TokenUsageRecord(
                    process_type="SIMULATION_REPLAY",
                    process_id=job.id,
                    incident_id=inc.incident_id,
                    rule_id=inc_rule.rule_id if inc_rule else inc.event_type,
                    model_identifier=model_ident,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                    latency_ms=latency_ms,
                    is_simulated=is_simulated,
                    executed_by_user="simulation_engine",
                    timestamp=utc_now(),
                    details={
                        "job_id": job.id,
                        "canonical_run_id": canonical_run.id,
                        "config_name": config.name,
                        "split_strategy": config.split_strategy,
                    },
                )
                self.db.add(result_entry)
                self.db.add(canon_res)
                self.db.add(tok_rec)
                job.processed_items += 1

            except (Exception, PipelineLLMUnavailableError) as e:
                logger.warning(f"DryRun adapter error on incident {inc.incident_id}: {e}")
                job.error_count += 1
                job.processed_items += 1
                self.db.add(
                    DryRunResult(
                        job_id=job.id,
                        incident_id=inc.id,
                        predicted_verdict="REQUIRES_ATTENTION",
                        confidence=0,
                        reasoning=f"Execution error: {str(e)}",
                        supporting_evidence=[],
                        missing_evidence=["Execution completion"],
                        analyst_questions=[],
                        latency_ms=0,
                        model_identifier="error",
                        prompt_version_number=prompt_ver_num,
                        validation_status="INVALID_SCHEMA",
                        is_simulated=is_simulated,
                    )
                )

        job.status = "COMPLETED"
        job.completed_at = utc_now()
        canonical_run.status = "COMPLETED"
        canonical_run.completed_at = job.completed_at
        canonical_run.evaluated_cases = job.processed_items
        canonical_run.verified_ground_truth_cases = verified_gt_count
        # Simulated or split-adapter runs remain INCONCLUSIVE for empirical G8 certification
        canonical_run.validation_state = "INCONCLUSIVE"
        canonical_run.metrics = {
            "adapter": "LEGACY_DRY_RUN_ADAPTER",
            "legacy_dry_run_job_id": job.id,
            "is_simulated": is_simulated,
            "sample_count": job.processed_items,
            "verified_ground_truth_cases": verified_gt_count,
            "error_count": job.error_count,
        }
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Optional[DryRunJob]:
        query = select(DryRunJob).where(DryRunJob.id == job_id).options(
            selectinload(DryRunJob.config).selectinload(DryRunConfig.rule),
            selectinload(DryRunJob.results).selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
        )
        res = await self.db.execute(query)
        return res.scalars().first()

    async def cancel_job(self, job_id: str) -> Optional[DryRunJob]:
        """Operator-initiated cancellation of in-flight simulation job."""
        job = await self.get_job(job_id)
        if not job:
            return None
        if job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
            job.status = "CANCELLED"
            job.completed_at = utc_now()
            await self.db.commit()
            await self.db.refresh(job)
        return job

    async def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Calculates real-time replay progress, rate, and estimated time of completion (ETA)."""
        job = await self.get_job(job_id)
        if not job:
            return None
        total = job.total_items or 0
        processed = job.processed_items or 0
        percent = round((processed / total * 100), 1) if total > 0 else 0.0

        elapsed_seconds = 0
        if job.started_at:
            end_time = job.completed_at or utc_now()
            elapsed_seconds = max(0, int((end_time - job.started_at).total_seconds()))

        eta_seconds = 0
        if processed > 0 and total > processed and elapsed_seconds > 0:
            rate = processed / max(1, elapsed_seconds)
            eta_seconds = int((total - processed) / rate)

        return {
            "job_id": job.id,
            "config_id": job.config_id,
            "status": job.status,
            "total_items": total,
            "processed_items": processed,
            "error_count": job.error_count,
            "progress_percent": percent,
            "elapsed_seconds": elapsed_seconds,
            "eta_seconds": eta_seconds,
            "is_simulated": job.is_simulated,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    async def list_jobs(self, limit: int = 50) -> List[DryRunJob]:
        query = select(DryRunJob).options(
            selectinload(DryRunJob.config).selectinload(DryRunConfig.rule)
        ).order_by(desc(DryRunJob.started_at)).limit(limit)
        res = await self.db.execute(query)
        return res.scalars().all()


# Backward compatibility alias
DryRunService = ValidationEngine


