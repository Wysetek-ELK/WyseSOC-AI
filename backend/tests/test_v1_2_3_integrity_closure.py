import os
import shutil
import tempfile
import sqlite3
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, or_
from alembic.config import Config
from alembic import command

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.incident import Incident
from app.utils.security import get_password_hash, create_access_token
from app.services.migration_service import get_alembic_config

ADMIN_ID = "admin-user-001"
ANALYST_A_ID = "analyst-user-002"
TENANT_A_ANALYST_ID = "analyst-tenant-a-005"
TENANT_B_ANALYST_ID = "analyst-tenant-b-006"
DEFAULT_ANALYST_ID = "analyst-default-007"

HEAVY_TCP_RULE_ID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
HEAVY_TCP_V1_ID = "8a460ab8-5f06-4a90-b2d4-db958199d644"
HEAVY_TCP_V3_ID = "ec0cc351-8dd1-4026-9dc3-586387bb324c"


@pytest_asyncio.fixture(autouse=True)
async def setup_test_users_and_incidents():
    async with AsyncSessionLocal() as db:
        users = [
            (ADMIN_ID, "admin", "admin@verdictum.test", "Administrator", None),
            (ANALYST_A_ID, "analyst", "analyst@verdictum.test", "SOC Analyst", None),
            (TENANT_A_ANALYST_ID, "analyst_tenant_a", "analyst_a@tenant-a.test", "SOC Analyst", "TenantA"),
            (TENANT_B_ANALYST_ID, "analyst_tenant_b", "analyst_b@tenant-b.test", "SOC Analyst", "TenantB"),
            (DEFAULT_ANALYST_ID, "analyst_default", "analyst_def@default.test", "SOC Analyst", "DEFAULT"),
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

        # Ensure isolated test incidents
        inc_legacy_default = (await db.execute(select(Incident).where(Incident.incident_id == "inc-legacy-default-901"))).scalar_one_or_none()
        if not inc_legacy_default:
            inc_legacy_default = Incident(
                incident_id="inc-legacy-default-901",
                event_type="LEGACY_UNASSIGNED_EVENT",
                title="Legacy Unassigned Platform Incident",
                severity="HIGH",
                customer="DEFAULT",
                ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "Platform test incident"}
            )
            db.add(inc_legacy_default)

        inc_tenant_b = (await db.execute(select(Incident).where(Incident.incident_id == "inc-tenant-b-isolated-202"))).scalar_one_or_none()
        if not inc_tenant_b:
            inc_tenant_b = Incident(
                incident_id="inc-tenant-b-isolated-202",
                event_type="TENANT_B_ISOLATED_EVENT",
                title="Tenant B Sensitive Incident",
                severity="CRITICAL",
                customer="TenantB",
                ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "Internal Tenant B test system"}
            )
            db.add(inc_tenant_b)

        await db.commit()


def get_token(username: str, role: str, user_id: str, customer: str = None) -> str:
    payload = {"sub": user_id, "username": username, "role": role}
    if customer:
        payload["customer"] = customer
    return create_access_token(payload)


@pytest.mark.asyncio
async def test_01_canonical_readiness_response_metrics():
    """
    Verify readiness responses for Heavy TCP historical (v1) and candidate (v3) versions:
    - quality_score is defined float
    - readiness_score is defined float and equals quality_score
    - gates_evaluated == 8
    - blocking_requirements list populated
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Evaluate candidate v3
        v3_res = await ac.get(f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V3_ID}", headers=headers)
        assert v3_res.status_code == 200, f"v3 query failed: {v3_res.text}"
        v3_data = v3_res.json()
        assert v3_data["quality_score"] is not None, "v3 quality_score must not be None"
        assert v3_data["readiness_score"] is not None, "v3 readiness_score must not be None"
        assert v3_data["quality_score"] == v3_data["readiness_score"], "quality_score and readiness_score must be synchronized"
        assert v3_data["quality_score"] == 77.0, f"Expected 77.0, got {v3_data['quality_score']}"
        assert v3_data["total_quality_gates"] == 8
        assert v3_data["quality_gates_passed"] == 6
        assert v3_data["readiness_status"] == "BLOCKED"
        assert len(v3_data["blocking_requirements"]) > 0

        # 2. Evaluate historical v1
        v1_res = await ac.get(f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V1_ID}", headers=headers)
        assert v1_res.status_code == 200, f"v1 query failed: {v1_res.text}"
        v1_data = v1_res.json()
        assert v1_data["quality_score"] is not None, "v1 quality_score must not be None"
        assert v1_data["readiness_score"] is not None, "v1 readiness_score must not be None"
        assert v1_data["quality_score"] == v1_data["readiness_score"]
        assert v1_data["quality_score"] == 54.0, f"Expected 54.0, got {v1_data['quality_score']}"
        assert v1_data["total_quality_gates"] == 8
        assert v1_data["quality_gates_passed"] == 2
        assert v1_data["readiness_status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_02_fail_closed_legacy_default_incident_isolation():
    """
    Verify fail-closed isolation:
    Tenant A analyst CANNOT access legacy DEFAULT or unassigned incidents across any endpoint.
    Platform DEFAULT analyst CAN access DEFAULT incidents, but CANNOT access Tenant B incidents.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_tenant_a = get_token("analyst_tenant_a", "SOC Analyst", TENANT_A_ANALYST_ID, customer="TenantA")
        token_default = get_token("analyst_default", "SOC Analyst", DEFAULT_ANALYST_ID, customer="DEFAULT")

        # 1. Tenant A accessing DEFAULT incident -> 403 Forbidden
        res_det = await ac.get("/api/incidents/inc-legacy-default-901", headers={"Authorization": f"Bearer {token_tenant_a}"})
        assert res_det.status_code == 403, f"Expected 403 for Tenant A on DEFAULT incident, got {res_det.status_code}"
        assert "Access denied" in res_det.json()["detail"]

        # 2. Tenant A timeline on DEFAULT incident -> 403 Forbidden
        res_tl = await ac.get("/api/incidents/inc-legacy-default-901/timeline", headers={"Authorization": f"Bearer {token_tenant_a}"})
        assert res_tl.status_code == 403, f"Expected 403, got {res_tl.status_code}"

        # 3. Tenant A review submit on DEFAULT incident -> 403 Forbidden
        res_rev = await ac.post(
            "/api/reviews/inc-legacy-default-901/submit",
            json={"analyst_verdict": "FALSE_POSITIVE", "analyst_notes": "Attempted unauthorized review"},
            headers={"Authorization": f"Bearer {token_tenant_a}"}
        )
        assert res_rev.status_code == 403, f"Expected 403, got {res_rev.status_code}"

        # 4. Tenant A prompt export on DEFAULT incident -> 403 Forbidden
        res_exp = await ac.get(
            "/api/prompts/actual-prompt/incident/inc-legacy-default-901/export",
            headers={"Authorization": f"Bearer {token_tenant_a}"}
        )
        assert res_exp.status_code == 403, f"Expected 403, got {res_exp.status_code}"

        # 5. DEFAULT Analyst accessing Tenant B incident -> 403 Forbidden
        res_def_b = await ac.get("/api/incidents/inc-tenant-b-isolated-202", headers={"Authorization": f"Bearer {token_default}"})
        assert res_def_b.status_code == 403, f"Expected 403, got {res_def_b.status_code}"
        assert "Access denied" in res_def_b.json()["detail"]


@pytest.mark.asyncio
async def test_03_cross_tenant_denial_across_all_endpoints():
    """
    Verify complete cross-tenant boundary: Tenant A vs Tenant B
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_tenant_a = get_token("analyst_tenant_a", "SOC Analyst", TENANT_A_ANALYST_ID, customer="TenantA")
        headers = {"Authorization": f"Bearer {token_tenant_a}"}

        # Detail
        res = await ac.get("/api/incidents/inc-tenant-b-isolated-202", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]

        # Timeline
        res = await ac.get("/api/incidents/inc-tenant-b-isolated-202/timeline", headers=headers)
        assert res.status_code == 403

        # Review submit
        res = await ac.post(
            "/api/reviews/inc-tenant-b-isolated-202/submit",
            json={"analyst_verdict": "FALSE_POSITIVE"},
            headers=headers
        )
        assert res.status_code == 403

        # Prompt export
        res = await ac.get("/api/prompts/actual-prompt/incident/inc-tenant-b-isolated-202/export", headers=headers)
        assert res.status_code == 403


def test_04_alembic_migration_013_idempotency_and_rollback():
    """
    Verify Alembic migration 013 (users.customer column and index) on an isolated database.
    Ensures safe upgrade, downgrade, and re-upgrade.
    """
    import importlib.util
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location("mig013", "backend/alembic/versions/013_user_tenant_customer.py")
    mig013 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig013)

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                email VARCHAR(128) UNIQUE NOT NULL,
                hashed_password VARCHAR(256) NOT NULL,
                full_name VARCHAR(128),
                role VARCHAR(32) NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))

        ctx = MigrationContext.configure(conn)
        mig013.op._proxy = Operations(ctx)

        # 1. Upgrade
        mig013.upgrade()
        insp = sa.inspect(conn)
        cols = [c["name"] for c in insp.get_columns("users")]
        indexes = [ix["name"] for ix in insp.get_indexes("users")]
        assert "customer" in cols, "customer column missing after upgrade!"
        assert "ix_users_customer" in indexes, "ix_users_customer missing after upgrade!"

        # 2. Downgrade
        mig013.downgrade()
        insp = sa.inspect(conn)
        cols = [c["name"] for c in insp.get_columns("users")]
        indexes = [ix["name"] for ix in insp.get_indexes("users")]
        assert "customer" not in cols, "customer column present after downgrade!"
        assert "ix_users_customer" not in indexes, "ix_users_customer present after downgrade!"

        # 3. Re-upgrade (idempotency check)
        mig013.upgrade()
        insp = sa.inspect(conn)
        cols = [c["name"] for c in insp.get_columns("users")]
        assert "customer" in cols, "customer column missing after re-upgrade!"
