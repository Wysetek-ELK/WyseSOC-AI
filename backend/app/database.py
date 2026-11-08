import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from app.config import settings

# Engine configuration for PostgreSQL / SQLite
engine_kwargs: Dict[str, Any] = {"echo": False}

is_postgres = "postgres" in settings.DATABASE_URL
if is_postgres:
    # High-throughput PostgreSQL connection pool on Server 1
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    })
elif "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yielding a managed AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def atomic_transaction(session: AsyncSession):
    """
    Transactional Safety Context Manager:
    Safely scopes database operations in a transaction.
    If an existing transaction is open, creates a savepoint.
    Automatically rolls back on any error and commits on clean exit.
    """
    if session.in_transaction():
        async with session.begin_nested():
            yield session
    else:
        async with session.begin():
            yield session


async def check_db_health(session: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """
    Active database health probe:
    Executes SELECT 1, validates pool connectivity, and measures query latency.
    """
    start_time = time.perf_counter()
    db_type = "postgresql" if is_postgres else "sqlite"
    
    async def _execute_probe(s: AsyncSession) -> Dict[str, Any]:
        result = await s.execute(text("SELECT 1"))
        val = result.scalar()
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        if val != 1:
            raise ValueError(f"Unexpected health check response: {val}")
        
        pool_info: Dict[str, Any] = {}
        if hasattr(async_engine.sync_engine, "pool"):
            pool = async_engine.sync_engine.pool
            if hasattr(pool, "size"):
                pool_info = {
                    "pool_size": getattr(pool, "size", lambda: 0)(),
                    "checked_in": getattr(pool, "checkedin", lambda: 0)(),
                    "checked_out": getattr(pool, "checkedout", lambda: 0)(),
                    "overflow": getattr(pool, "overflow", lambda: 0)(),
                }

        return {
            "status": "healthy",
            "database_type": db_type,
            "latency_ms": elapsed_ms,
            "connected": True,
            "pool": pool_info
        }

    try:
        if session:
            return await _execute_probe(session)
        else:
            async with AsyncSessionLocal() as probe_session:
                return await _execute_probe(probe_session)
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "unhealthy",
            "database_type": db_type,
            "latency_ms": elapsed_ms,
            "connected": False,
            "error": str(e)
        }
