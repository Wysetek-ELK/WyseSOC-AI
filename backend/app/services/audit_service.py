import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.config import settings
from app.models.audit import AuditLog


def get_audit_signing_key() -> bytes:
    """Returns the cryptographic signing key for audit trail HMAC."""
    key = settings.AUDIT_SIGNING_KEY or (settings.SECRET_KEY + ":audit-signature-salt-v1")
    return key.encode("utf-8")


def compute_audit_signature(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    created_at: datetime,
    details: Dict[str, Any],
) -> str:
    """
    Computes HMAC-SHA256 tamper-proof signature for an audit log entry.
    """
    key = get_audit_signing_key()
    details_str = json.dumps(details, sort_keys=True)
    msg = f"{user_id or ''}|{action}|{resource_type}|{resource_id or ''}|{created_at.isoformat()}|{details_str}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


class AuditService:
    KEY_ID = "hmac-sha256-v1"

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
        now = datetime.utcnow()
        safe_details = details or {}
        sig = compute_audit_signature(
            user_id=user_id,
            action=action,
            resource_type=entity_type,
            resource_id=entity_id,
            created_at=now,
            details=safe_details,
        )

        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=entity_type,
            resource_id=entity_id,
            details=safe_details,
            ip_address=ip_address,
            created_at=now,
            signature=sig,
            key_id=self.KEY_ID,
        )
        self.db.add(audit_entry)
        await self.db.commit()
        return audit_entry

    @classmethod
    def verify_record(cls, record: AuditLog) -> bool:
        """Verifies HMAC signature of a single audit log entry."""
        if not record.signature:
            return False  # Unsigned legacy entry
        expected = compute_audit_signature(
            user_id=record.user_id,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            created_at=record.created_at,
            details=record.details or {},
        )
        return hmac.compare_digest(record.signature, expected)

    async def verify_audit_integrity(self, limit: int = 500) -> Dict[str, Any]:
        """
        Scans recent audit records and verifies cryptographic integrity.
        Detects database tampering, unauthorized row modifications, or missing signatures.
        """
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        res = await self.db.execute(stmt)
        records = res.scalars().all()

        total = len(records)
        verified = 0
        tampered_ids: List[str] = []
        unsigned_ids: List[str] = []

        for r in records:
            if not r.signature:
                unsigned_ids.append(r.id)
            elif self.verify_record(r):
                verified += 1
            else:
                tampered_ids.append(r.id)

        is_tamper_free = len(tampered_ids) == 0
        return {
            "total_inspected": total,
            "verified_valid": verified,
            "tampered_count": len(tampered_ids),
            "tampered_ids": tampered_ids,
            "unsigned_count": len(unsigned_ids),
            "integrity_status": "VALID" if is_tamper_free else "TAMPER_DETECTED",
        }
