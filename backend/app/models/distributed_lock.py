from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DistributedLock(Base):
    """
    Database-backed distributed lease lock for coordinating multi-worker
    operations (e.g., per-incident VerdictTriageAgent evaluation) across
    multiple OS worker processes (Uvicorn workers, Celery workers, APScheduler).
    """

    __tablename__ = "distributed_locks"

    lock_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

