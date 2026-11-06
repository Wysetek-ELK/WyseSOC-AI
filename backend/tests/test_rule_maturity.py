import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.services.maturity_service import RuleMaturityService


@pytest.mark.asyncio
async def test_rule_maturity_lifecycle_and_candidate_detection(db_session: AsyncSession):
    maturity_service = RuleMaturityService(db_session)

    # 1. New Rule starts at NOT_TESTED
    rule = Rule(
        id="RULE-MATURITY-01",
        rule_id="RULE-MATURITY-01",
        event_type="EndpointMalwareDetected",
        name="Endpoint Malware Detected",
        severity="CRITICAL",
    )
    db_session.add(rule)
    await db_session.commit()

    initial_eval = await maturity_service.get_or_create_evaluation(rule.id)
    assert initial_eval.maturity_status == "NOT_TESTED"
    assert initial_eval.is_admin_approved is False

    # 2. Add dry run job and 6 high-accuracy results (100% precision, 100% recall, 100% coverage, N=6)
    config = DryRunConfig(name="Cfg", rule_id=rule.id, provider_type="SIMULATED", split_strategy="ALL")
    db_session.add(config)
    await db_session.flush()

    job = DryRunJob(config_id=config.id, status="COMPLETED", total_items=6, processed_items=6, is_simulated=True)
    db_session.add(job)
    await db_session.flush()

    for i in range(6):
        inc = Incident(
            id=f"INC-MAT-{i+1}",
            incident_id=f"INC-MAT-{i+1}",
            rule_id=rule.id,
            event_type=rule.event_type,
            title=f"Incident {i+1}",
            severity="HIGH",
            customer="CrowdStrike",
        )
        db_session.add(inc)
        await db_session.flush()

        db_session.add(HistoricalGroundTruth(incident_id=inc.id, resolution="True Positive - Malware confirmed"))
        db_session.add(
            DryRunResult(
                job_id=job.id,
                incident_id=inc.id,
                predicted_verdict="TRUE_POSITIVE",
                confidence=95,
                reasoning="Confirmed signature",
                latency_ms=100,
                model_identifier="test-model",
                prompt_version_number=1,
                validation_status="VALID",
                is_simulated=True,
            )
        )

    await db_session.commit()

    # 3. Update maturity from results
    updated_eval = await maturity_service.update_rule_maturity_from_results(rule.id)
    # Meets thresholds: Precision 100% >= 95%, Recall 100% >= 90%, Coverage 100% >= 80%, N = 6 >= 5
    assert updated_eval.maturity_status == "CANDIDATE_FOR_AUTOMATION"
    assert updated_eval.is_admin_approved is False
    assert "Candidate for automation" in updated_eval.recommendation_explanation


@pytest.mark.asyncio
async def test_admin_approval_gate_and_rbac(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
    analyst_token: str,
):
    maturity_service = RuleMaturityService(db_session)

    rule = Rule(
        id="RULE-MATURITY-02",
        rule_id="RULE-MATURITY-02",
        event_type="SuspiciousLoginSequence",
        name="Suspicious Login Sequence",
        severity="MEDIUM",
    )
    db_session.add(rule)
    await db_session.commit()

    # Initial evaluation
    await maturity_service.get_or_create_evaluation(rule.id)

    # 1. Analyst attempts approval -> 403 Forbidden
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    fail_resp = await client.post(
        f"/api/evaluations/rule-maturity/{rule.id}/approve",
        headers=analyst_headers,
        json={"approval_notes": "Attempting signoff as analyst"},
    )
    assert fail_resp.status_code == 403

    # 2. Administrator approves -> 200 OK
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    success_resp = await client.post(
        f"/api/evaluations/rule-maturity/{rule.id}/approve",
        headers=admin_headers,
        json={"approval_notes": "Reviewed dry-run metrics, confirmed zero false negatives. Approved for dry-run tier 1 auto-triage."},
    )
    assert success_resp.status_code == 200
    data = success_resp.json()
    assert data["maturity_status"] == "APPROVED_FOR_AUTOMATION"
    assert data["is_admin_approved"] is True
    assert data["approved_by_username"] == "admin_test"
    assert "Reviewed dry-run metrics" in data["approval_notes"]
