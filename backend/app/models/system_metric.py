from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemServerSample(Base):
    __tablename__ = "system_server_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # "server-1" or "server-2"
    server_name: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ONLINE", nullable=False)

    # Core system utilization
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    memory_used_gb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    memory_total_gb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Storage utilization
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # GPU & Inference Telemetry (Server 2)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active_requests: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Extended metadata (loadavg, uptime, model identifier, etc.)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
