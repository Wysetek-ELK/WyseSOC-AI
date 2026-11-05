import pytest
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.learning import LearningRecord
from app.services.ingestion_service import IngestionService

ZIP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip"))


@pytest.mark.asyncio
async def test_investigation_queue_and_assignment(client: AsyncClient, db_session: AsyncSession, analyst_token: str, admin_token: str):
    # Ingest fixture data
    with open(ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    ingestor = IngestionService(db_session)
    await ingestor.ingest_zip(file_bytes=file_bytes, filename="Incident json.zip", username="test_admin")

    # 1. Check queue listing
    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = await client.get("/api/investigations/queue", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 20
    assert len(data["items"]) == 20
    assert data["items"][0]["status"] == "PENDING_REVIEW"

    inv_id = data["items"][0]["id"]
    incident_id = data["items"][0]["incident_id"]

    # 2. Assign investigation
    assign_res = await client.post(
        f"/api/investigations/{inv_id}/assign",
        headers=headers,
        json={"user_id": "test-analyst-uuid"}
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["investigation_status"] == "ASSIGNED"

    # 3. Add question
    q_res = await client.post(
        f"/api/investigations/{inv_id}/questions",
        headers=headers,
        json={"question": "Is the parent process a scheduled IT task?"}
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["question"] == "Is the parent process a scheduled IT task?"
    question_id = q_data["id"]

    # 4. Answer question
    ans_res = await client.post(
        f"/api/investigations/questions/{question_id}/answer",
        headers=headers,
        json={"answer": "Verified with SysAdmin: Not a scheduled enterprise task"}
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["answer"] == "Verified with SysAdmin: Not a scheduled enterprise task"

    # 5. Attach evidence
    ev_res = await client.post(
        f"/api/investigations/{inv_id}/evidence",
        headers=headers,
        json={
            "evidence_type": "TELEMETRY",
            "reference_key": "powershell.exe -enc",
            "evidence_content": "Base64 payload decoded to Cobalt Strike stager",
            "analyst_rationale": "Execution artifact shows direct C2 beaconing behavior"
        }
    )
    assert ev_res.status_code == 200
    assert ev_res.json()["reference_key"] == "powershell.exe -enc"


@pytest.mark.asyncio
async def test_analyst_verdict_and_ground_truth_isolation(client: AsyncClient, db_session: AsyncSession, analyst_token: str):
    # Ingest fixture data
    with open(ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    ingestor = IngestionService(db_session)
    await ingestor.ingest_zip(file_bytes=file_bytes, filename="Incident json.zip", username="test_admin")

    # Pick an incident with known historical ground truth
    res = await db_session.execute(select(Incident).join(Incident.ground_truth))
    inc = res.scalars().first()
    assert inc is not None

    gt_res = await db_session.execute(select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == inc.id))
    original_gt = gt_res.scalars().first()
    assert original_gt is not None
    original_resolution = original_gt.resolution
    original_comments = original_gt.comments

    # Get investigation
    headers = {"Authorization": f"Bearer {analyst_token}"}
    inv_res = await client.get(f"/api/investigations/by-incident/{inc.id}", headers=headers)
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    # Submit analyst verdict (e.g., TRUE_POSITIVE with verification)
    submit_res = await client.post(
        f"/api/investigations/{inv_id}/verdict",
        headers=headers,
        json={
            "analyst_verdict": "TRUE_POSITIVE",
            "verdict_reason": "Confirmed adversary C2 callback with decoded stager.",
            "analyst_notes": "Immediate endpoint isolation executed in dry-run mode.",
            "is_disputed": False,
            "is_independently_verified": True,
            "status": "REVIEWED"
        }
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["analyst_verdict"] == "TRUE_POSITIVE"
    assert submit_res.json()["is_independently_verified"] is True

    # VERIFY CRITICAL GROUND TRUTH ISOLATION:
    # Historical ground truth table must be 100% UNMODIFIED
    gt_check_res = await db_session.execute(select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == inc.id))
    post_gt = gt_check_res.scalars().first()
    assert post_gt.resolution == original_resolution
    assert post_gt.comments == original_comments

    # Verify LearningRecord was created from independently verified verdict
    lr_res = await db_session.execute(select(LearningRecord).where(LearningRecord.incident_id == inc.id))
    lr = lr_res.scalars().first()
    assert lr is not None
    assert lr.verified_verdict == "TRUE_POSITIVE"
    assert lr.verification_status == "VERIFIED"


@pytest.mark.asyncio
async def test_requires_attention_with_insufficient_evidence(client: AsyncClient, db_session: AsyncSession, analyst_token: str):
    # Ingest fixture data
    with open(ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    ingestor = IngestionService(db_session)
    await ingestor.ingest_zip(file_bytes=file_bytes, filename="Incident json.zip", username="test_admin")

    headers = {"Authorization": f"Bearer {analyst_token}"}
    queue_res = await client.get("/api/investigations/queue", headers=headers)
    inv_id = queue_res.json()["items"][1]["id"]

    # Submit REQUIRES_ATTENTION with explicit insufficient evidence reason
    res = await client.post(
        f"/api/investigations/{inv_id}/verdict",
        headers=headers,
        json={
            "analyst_verdict": "REQUIRES_ATTENTION",
            "verdict_reason": "Parent process telemetry was truncated by SIEM agent",
            "analyst_notes": "Needs full endpoint agent memory dump to confirm lineage",
            "insufficient_evidence_reason": "Command line is missing parent PPID and user session ID",
            "is_disputed": True,
            "is_independently_verified": False,
            "status": "REVIEWED"
        }
    )
    assert res.status_code == 200
    assert res.json()["analyst_verdict"] == "REQUIRES_ATTENTION"
    assert res.json()["is_disputed"] is True
