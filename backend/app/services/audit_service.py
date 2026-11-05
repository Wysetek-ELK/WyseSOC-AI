from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        entity_type: str = "",
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=entity_type,
            resource_id=entity_id,
            details=details or {},
            ip_address=ip_address,
        )
        self.db.add(audit_entry)
        await self.db.commit()
        return audit_entry
