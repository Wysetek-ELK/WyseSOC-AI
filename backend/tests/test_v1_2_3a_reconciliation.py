import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token

ADMIN_ID = "admin-user-001"
ANALYST_A_ID = "analyst-user-002"
HEAVY_TCP_RULE_ID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
HEAVY_TCP_V1_ID = "8a460ab8-5f06-4a90-b2d4-db958199d644"
HEAVY_TCP_V3_ID = "ec0cc351-8dd1-4026-9dc3-586387bb324c"
NONEXISTENT_RULE_ID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_VERSION_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


@pytest_asyncio.fixture(autouse=True)
async def ensure_test_users():
    async with AsyncSessionLocal() as db:
        users = [
            (ADMIN_ID, "admin", "admin@verdictum.test", "Administrator", None),
            (ANALYST_A_ID, "analyst", "analyst@verdictum.test", "SOC Analyst", None),
        ]
        for uid, uname, uemail, urole, ucustomer in users:
            res = await db.execute(select(User).where(User.username == uname))
            u = res.scalar_one_or_none()
            if not u:
                u = User(
                    id=uid,
                    username=uname,
                    email=uemail,
                    hashed_password=get_password_hash("AnalystPassword123!"),
                    role=urole,
                    customer=ucustomer,
                    is_active=True,
                )
                db.add(u)
            else:
                u.id = uid
                u.role = urole
                u.customer = ucustomer
                db.add(u)
        await db.commit()


def get_token(username: str, role: str, user_id: str) -> str:
    return create_access_token({"sub": user_id, "username": username, "role": role})


@pytest.mark.asyncio
async def test_01_readiness_score_mathematical_parity_and_breakdown():
    """
    Verify exact mathematical parity between quality_score, readiness_score,
    and the sum of individual gate scores across all evaluated quality gates.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        headers = {"Authorization": f"Bearer {token}"}

        res = await ac.get(
            f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V3_ID}",
            headers=headers,
        )
        assert res.status_code == 200, f"Readiness query failed: {res.text}"
        data = res.json()

        quality_score = data.get("quality_score")
        readiness_score = data.get("readiness_score")
        assert quality_score is not None, "quality_score must be defined"
        assert readiness_score is not None, "readiness_score must be defined"
        assert quality_score == readiness_score, "quality_score and readiness_score must be equal"

        # Gate score sum parity
        gate_results = data.get("gate_results") or {}
        assert len(gate_results) == 8, f"Expected 8 gates, found {len(gate_results)}"

        calculated_sum = round(sum(g.get("score", 0.0) for g in gate_results.values()), 1)
        assert quality_score == calculated_sum, (
            f"Mathematical discrepancy: quality_score ({quality_score}) != sum of gate scores ({calculated_sum})"
        )

        # Gate status and blocking requirements
        assert data.get("total_quality_gates") == 8
        assert data.get("quality_gates_passed") == 6
        assert data.get("readiness_status") == "BLOCKED"
        assert data.get("approval_eligible") is False
        assert len(data.get("blocking_requirements", [])) > 0


@pytest.mark.asyncio
async def test_02_readiness_nonexistent_rule_returns_404():
    """
    Verify that querying readiness for a nonexistent rule returns 404 Not Found
    and does NOT crash or return fabricated default readiness data.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        headers = {"Authorization": f"Bearer {token}"}

        res = await ac.get(
            f"/api/prompts/rule/{NONEXISTENT_RULE_ID}/readiness",
            headers=headers,
        )
        assert res.status_code == 404, f"Expected 404 for nonexistent rule, got {res.status_code}"
        err = res.json()
        assert "not found" in err.get("detail", "").lower() or "not found" in str(err).lower()


@pytest.mark.asyncio
async def test_03_readiness_nonexistent_version_returns_404():
    """
    Verify that querying readiness for a nonexistent version of an existing rule
    returns 404 Not Found and does NOT silently evaluate v1 or fallback to defaults.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        headers = {"Authorization": f"Bearer {token}"}

        res = await ac.get(
            f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={NONEXISTENT_VERSION_ID}",
            headers=headers,
        )
        assert res.status_code == 404, f"Expected 404 for nonexistent version, got {res.status_code}"
        err = res.json()
        assert "not found" in err.get("detail", "").lower() or "not found" in str(err).lower()
