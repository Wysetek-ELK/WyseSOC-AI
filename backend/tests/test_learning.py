import pytest
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident
from app.models.rule import Rule
from app.services.ingestion_service import IngestionService

ZIP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip"))


@pytest.mark.asyncio
async def test_learning_knowledge_base_and_similar_cases(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
    admin_token: str,
):
    # Ingest fixture data
    with open(ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    ingestor = IngestionService(db_session)
    await ingestor.ingest_zip(file_bytes=file_bytes, filename="Incident json.zip", username="test_admin")

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Seed historical verified learning cases
    seed_res = await client.post("/api/learning/seed-historical", headers=headers_admin)
    assert seed_res.status_code == 200
    assert seed_res.json()["seeded_count"] == 20

    # 2. List learning records
    list_res = await client.get("/api/learning/records", headers=headers_analyst)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 20
    assert len(data["items"]) == 20

    # Test filtering by verdict (TRUE_POSITIVE)
    tp_res = await client.get("/api/learning/records?verdict=TRUE_POSITIVE", headers=headers_analyst)
    assert tp_res.status_code == 200
    assert tp_res.json()["total"] == 10

    # 3. Test deterministic similar cases lookup
    inc_res = await db_session.execute(select(Incident))
    target_inc = inc_res.scalars().first()
    assert target_inc is not None

    sim_res = await client.post(
        "/api/learning/similar-cases",
        headers=headers_analyst,
        json={
            "incident_id": target_inc.id,
            "top_k": 5,
        }
    )
    assert sim_res.status_code == 200
    matches = sim_res.json()
    assert len(matches) > 0
    assert len(matches) <= 5
    # Ensure match_score is bounded between 0.0 and 1.0
    for m in matches:
        assert 0.0 <= m["match_score"] <= 1.0
        assert len(m["matched_features"]) > 0
        assert m["incident_id"] != target_inc.id  # Must not match itself
