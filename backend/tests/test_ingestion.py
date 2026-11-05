import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.ingestion_service import IngestionService
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.import_job import ImportJob

FIXTURE_ZIP_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip")
)


@pytest.mark.asyncio
async def test_real_zip_ingestion(db_session: AsyncSession):
    assert os.path.exists(FIXTURE_ZIP_PATH), f"Fixture zip missing at {FIXTURE_ZIP_PATH}"

    with open(FIXTURE_ZIP_PATH, "rb") as f:
        file_bytes = f.read()

    service = IngestionService(db_session)
    job, summary = await service.ingest_zip(
        file_bytes=file_bytes,
        filename="Incident json.zip",
        username="test_admin"
    )

    # 1. Verify job summary
    assert summary["status"] == "COMPLETED"
    assert summary["total_found"] == 22  # 20 JSON files + 2 Rule TXT files
    assert summary["rules_detected"] == 2
    assert summary["imported"] == 20
    assert summary["duplicates"] == 0
    assert summary["errors"] == 0

    # 2. Verify rules in database
    rule_res = await db_session.execute(select(Rule))
    rules = rule_res.scalars().all()
    assert len(rules) == 2
    rule_event_types = {r.event_type for r in rules}
    assert "PH_RULE_CS_SUSPICIOUS_ACTIVITY" in rule_event_types
    assert "Prisma_SASE_Suspicious_File_Threat_Detection_" in rule_event_types

    # 3. Verify incidents in database
    inc_res = await db_session.execute(select(Incident))
    incidents = inc_res.scalars().all()
    assert len(incidents) == 20

    # Check incident-to-rule linkage
    for inc in incidents:
        assert inc.rule_id is not None, f"Incident {inc.incident_id} failed to link to a rule!"

    # 4. Verify historical ground truth separation
    gt_res = await db_session.execute(select(HistoricalGroundTruth))
    gt_records = gt_res.scalars().all()
    assert len(gt_records) == 20

    tp_count = sum(1 for g in gt_records if "True Positive" in g.resolution)
    fp_count = sum(1 for g in gt_records if "False Positive" in g.resolution)
    assert tp_count == 10
    assert fp_count == 10

    # 5. Verify events in database
    event_res = await db_session.execute(select(func.count(IncidentEvent.id)))
    total_events = event_res.scalar_one()
    assert total_events > 50  # We know CrowdStrike and Prisma contain many events


@pytest.mark.asyncio
async def test_duplicate_handling(db_session: AsyncSession):
    with open(FIXTURE_ZIP_PATH, "rb") as f:
        file_bytes = f.read()

    service = IngestionService(db_session)

    # First ingestion: should import 20
    job1, summary1 = await service.ingest_zip(
        file_bytes=file_bytes,
        filename="Incident json.zip",
        username="test_admin"
    )
    assert summary1["imported"] == 20

    # Second ingestion: should detect all 20 as duplicates
    job2, summary2 = await service.ingest_zip(
        file_bytes=file_bytes,
        filename="Incident json.zip",
        username="test_admin"
    )

    assert summary2["imported"] == 0
    assert summary2["duplicates"] == 20
    assert summary2["errors"] == 0

    # Incident count in DB should remain exactly 20
    inc_count_res = await db_session.execute(select(func.count(Incident.id)))
    assert inc_count_res.scalar_one() == 20
