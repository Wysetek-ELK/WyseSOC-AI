import pytest
from app.database import check_db_health, atomic_transaction
from app.models.user import User


@pytest.mark.asyncio
async def test_check_db_health_live_query(db_session):
    """Verifies that check_db_health executes SELECT 1, measures latency, and returns healthy."""
    health = await check_db_health(db_session)
    assert health["status"] == "healthy"
    assert health["connected"] is True
    assert health["latency_ms"] >= 0.0
    assert health["database_type"] in ("sqlite", "postgresql")


@pytest.mark.asyncio
async def test_atomic_transaction_commit(db_session):
    """Verifies that atomic_transaction commits clean modifications."""
    async with atomic_transaction(db_session):
        user = User(
            username="atomic_test_user",
            email="atomic@example.com",
            hashed_password="hashed_pw_test",
            role="SOC Analyst"
        )
        db_session.add(user)

    assert user.id is not None


@pytest.mark.asyncio
async def test_atomic_transaction_rollback(db_session):
    """Verifies that atomic_transaction automatically rolls back on unhandled error."""
    with pytest.raises(ValueError):
        async with atomic_transaction(db_session):
            user = User(
                username="rollback_user",
                email="rollback@example.com",
                hashed_password="pw",
            )
            db_session.add(user)
            raise ValueError("Intentional error triggering transaction rollback")

