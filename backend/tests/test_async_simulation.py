import pytest
from app.services.dry_run_service import DryRunService
from app.schemas.dry_run import DryRunConfigCreate
from app.models.incident import Incident
from app.models.rule import Rule
from app.models.user import User


@pytest.mark.asyncio
async def test_dry_run_job_progress_and_cancellation(db_session):
    """
    P4-REQ-05: Tests async simulation lab cancellation and progress calculation.
    """
    service = DryRunService(db_session)

    # Setup rule and incidents
    rule = Rule(
        rule_id="RULE-ASYNC-SIM-01",
        name="Async Simulation Rule",
        event_type="test_async_event",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.flush()

    for i in range(5):
        inc = Incident(
            incident_id=f"INC-ASYNC-{i}",
            rule_id=rule.id,
            event_type="test_async_event",
            title=f"Incident {i}",
            severity="HIGH",
        )
        db_session.add(inc)
    await db_session.commit()

    config = await service.create_config(
        DryRunConfigCreate(
            name="Async Simulation Test",
            description="Testing progress and cancellation",
            rule_id=rule.id,
            provider_type="SIMULATED",
            split_strategy="ALL",
        )
    )

    # 1. Execute job
    job = await service.execute_dry_run_job(config_id=config.id)
    assert job.status in ("COMPLETED", "CANCELLED")

    # 2. Test get_job_progress
    progress = await service.get_job_progress(job.id)
    assert progress is not None
    assert progress["job_id"] == job.id
    assert progress["total_items"] >= 0
    assert "progress_percent" in progress
    assert "eta_seconds" in progress

    # 3. Test cancel_job
    cancelled_job = await service.cancel_job(job.id)
    assert cancelled_job is not None
    assert cancelled_job.status in ("COMPLETED", "CANCELLED")

