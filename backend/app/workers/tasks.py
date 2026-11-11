import asyncio
import logging
import random
import time
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Dict, Any, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import AsyncSessionLocal, atomic_transaction
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.task_queue import QueuedTask
from app.workers.celery_app import celery_app, is_redis_available

logger = logging.getLogger("ai_verdict.tasks")


async def _async_record_task_state(
    task_name: str,
    queue_name: str,
    entity_id: str,
    status: str,
    retry_count: int = 0,
    max_retries: int = 3,
    payload: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> str:
    """Updates or inserts the task state machine record into QueuedTask."""
    async def _do_record(session) -> str:
        async with atomic_transaction(session):
            stmt = select(QueuedTask).where(
                QueuedTask.task_name == task_name,
                QueuedTask.entity_id == entity_id,
            ).order_by(QueuedTask.created_at.desc()).limit(1)
            res = await session.execute(stmt)
            task_rec = res.scalar_one_or_none()

            now = utc_now()
            if task_rec:
                task_rec.status = status
                task_rec.retry_count = retry_count
                task_rec.updated_at = now
                if result is not None:
                    task_rec.result = result
                if error_message is not None:
                    task_rec.error_message = error_message
                if status in ("COMPLETED", "DEAD_LETTER"):
                    task_rec.completed_at = now
                return task_rec.id
            else:
                new_task = QueuedTask(
                    task_name=task_name,
                    queue_name=queue_name,
                    entity_type="INCIDENT",
                    entity_id=entity_id,
                    status=status,
                    retry_count=retry_count,
                    max_retries=max_retries,
                    payload=payload or {},
                    result=result,
                    error_message=error_message,
                    created_at=now,
                    updated_at=now,
                    completed_at=now if status in ("COMPLETED", "DEAD_LETTER") else None,
                )
                session.add(new_task)
                await session.flush()
                return new_task.id

    if db:
        return await _do_record(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _do_record(session)


async def _execute_incident_triage_core(
    incident_id: str,
    trigger_source: str = "LIVE",
    is_simulated: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Executes core incident triage with idempotent state machine tracking.
    Handles bounded retries with exponential backoff and dead-letter routing.
    """
    await _async_record_task_state(
        task_name="triage_incident",
        queue_name="live_triage",
        entity_id=incident_id,
        status="PROCESSING",
        retry_count=retry_count,
        max_retries=max_retries,
        payload={"trigger_source": trigger_source, "is_simulated": is_simulated},
        db=db,
    )

    try:
        from app.services.ai_verdict_service import AIVerdictService
        
        async def _triage(session: AsyncSession):
            inc_res = await session.execute(select(Incident).where(Incident.incident_id == incident_id))
            inc = inc_res.scalar_one_or_none()
            if not inc:
                raise ValueError(f"Incident with ID '{incident_id}' not found in database.")

            verdict_service = AIVerdictService(session)
            return await verdict_service.evaluate_incident(
                incident_id_or_obj=inc,
                allow_simulated_fallback=is_simulated,
            )

        if db:
            verdict_result = await _triage(db)
        else:
            async with AsyncSessionLocal() as session:
                verdict_result = await _triage(session)

        # Mark COMPLETED
        await _async_record_task_state(
            task_name="triage_incident",
            queue_name="live_triage",
            entity_id=incident_id,
            status="COMPLETED",
            retry_count=retry_count,
            max_retries=max_retries,
            result={"verdict": verdict_result.get("verdict"), "confidence": verdict_result.get("confidence")},
            db=db,
        )
        logger.info(f"Successfully triaged incident '{incident_id}' -> Verdict: {verdict_result.get('verdict')}")
        return verdict_result

    except Exception as exc:
        err_str = str(exc)
        logger.error(f"Error triaging incident '{incident_id}' (attempt {retry_count + 1}/{max_retries}): {err_str}")

        if retry_count < max_retries:
            await _async_record_task_state(
                task_name="triage_incident",
                queue_name="live_triage",
                entity_id=incident_id,
                status="RETRYING",
                retry_count=retry_count + 1,
                max_retries=max_retries,
                error_message=f"Attempt {retry_count + 1} failed: {err_str}",
                db=db,
            )
            backoff_delay = (2 ** retry_count) * 2.0 + random.uniform(0.1, 1.0)
            await asyncio.sleep(backoff_delay)
            return await _execute_incident_triage_core(
                incident_id=incident_id,
                trigger_source=trigger_source,
                is_simulated=is_simulated,
                retry_count=retry_count + 1,
                max_retries=max_retries,
                db=db,
            )
        else:
            await _async_record_task_state(
                task_name="triage_incident",
                queue_name="live_triage",
                entity_id=incident_id,
                status="DEAD_LETTER",
                retry_count=retry_count,
                max_retries=max_retries,
                error_message=f"DEAD-LETTER: Exceeded {max_retries} retries. Final error: {err_str}",
                db=db,
            )
            raise


if celery_app is not None:
    @celery_app.task(bind=True, max_retries=3)
    def triage_incident_task(self, incident_id: str, trigger_source: str = "LIVE", is_simulated: bool = False):
        """Celery worker task wrapper executing async triage."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                _execute_incident_triage_core(
                    incident_id=incident_id,
                    trigger_source=trigger_source,
                    is_simulated=is_simulated,
                    retry_count=self.request.retries,
                    max_retries=3
                )
            )
        finally:
            loop.close()


    @celery_app.task(bind=True)
    def run_dry_run_job_task(self, job_or_config_id: str):
        """Celery worker task for executing asynchronous simulation lab jobs."""
        from app.services.dry_run_service import DryRunService
        from app.models.dry_run import DryRunJob
        from sqlalchemy import select

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _run():
                async with AsyncSessionLocal() as session:
                    svc = DryRunService(session)
                    cfg_id = job_or_config_id
                    job_res = await session.execute(select(DryRunJob).where(DryRunJob.id == job_or_config_id))
                    existing_job = job_res.scalar_one_or_none()
                    if existing_job and existing_job.config_id:
                        cfg_id = existing_job.config_id
                    return await svc.execute_dry_run_job(config_id=cfg_id)
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    @celery_app.task(bind=True)
    def run_policy_simulation_task(
        self,
        run_id: str,
        rule_id: str,
        candidate_version_id: Optional[str] = None,
        baseline_version_id: Optional[str] = None,
        provider_type: str = "SIMULATED",
        sample_limit: Optional[int] = 500,
        include_unlabeled_replay: bool = False,
    ):
        """Celery worker task for asynchronous AIS policy simulation on simulation_replay queue."""
        from app.models.prompt import PromptVersion
        from app.services.policy_simulation_service import PolicySimulationService
        from sqlalchemy import select

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _run():
                async with AsyncSessionLocal() as session:
                    cand_ver = None
                    base_ver = None
                    if candidate_version_id:
                        res = await session.execute(
                            select(PromptVersion).where(PromptVersion.id == candidate_version_id)
                        )
                        cand_ver = res.scalar_one_or_none()
                    if baseline_version_id:
                        res_b = await session.execute(
                            select(PromptVersion).where(PromptVersion.id == baseline_version_id)
                        )
                        base_ver = res_b.scalar_one_or_none()
                    svc = PolicySimulationService(session)
                    return await svc.evaluate_candidate_policy(
                        rule_id=rule_id,
                        candidate_version=cand_ver,
                        baseline_version=base_ver,
                        provider_type=provider_type,
                        sample_limit=sample_limit,
                        include_unlabeled_replay=include_unlabeled_replay,
                        existing_run_id=run_id,
                    )

            return loop.run_until_complete(_run())
        finally:
            loop.close()
else:
    def triage_incident_task(*args, **kwargs):
        raise RuntimeError("Celery is not available.")

    def run_dry_run_job_task(*args, **kwargs):
        raise RuntimeError("Celery is not available.")

    def run_policy_simulation_task(*args, **kwargs):
        raise RuntimeError("Celery is not available.")


async def dispatch_policy_simulation(
    *,
    db: AsyncSession,
    rule_id: str,
    candidate_version: Any = None,
    baseline_version: Any = None,
    provider_type: str = "SIMULATED",
    sample_limit: Optional[int] = 500,
    include_unlabeled_replay: bool = False,
    async_execution: bool = False,
) -> Dict[str, Any]:
    """
    Dispatch AIS historical policy simulation either asynchronously on Celery's
    `simulation_replay` queue (when async_execution=True and Redis/Celery are healthy)
    or directly in-process via PolicySimulationService.
    """
    from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
    from app.services.policy_quality_validator import PolicyQualityValidator
    from app.services.policy_simulation_service import PolicySimulationService
    import uuid as _uuid

    use_celery = (
        bool(async_execution)
        and settings.USE_ASYNC_CELERY
        and is_redis_available()
        and (celery_app is not None)
    )
    cand_id = str(getattr(candidate_version, "id", None) or "") or None
    base_id = str(getattr(baseline_version, "id", None) or "") or None

    if use_celery:
        run_id = str(_uuid.uuid4())
        policy_digest = (
            PolicyQualityValidator.compute_policy_digest(candidate_version)
            if candidate_version is not None
            else None
        )
        queued_rec = HistoricalEvaluationRunRecord(
            id=run_id,
            run_name=f"Policy Candidate Simulation ({provider_type})",
            rule_id=rule_id,
            policy_version_id=cand_id,
            status="QUEUED",
            validation_state="INCONCLUSIVE",
            config_snapshot={
                "provider_type": str(provider_type or "SIMULATED").upper(),
                "is_simulated": str(provider_type or "SIMULATED").upper() == "SIMULATED",
                "sample_limit": sample_limit,
                "policy_version_id": cand_id,
                "policy_digest": policy_digest,
                "include_unlabeled_replay": include_unlabeled_replay,
                "queued_at": utc_now().isoformat(),
            },
        )
        db.add(queued_rec)
        await db.commit()
        task = run_policy_simulation_task.apply_async(
            args=[
                run_id,
                rule_id,
                cand_id,
                base_id,
                str(provider_type or "SIMULATED").upper(),
                sample_limit,
                bool(include_unlabeled_replay),
            ],
            queue="simulation_replay",
        )
        return {
            "dispatch_mode": "CELERY_ASYNC",
            "task_id": task.id,
            "run_id": run_id,
            "status": "QUEUED",
            "simulation_status": "NOT_EVALUATED",
            "provider_type": str(provider_type or "SIMULATED").upper(),
            "rule_id": rule_id,
            "message": "Historical policy simulation queued on simulation_replay worker.",
        }

    svc = PolicySimulationService(db)
    result = await svc.evaluate_candidate_policy(
        rule_id=rule_id,
        candidate_version=candidate_version,
        baseline_version=baseline_version,
        provider_type=str(provider_type or "SIMULATED").upper(),
        sample_limit=sample_limit,
        include_unlabeled_replay=bool(include_unlabeled_replay),
    )
    if isinstance(result, dict):
        result.setdefault("dispatch_mode", "IN_PROCESS_ASYNC")
    return result


async def dispatch_incident_triage(
    incident_id: str,
    trigger_source: str = "LIVE",
    is_simulated: bool = False,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Unified Dispatcher:
    - If Celery is enabled and Redis broker is reachable: routes through Celery queue.
    - If Celery is disabled or Redis is unavailable (dev/test): executes directly in-process
      with identical state machine and error handling.
    """
    use_celery = settings.USE_ASYNC_CELERY and is_redis_available() and (celery_app is not None)

    if use_celery:
        logger.info(f"Dispatching incident '{incident_id}' to Celery 'live_triage' queue.")
        task = triage_incident_task.apply_async(
            args=[incident_id, trigger_source, is_simulated],
            queue="live_triage"
        )
        return {
            "dispatch_mode": "CELERY_ASYNC",
            "task_id": task.id,
            "status": "QUEUED",
            "incident_id": incident_id,
        }
    else:
        logger.info(f"Executing incident '{incident_id}' triage in-process (async direct mode).")
        return await _execute_incident_triage_core(
            incident_id=incident_id,
            trigger_source=trigger_source,
            is_simulated=is_simulated,
            retry_count=0,
            max_retries=3,
            db=db,
        )
