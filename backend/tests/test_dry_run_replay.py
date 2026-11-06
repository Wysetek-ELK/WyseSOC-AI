import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.dry_run import DryRunConfig, DryRunJob
from app.services.dry_run_service import DryRunService


async def create_sample_incidents(db: AsyncSession) -> Rule:
    rule = Rule(
        id="RULE-DRYRUN-01",
        rule_id="RULE-DRYRUN-01",
        event_type="EndpointSuspiciousActivity",
        name="Endpoint Suspicious Activity Rule",
        severity="HIGH",
        pattern_logic="Detects suspicious powershell and certutil executions",
    )
    db.add(rule)
    await db.commit()

    # Create 10 incidents across 3 hosts
    hosts = ["HOST-A", "HOST-B", "HOST-C"]
    for i in range(10):
        inc = Incident(
            id=f"INC-DR-{i+1:02d}",
            incident_id=f"INC-DR-{i+1:02d}",
            rule_id=rule.id,
            event_type=rule.event_type,
            title=f"Suspicious activity detection {i+1}",
            severity="HIGH" if i % 2 == 0 else "MEDIUM",
            customer="CrowdStrike",
            reporting_device=hosts[i % 3],
            created_at_epoch=1700000000 + (i * 3600),
            raw_payload={"detail": f"Incident detail {i+1}"},
        )
        db.add(inc)
        await db.flush()

        # Add event
        ev = IncidentEvent(
            incident_id=inc.id,
            event_type="ProcessCreate",
            raw_log=f"cmd.exe /c whoami on {hosts[i % 3]}",
            attributes={"CommandLine": "whoami.exe", "Host": hosts[i % 3]},
        )
        db.add(ev)

        # Ground truth
        resolution = "True Positive - Confirmed malicious activity" if i % 2 == 0 else "False Positive - Authorized maintenance"
        gt = HistoricalGroundTruth(
            incident_id=inc.id,
            resolution=resolution,
            cleared_reason="Analyst verified",
            comments=f"Detailed analyst notes {i+1}",
        )
        db.add(gt)

    await db.commit()
    return rule


@pytest.mark.asyncio
async def test_dataset_splitting_strategies(db_session: AsyncSession):
    rule = await create_sample_incidents(db_session)
    service = DryRunService(db_session)

    # Strategy: ALL
    all_split = await service.split_dataset("ALL", rule_id=rule.id)
    assert len(all_split) == 10

    # Strategy: CHRONOLOGICAL_70_30 (top 30% most recent)
    chrono_split = await service.split_dataset("CHRONOLOGICAL_70_30", rule_id=rule.id)
    assert len(chrono_split) == 3
    # Verify chronological ordering
    assert chrono_split[0].created_at_epoch > all_split[0].created_at_epoch

    # Strategy: GROUP_AWARE_HOST (groups by reporting_device)
    host_split = await service.split_dataset("GROUP_AWARE_HOST", rule_id=rule.id)
    assert 1 <= len(host_split) <= 10
    # Verify hosts in test set are grouped
    hosts_in_split = {inc.reporting_device for inc in host_split}
    assert len(hosts_in_split) >= 1


@pytest.mark.asyncio
async def test_dry_run_job_execution_api(client: AsyncClient, db_session: AsyncSession, analyst_token: str):
    rule = await create_sample_incidents(db_session)
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Create config
    config_resp = await client.post(
        "/api/dry-run/configs",
        headers=headers,
        json={
            "name": "Endpoint Activity Baseline Replay",
            "description": "Baseline simulation test for Rule 1",
            "rule_id": rule.id,
            "provider_type": "SIMULATED",
            "split_strategy": "ALL",
        },
    )
    assert config_resp.status_code == 201
    config_data = config_resp.json()
    config_id = config_data["id"]
    assert config_data["provider_type"] == "SIMULATED"

    # 2. Trigger dry-run job
    trigger_resp = await client.post(
        "/api/dry-run/trigger",
        headers=headers,
        json={"config_id": config_id, "custom_sample_limit": 6},
    )
    assert trigger_resp.status_code == 201
    job_data = trigger_resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "COMPLETED"
    assert job_data["total_items"] == 6
    assert job_data["processed_items"] == 6
    assert job_data["is_simulated"] is True

    # 3. Retrieve results
    results_resp = await client.get(f"/api/dry-run/jobs/{job_id}/results", headers=headers)
    assert results_resp.status_code == 200
    results = results_resp.json()
    assert len(results) == 6
    for r in results:
        assert r["job_id"] == job_id
        assert r["is_simulated"] is True
        assert r["validation_status"] == "VALID"
        assert r["predicted_verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
        assert r["ground_truth_verdict"] is not None
        assert "is_agreement" in r
