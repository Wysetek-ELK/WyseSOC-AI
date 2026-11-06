import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.services.evaluation_service import EvaluationService, _safe_divide


def test_safe_divide_edge_cases():
    assert _safe_divide(0, 0) == 0.0
    assert _safe_divide(10, 0) == 0.0
    assert _safe_divide(5, 10) == 50.0
    assert _safe_divide(1, 3) == 33.33


@pytest.mark.asyncio
async def test_evaluation_metrics_calculation(client: AsyncClient, db_session: AsyncSession, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}

    rule = Rule(
        id="RULE-EVAL-01",
        rule_id="RULE-EVAL-01",
        event_type="EvalEventType",
        name="Evaluation Test Detection Rule",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.commit()

    config = DryRunConfig(
        name="Eval Config",
        rule_id=rule.id,
        provider_type="SIMULATED",
        split_strategy="ALL",
    )
    db_session.add(config)
    await db_session.flush()

    job = DryRunJob(
        config_id=config.id,
        status="COMPLETED",
        total_items=4,
        processed_items=4,
        is_simulated=True,
    )
    db_session.add(job)
    await db_session.flush()

    # Create 4 specific test incidents & results:
    # 1: GT=TP, Pred=TP (TP Agree)
    # 2: GT=TP, Pred=FP (False Negative for TP)
    # 3: GT=FP, Pred=FP (FP Agree)
    # 4: GT=TP, Pred=REQUIRES_ATTENTION (Abstention)
    cases = [
        ("INC-E1", "True Positive - Malicious", "TRUE_POSITIVE"),
        ("INC-E2", "True Positive - Malicious", "FALSE_POSITIVE"),
        ("INC-E3", "False Positive - Authorized test", "FALSE_POSITIVE"),
        ("INC-E4", "True Positive - Malicious", "REQUIRES_ATTENTION"),
    ]

    for inc_id, gt_res, pred in cases:
        inc = Incident(
            id=inc_id,
            incident_id=inc_id,
            rule_id=rule.id,
            event_type=rule.event_type,
            title=f"Incident {inc_id}",
            severity="HIGH",
            customer="Test",
        )
        db_session.add(inc)
        await db_session.flush()

        gt = HistoricalGroundTruth(
            incident_id=inc.id,
            resolution=gt_res,
        )
        db_session.add(gt)

        res = DryRunResult(
            job_id=job.id,
            incident_id=inc.id,
            predicted_verdict=pred,
            confidence=90 if pred != "REQUIRES_ATTENTION" else 50,
            reasoning="Test reason",
            latency_ms=120,
            model_identifier="test-model",
            prompt_version_number=1,
            validation_status="VALID",
            is_simulated=True,
        )
        db_session.add(res)

    await db_session.commit()

    # Retrieve metrics via API
    metrics_resp = await client.get(f"/api/evaluations/job/{job.id}/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()

    assert metrics["job_id"] == job.id
    assert metrics["total_evaluated"] == 4
    assert metrics["resolved_predictions"] == 3
    assert metrics["abstention_count"] == 1
    assert metrics["is_simulated"] is True

    # Check math:
    # Resolved = 3 (INC-E1, INC-E2, INC-E3)
    # Agreed = 2 (INC-E1, INC-E3)
    # Verdict Accuracy = 2/3 = 66.67%
    assert metrics["verdict_accuracy"] == 66.67

    # TP Precision: TP_agree(1) / Pred_TP(1) = 100.0%
    assert metrics["tp_precision"] == 100.0

    # FP Precision: FP_agree(1) / Pred_FP(2) = 50.0%
    assert metrics["fp_precision"] == 50.0

    # Abstention Coverage: 3/4 = 75.0%
    assert metrics["abstention_coverage"] == 75.0

    # Confusion Matrix
    cm = metrics["confusion_matrix"]
    assert cm["true_positive_as_tp"] == 1
    assert cm["true_positive_as_fp"] == 1
    assert cm["true_positive_as_abstain"] == 1
    assert cm["false_positive_as_fp"] == 1
    assert cm["false_positive_as_tp"] == 0

    # Test CSV Export
    csv_resp = await client.get(f"/api/evaluations/job/{job.id}/export/csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    csv_text = csv_resp.text
    assert "Incident ID,SIEM Rule,Event Type" in csv_text
    assert "INC-E1" in csv_text
    assert "AGREE" in csv_text

    # Test JSON Export
    json_resp = await client.get(f"/api/evaluations/job/{job.id}/export/json", headers=headers)
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers["content-type"]
    json_data = json_resp.json()
    assert json_data["job_id"] == job.id
    assert len(json_data["results"]) == 4
