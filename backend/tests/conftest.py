import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend directory is in python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-fixture-minimum-32-chars-long-1234567890"

from app.config import settings
settings.APP_ENV = "testing"
settings.SECRET_KEY = "test-secret-key-fixture-minimum-32-chars-long-1234567890"
settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK = True

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    """Reset database schema cleanly before each individual test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="admin_test",
        email="admin_test@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Test",
        role="Administrator",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def analyst_user(db_session: AsyncSession) -> User:
    user = User(
        username="analyst_test",
        email="analyst_test@example.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Analyst Test",
        role="SOC Analyst",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        username="viewer_test",
        email="viewer_test@example.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Viewer Test",
        role="Read-Only Viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": admin_user.id, "username": admin_user.username, "role": admin_user.role})


@pytest.fixture
def analyst_token(analyst_user: User) -> str:
    return create_access_token({"sub": analyst_user.id, "username": analyst_user.username, "role": analyst_user.role})


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token({"sub": viewer_user.id, "username": viewer_user.username, "role": viewer_user.role})
