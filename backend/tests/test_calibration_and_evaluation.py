import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.incident import Incident, HistoricalGroundTruth
from app.schemas.calibration import DatasetSplitType, CalibrationStatus
from app.services.calibration_evaluation_service import CalibrationEvaluationService


def test_deterministic_dataset_partitioning():
    """Verify SHA-256 modulo deterministic 4-way dataset partitioning."""
    sample_ids = [f"INC-PARTITION-{i:04d}" for i in range(200)]
    partitions = [CalibrationEvaluationService.assign_dataset_partition(sid) for sid in sample_ids]

    # Determinism check: identical ID yields identical partition every time
    assert CalibrationEvaluationService.assign_dataset_partition("INC-FIXED-01") == CalibrationEvaluationService.assign_dataset_partition("INC-FIXED-01")

    # Distribution check across 200 samples
    train_count = sum(1 for p in partitions if p == DatasetSplitType.TRAIN)
    tuning_count = sum(1 for p in partitions if p == DatasetSplitType.TUNING)
    calib_count = sum(1 for p in partitions if p == DatasetSplitType.CALIBRATION)
    test_count = sum(1 for p in partitions if p == DatasetSplitType.LOCKED_TEST)

    assert train_count > 0
    assert tuning_count > 0
    assert calib_count > 0
    assert test_count > 0
    assert (train_count + tuning_count + calib_count + test_count) == 200


def test_honest_metrics_calculation_and_withholding():
    """Verify metrics calculation and honest withholding when sample size is insufficient."""
    # Under 30 samples (e.g. 10 cases)
    mock_evals = []
    for i in range(10):
        mock_evals.append({
            "predicted_verdict": "TRUE_POSITIVE" if i < 7 else "REQUIRES_ATTENTION",
            "ground_truth_verdict": "TRUE_POSITIVE" if i < 8 else "FALSE_POSITIVE",
            "confidence": 92.0,
        })

    metrics = CalibrationEvaluationService.calculate_metrics(mock_evals)
    assert metrics.ground_truth_available_count == 10
    assert metrics.tp_count == 7
    assert metrics.abstained_count == 3
    assert metrics.precision is not None
    assert metrics.recall is not None


@pytest.mark.asyncio
async def test_rule_calibration_report_service(db_session: AsyncSession):
    """Verify RuleCalibrationReport sets NOT_CALIBRATED when sample size < 30."""
    rule = Rule(
        id="rule-calib-test",
        rule_id="RULE-CALIB-01",
        name="Calibration Test Rule",
        event_type="Process",
    )
    db_session.add(rule)
    await db_session.flush()

    # Create 5 incidents with ground truth (under 30 threshold)
    for i in range(5):
        inc = Incident(
            incident_id=f"INC-CALIB-{i}",
            rule_id=rule.id,
            event_type="Process",
            title=f"Incident {i}",
            ai_verdict={"verdict": "TRUE_POSITIVE", "raw_model_confidence": 88.0, "confidence": 88.0},
        )
        db_session.add(inc)
        await db_session.flush()

        gt = HistoricalGroundTruth(
            incident_id=inc.id,
            resolution="True Positive",
            cleared_user="supervisor-01",
        )
        db_session.add(gt)

    await db_session.commit()

    report = await CalibrationEvaluationService.generate_rule_calibration_report(
        db=db_session,
        rule_id=rule.id,
    )

    assert report.sample_size == 5
    assert report.min_required_samples == 30
    assert report.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert "INSUFFICIENT_SAMPLE_SIZE" in report.honest_assessment_notes
    assert "confidence calibration is WITHHELD" in report.honest_assessment_notes


@pytest.mark.asyncio
async def test_calibration_api_endpoint(client: AsyncClient, db_session: AsyncSession, analyst_token: str):
    """Verify GET /api/rules/{id}/calibration-report endpoint."""
    rule = Rule(
        id="rule-calib-api",
        rule_id="RULE-CALIB-API",
        name="API Calibration Rule",
        event_type="Network",
    )
    db_session.add(rule)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = await client.get(f"/api/rules/{rule.id}/calibration-report", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["rule_id"] == rule.id
    assert data["calibration_status"] == "NOT_CALIBRATED"
    assert data["sample_size"] == 0
    assert "WITHHELD" in data["honest_assessment_notes"]
