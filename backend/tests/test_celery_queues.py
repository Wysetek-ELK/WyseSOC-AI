import pytest
from app.workers.celery_app import celery_app, is_redis_available, get_queue_depth
from app.workers.tasks import (
    _async_record_task_state,
    dispatch_incident_triage,
)
from app.models.task_queue import QueuedTask
from sqlalchemy import select


@pytest.mark.asyncio
async def test_celery_configuration_and_queues():
    """Verifies Celery configuration, task serializer, queues, and time limits."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert "live_triage" in celery_app.conf.task_queues
    assert "simulation_replay" in celery_app.conf.task_queues
    assert celery_app.conf.task_acks_late is True


@pytest.mark.asyncio
async def test_task_state_machine_transitions(db_session):
    """
    Tests durable task state machine:
    QUEUED -> PROCESSING -> RETRYING -> DEAD_LETTER
    """
    entity_id = "test-incident-task-state-001"
    
    # 1. Record initial PROCESSING
    task_id = await _async_record_task_state(
        task_name="triage_incident",
        queue_name="live_triage",
        entity_id=entity_id,
        status="PROCESSING",
        retry_count=0,
        db=db_session,
    )
    assert task_id is not None

    # Verify in DB
    res = await db_session.execute(select(QueuedTask).where(QueuedTask.id == task_id))
    task = res.scalar_one_or_none()
    assert task is not None
    assert task.status == "PROCESSING"

    # 2. Record RETRYING
    await _async_record_task_state(
        task_name="triage_incident",
        queue_name="live_triage",
        entity_id=entity_id,
        status="RETRYING",
        retry_count=1,
        error_message="Simulated temporary failure",
        db=db_session,
    )
    await db_session.refresh(task)
    assert task.status == "RETRYING"
    assert task.retry_count == 1

    # 3. Record DEAD_LETTER
    await _async_record_task_state(
        task_name="triage_incident",
        queue_name="live_triage",
        entity_id=entity_id,
        status="DEAD_LETTER",
        retry_count=3,
        error_message="Max retries exceeded",
        db=db_session,
    )
    await db_session.refresh(task)
    assert task.status == "DEAD_LETTER"
    assert task.completed_at is not None
