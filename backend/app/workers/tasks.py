import asyncio
import logging
import random
import time
from datetime import datetime
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

            now = datetime.utcnow()
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
    def run_dry_run_job_task(self, job_id: str):
        """Celery worker task for executing asynchronous simulation lab jobs."""
        from app.services.dry_run_service import dry_run_service
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _run():
                async with AsyncSessionLocal() as session:
                    return await dry_run_service.execute_dry_run_job(db=session, job_id=job_id)
            return loop.run_until_complete(_run())
        finally:
            loop.close()
else:
    def triage_incident_task(*args, **kwargs):
        raise RuntimeError("Celery is not available.")

    def run_dry_run_job_task(*args, **kwargs):
        raise RuntimeError("Celery is not available.")


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
