import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.services.model_provider.factory import get_model_provider
from app.services.incident_service import IncidentService
from app.schemas.incident import ModelFacingIncidentPayload
from app.schemas.dry_run import DryRunConfigCreate
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.token_budget_service import TokenBudgetService


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

    async def execute_dry_run_job(self, config_id: str, custom_sample_limit: Optional[int] = None) -> DryRunJob:
        config = await self.get_config(config_id)
        if not config:
            raise ValueError(f"Dry run configuration {config_id} not found")

        provider = get_model_provider(config.provider_type)
        is_simulated = (config.provider_type.upper() == "SIMULATED")

        # Resolve prompt policy with 100% Live-Simulation Parity (P3-REQ-02)
        target_pv = None
        target_rule = None
        if config.prompt_version_id:
            pv_res = await self.db.execute(select(PromptVersion).where(PromptVersion.id == config.prompt_version_id))
            target_pv = pv_res.scalars().first()
        elif config.rule_id:
            r_res = await self.db.execute(select(Rule).where(Rule.id == config.rule_id))
            target_rule = r_res.scalars().first()
            rp_res = await self.db.execute(
                select(RulePrompt).where(RulePrompt.rule_id == config.rule_id).options(selectinload(RulePrompt.versions))
            )
            rp = rp_res.scalars().first()
            if rp and rp.versions:
                target_pv = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])

        if not target_rule and target_pv:
            rp_q = await self.db.execute(select(RulePrompt).where(RulePrompt.id == target_pv.prompt_id).options(selectinload(RulePrompt.rule)))
            rp_obj = rp_q.scalars().first()
            if rp_obj:
                target_rule = rp_obj.rule

        compiled_policy = PolicyCompilerService.compile_policy(
            rule=target_rule,
            prompt_version=target_pv,
            execution_mode=CompilationExecutionMode.SIMULATION,
            raise_on_unapproved=False,
        )
        prompt_ver_num = compiled_policy.version_number or 1

        # Dataset splitting
        incidents_to_test = await self.split_dataset(
            strategy=config.split_strategy,
            rule_id=config.rule_id,
            custom_limit=custom_sample_limit
        )

        job = DryRunJob(
            config_id=config.id,
            status="RUNNING",
            total_items=len(incidents_to_test),
            processed_items=0,
            error_count=0,
            is_simulated=is_simulated,
            started_at=datetime.utcnow(),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        incident_service = IncidentService(self.db)

        # Execute replay
        for inc in incidents_to_test:
            try:
                # 1. Generate strictly sanitized model-facing payload (ZERO ground-truth leakage)
                payload_dict = incident_service.get_model_facing_payload(inc)

                rule_dict = {
                    "id": inc.rule_id or "",
                    "name": inc.rule.name if inc.rule else inc.event_type,
                    "event_type": inc.event_type,
                    "severity": inc.severity,
                }

                budgeted = TokenBudgetService.budget_prompt(
                    compiled_policy=compiled_policy,
                    incident_payload=payload_dict,
                    rag_block="",
                )
                prompt_text = budgeted.budgeted_system_prompt
                budgeted_payload = budgeted.budgeted_incident_payload

                # 2. Invoke provider
                verdict = await provider.analyze_incident(
                    incident_payload=budgeted_payload,
                    rule_spec=rule_dict,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )

                p_tok = getattr(verdict, "prompt_tokens", 0) or max(40, len(prompt_text) // 4)
                c_tok = getattr(verdict, "completion_tokens", 0) or max(20, len(verdict.reason) // 4)
                t_tok = getattr(verdict, "total_tokens", 0) or (p_tok + c_tok)

                # 3. Save result
                result_entry = DryRunResult(
                    job_id=job.id,
                    incident_id=inc.id,
                    predicted_verdict=verdict.verdict,
                    confidence=int(verdict.confidence),
                    reasoning=verdict.reason,
                    supporting_evidence=verdict.supporting_evidence,
                    missing_evidence=verdict.missing_evidence,
                    analyst_questions=verdict.analyst_questions,
                    latency_ms=verdict.latency_ms,
                    model_identifier=verdict.model_identifier,
                    prompt_version_number=verdict.prompt_version_number,
                    validation_status=verdict.validation_status,
                    is_simulated=verdict.is_simulated,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                )
                self.db.add(result_entry)

                # 3b. Record persistent bifurcated token usage on Server 1
                from app.models.token_usage import TokenUsageRecord
                tok_rec = TokenUsageRecord(
                    process_type="SIMULATION_REPLAY",
                    process_id=job.id,
                    incident_id=inc.incident_id,
                    rule_id=inc.rule.rule_id if inc.rule else inc.event_type,
                    model_identifier=verdict.model_identifier,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    total_tokens=t_tok,
                    latency_ms=verdict.latency_ms,
                    is_simulated=verdict.is_simulated,
                    executed_by_user="simulation_engine",
                    timestamp=datetime.utcnow(),
                    details={
                        "job_id": job.id,
                        "config_name": config.name,
                        "split_strategy": config.split_strategy,
                    },
                )
                self.db.add(tok_rec)
                job.processed_items += 1

            except Exception as e:
                job.error_count += 1
                job.processed_items += 1
                # Record error entry
                err_result = DryRunResult(
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
                self.db.add(err_result)

        job.status = "COMPLETED"
        job.completed_at = datetime.utcnow()
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

    async def list_jobs(self, limit: int = 50) -> List[DryRunJob]:
        query = select(DryRunJob).options(
            selectinload(DryRunJob.config).selectinload(DryRunConfig.rule)
        ).order_by(desc(DryRunJob.started_at)).limit(limit)
        res = await self.db.execute(query)
        return res.scalars().all()


# Backward compatibility alias
DryRunService = ValidationEngine


