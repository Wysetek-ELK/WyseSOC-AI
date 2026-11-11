import uuid
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # LOGIN, LOGOUT, USER_CREATE, IMPORT, VIEW_INCIDENT, etc.
    resource_type: Mapped[str] = mapped_column(String(64), index=True, default="")  # INCIDENT, RULE, IMPORT_JOB, USER, SYSTEM
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    key_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)

