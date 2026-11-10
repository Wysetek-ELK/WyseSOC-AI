"""
Database-backed distributed lock manager with optional Redis coordination.

Enables mutual exclusion for per-incident triage across multiple Uvicorn,
APScheduler, and Celery worker processes without requiring Redis to be online.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.config import settings
from app.models.distributed_lock import DistributedLock

logger = logging.getLogger("ai_verdict.distributed_lock")


def _extract_async_engine(db: Optional[AsyncSession]) -> Optional[AsyncEngine]:
    """Extracts the bound AsyncEngine from an AsyncSession when available."""
    if db is None:
        return None
    for candidate in (
        getattr(db, "bind", None),
        getattr(getattr(db, "sync_session", None), "bind", None),
    ):
        if isinstance(candidate, AsyncEngine):
            return candidate
        if isinstance(candidate, AsyncConnection):
            return candidate.engine
    try:
        sync_bind = db.get_bind()
        if isinstance(sync_bind, Engine) and getattr(sync_bind.dialect, "is_async", False):
            return AsyncEngine(sync_bind)
    except Exception:
        pass
    return None


def _is_in_memory_sqlite(engine: Optional[AsyncEngine]) -> bool:
    """Returns True when engine is an in-memory SQLite database (single process only)."""
    if engine is None:
        return True
    try:
        url_str = str(engine.url).lower()
        return url_str.startswith("sqlite") and (":memory:" in url_str or "mode=memory" in url_str)
    except Exception:
        return False


def _try_redis_acquire(lock_key: str, owner_id: str, ttl_ms: int) -> Optional[bool]:
    """
    Attempts atomic Redis SET NX PX when Redis is enabled/reachable.
    Returns True if acquired, False if held by another owner, None if Redis unavailable.
    """
    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url or not getattr(settings, "USE_ASYNC_CELERY", False):
        return None
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        acquired = client.set(f"lock:{lock_key}", owner_id, nx=True, px=max(1000, int(ttl_ms)))
        return bool(acquired)
    except Exception:
        return None


def _release_redis_lock(lock_key: str, owner_id: str) -> None:
    """Atomically releases Redis lock only if still owned by owner_id."""
    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url or not getattr(settings, "USE_ASYNC_CELERY", False):
        return
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        lua = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        client.eval(lua, 1, f"lock:{lock_key}", owner_id)
    except Exception:
        pass


class DistributedLockManager:
    """
    Cross-process distributed lease lock backed by the `distributed_locks` table
    (atomic UPSERT with TTL expiration check) plus optional Redis SET NX PX.
    """

    @classmethod
    @asynccontextmanager
    async def acquire(
        cls,
        db: Optional[AsyncSession],
        lock_key: str,
        ttl_seconds: int = 120,
        acquire_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.05,
    ) -> AsyncGenerator[str, None]:
        """
        Acquires an atomic per-key lease across OS processes and holds it for the
        duration of the context manager. Raises TimeoutError if contention exceeds timeout.
        """
        owner_id = f"owner-{uuid.uuid4().hex}"
        engine = _extract_async_engine(db)
        in_memory = _is_in_memory_sqlite(engine)
        use_db_lock = (engine is not None) and (not in_memory)

        clean_key = lock_key[:128]
        deadline = time.monotonic() + max(0.5, float(acquire_timeout_seconds))
        redis_acquired = False
        db_acquired = False

        try:
            while True:
                now = datetime.utcnow()
                expires = now + timedelta(seconds=max(5, int(ttl_seconds)))

                # Fast optional Redis coordination when async Celery/Redis is active
                r_res = _try_redis_acquire(clean_key, owner_id, ttl_seconds * 1000)
                if r_res is False:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out waiting for Redis distributed lock '{clean_key}'.")
                    await asyncio.sleep(poll_interval_seconds)
                    continue
                if r_res is True:
                    redis_acquired = True

                if not use_db_lock:
                    break

                try:
                    assert engine is not None
                    dialect_name = engine.dialect.name
                    insert_fn = pg_insert if "postgres" in dialect_name else sqlite_insert
                    stmt = insert_fn(DistributedLock).values(
                        lock_key=clean_key,
                        owner_id=owner_id,
                        acquired_at=now,
                        expires_at=expires,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[DistributedLock.lock_key],
                        set_={
                            "owner_id": stmt.excluded.owner_id,
                            "acquired_at": stmt.excluded.acquired_at,
                            "expires_at": stmt.excluded.expires_at,
                        },
                        where=(DistributedLock.expires_at <= now),
                    )
                    async with engine.begin() as conn:
                        await conn.execute(stmt)
                        owner_res = await conn.execute(
                            select(DistributedLock.owner_id).where(DistributedLock.lock_key == clean_key)
                        )
                        row_owner = owner_res.scalar_one_or_none()
                        if row_owner == owner_id:
                            db_acquired = True
                            break
                except (OperationalError, ProgrammingError) as exc:
                    msg = str(exc).lower()
                    if "no such table" in msg or "does not exist" in msg:
                        logger.debug(f"distributed_locks table missing ({exc}); relying on process lock.")
                        break
                    if "database is locked" in msg or "busy" in msg:
                        if redis_acquired:
                            _release_redis_lock(clean_key, owner_id)
                            redis_acquired = False
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"Timed out waiting for SQLite lock contention on '{clean_key}'.") from exc
                        await asyncio.sleep(poll_interval_seconds)
                        continue
                    raise

                # Another worker holds a valid non-expired DB lock
                if redis_acquired:
                    _release_redis_lock(clean_key, owner_id)
                    redis_acquired = False

                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for distributed DB lock '{clean_key}'.")
                await asyncio.sleep(poll_interval_seconds)

            yield owner_id
        finally:
            if db_acquired and engine is not None:
                try:
                    async with engine.begin() as conn:
                        await conn.execute(
                            delete(DistributedLock).where(
                                DistributedLock.lock_key == clean_key,
                                DistributedLock.owner_id == owner_id,
                            )
                        )
                except Exception as rel_exc:
                    logger.warning(f"Failed releasing DB distributed lock '{clean_key}': {rel_exc}")
            if redis_acquired:
                _release_redis_lock(clean_key, owner_id)
