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


@pytest.mark.asyncio
async def test_extract_incident_timestamps_fortisiem_formats(db_session: AsyncSession):
    """
    Verifies that FortiSIEM timestamps across diverse formats (pub API fields,
    fixture formats, ISO strings, string epochs, and triggering events)
    are accurately parsed into milliseconds and populate occurrence time.
    """
    from app.services.ingestion_service import extract_incident_timestamps, IngestionService
    from app.services.incident_service import IncidentService

    # 1. FortiSIEM pub API format
    pub_data = {
        "incidentId": "200001",
        "eventType": "PH_RULE_TEST_PUB",
        "eventName": "Pub API Alert",
        "incidentFirstSeen": "1794056190000",
        "incidentLastSeen": 1794056290000,
        "incidentDetail": "test",
    }
    fs, ls, ca, ua = extract_incident_timestamps(pub_data)
    assert fs == 1794056190000
    assert ls == 1794056290000
    assert ca == 1794056190000  # Mutual fallback to first seen

    # 2. ISO date string format
    iso_data = {
        "incidentId": "200002",
        "eventType": "PH_RULE_TEST_ISO",
        "incidentTime": "2026-11-07T12:00:00Z",
    }
    fs2, ls2, ca2, _ = extract_incident_timestamps(iso_data)
    assert fs2 is not None
    assert fs2 > 1700000000000
    assert ca2 == fs2

    # 3. Triggering events fallback
    evt_data = {
        "incidentId": "200003",
        "eventType": "PH_RULE_TEST_EVT",
        "rawEvents": [
            {
                "eventId": "evt-1",
                "attribute": {"Event Receive Time": 1794056195000}
            }
        ]
    }
    fs3, ls3, ca3, _ = extract_incident_timestamps(evt_data)
    assert fs3 == 1794056195000
    assert ca3 == 1794056195000


@pytest.mark.asyncio
async def test_list_incidents_latest_on_top(db_session: AsyncSession):
    """
    Verifies that IncidentService.list_incidents orders incidents strictly
    with the latest incident occurrence time on top.
    """
    from app.services.ingestion_service import IngestionService
    from app.services.incident_service import IncidentService

    ingestion = IngestionService(db_session)

    # Ingest 3 incidents with distinct occurrence times
    t_old = 1700000000000
    t_mid = 1750000000000
    t_new = 1800000000000

    await ingestion.ingest_single_json(
        raw_data={
            "incidentId": "ORDER_MID",
            "eventType": "PH_RULE_ORDER_TEST",
            "eventName": "Order Test Alert",
            "incidentFirstSeen": t_mid,
            "status": 1,
        },
        filename="order_mid.json",
        username="test"
    )

    await ingestion.ingest_single_json(
        raw_data={
            "incidentId": "ORDER_OLD",
            "eventType": "PH_RULE_ORDER_TEST",
            "eventName": "Order Test Alert",
            "incidentFirstSeen": t_old,
            "status": 1,
        },
        filename="order_old.json",
        username="test"
    )

    await ingestion.ingest_single_json(
        raw_data={
            "incidentId": "ORDER_NEW",
            "eventType": "PH_RULE_ORDER_TEST",
            "eventName": "Order Test Alert",
            "incidentFirstSeen": t_new,
            "status": 1,
        },
        filename="order_new.json",
        username="test"
    )

    service = IncidentService(db_session)
    items, total = await service.list_incidents(page=1, page_size=10, search="ORDER_")

    assert total >= 3
    order_ids = [item.incident_id for item in items if item.incident_id.startswith("ORDER_")]
    assert order_ids == ["ORDER_NEW", "ORDER_MID", "ORDER_OLD"], f"Expected latest on top, got {order_ids}"


@pytest.mark.asyncio
async def test_fortisiem_raw_events_ingestion_and_self_healing(db_session: AsyncSession):
    """
    Verifies that raw security events with FortiSIEM live structure
    (rawMessage, attributes plural, receiveTime) are fully parsed,
    and existing incidents with empty events self-heal upon get_incident.
    """
    from app.services.ingestion_service import IngestionService
    from app.services.incident_service import IncidentService

    ingestion = IngestionService(db_session)
    live_raw_payload = {
        "incidentId": "300001",
        "eventType": "PH_RULE_LIVE_EVENT_TEST",
        "eventName": "Live Event Structure Test",
        "incidentFirstSeen": 1794056190000,
        "status": 1,
        "rawEvents": [
            {
                "id": 987654321,
                "eventType": "FortiGate-web-filter",
                "receiveTime": 1794056190000,
                "rawMessage": "<188>date=2026-11-06 time=23:17:11 devname=\"FW\" srcip=internal-client dstip=internal-server msg=\"blocked\"",
                "attributes": {
                    "Source Host": "internal-client",
                    "Destination Host": "internal-server",
                    "Event Receive Time": 1794056190000,
                    "Firewall Action": "blocked",
                }
            }
        ]
    }

    job, result, msg = await ingestion.ingest_single_json(
        raw_data=live_raw_payload,
        filename="live_event_test.json",
        username="admin"
    )
    assert result == "imported"

    service = IncidentService(db_session)
    detail = await service.get_incident("300001")
    assert detail is not None
    assert len(detail.events) == 1

    evt = detail.events[0]
    assert evt.event_id == "987654321"
    assert "blocked" in evt.raw_log
    assert evt.attributes.get("Source Host") == "internal-client"
    assert evt.attributes.get("Destination Host") == "internal-server"
    assert evt.event_receive_time == 1794056190000


