import pytest
from app.config import settings
from app.services.migration_service import (
    get_head_revision,
    get_current_db_revision,
    verify_schema_on_startup,
)


@pytest.mark.asyncio
async def test_get_head_revision_matches_current():
    """Verifies that the Alembic head revision matches the latest AIS 2.1 + Phase 8 migration."""
    head = get_head_revision()
    assert head == "007_distributed_locks"


@pytest.mark.asyncio
async def test_production_startup_blocks_unmigrated_db(db_session):
    """
    AV-012 Strict Compliance Test:
    In production mode, verify_schema_on_startup MUST fail with RuntimeError
    if the database is unmigrated or mismatched, and MUST NOT execute runtime DDL.
    """
    conn = await db_session.connection()
    # Mocking current DB revision as outdated or None
    class MockConn:
        async def execute(self, stmt):
            class MockRes:
                def fetchone(self):
                    return ("002_phase2_investigation_and_learning",)
            return MockRes()

    with pytest.raises(RuntimeError) as exc_info:
        await verify_schema_on_startup(conn=MockConn(), is_production=True, auto_migrate=False)

    assert "AV-012" in str(exc_info.value)
    assert "Runtime DDL is forbidden in production" in str(exc_info.value)


@pytest.mark.asyncio
async def test_development_startup_allows_clean_initialization(db_session):
    """In development/test mode, verify_schema_on_startup proceeds cleanly."""
    conn = await db_session.connection()
    head = get_head_revision()
    class MockConnHead:
        async def execute(self, stmt):
            class MockRes:
                def fetchone(self):
                    return (head,)
            return MockRes()

    ok, msg = await verify_schema_on_startup(conn=MockConnHead(), is_production=False, auto_migrate=False)
    assert ok is True
    assert "Database up to date" in msg
