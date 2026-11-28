"""
AIS 3.2 — Verified Organizational Evidence Context Service.

PostgreSQL is the authoritative store (`OrganizationalContextRecord`).
Redis may cache verified tenant-scoped records with strict invalidation,
never serving as an independent source of truth.

Security & Epistemic Rules:
- Tenant-isolated by `customer`.
- Requires `verification_status == 'VERIFIED'` and `approval_status == 'APPROVED'`.
- Automatically excludes expired records (`valid_until < now`) or future records (`valid_from > now`).
- Internal IP != authorized; Public IP != malicious; Missing context -> UNKNOWN (never fabricated).
- Previous analyst verdicts MUST NEVER be imported as organizational context.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ais32_intelligence import OrganizationalContextRecord
from app.models.audit import AuditLog
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.org_context")

SUPPORTED_CONTEXT_TYPES = (
    "AUTHORIZED_SCANNER",
    "SECURITY_ASSESSMENT_SYSTEM",
    "INTERNAL_IP_RANGE",
    "ASSET_INVENTORY",
    "CRITICAL_ASSET",
    "SERVER_CLASSIFICATION",
    "SERVICE_ACCOUNT",
    "APPROVED_ADMIN_TOOL",
    "APPROVED_SOFTWARE",
    "CUSTOMER_EXCEPTION",
    "MAINTENANCE_WINDOW",
    "APPROVED_CONFIG_CHANGE",
    "IDENTITY_INFO",
    "NETWORK_ZONE",
    "APPROVED_EXTERNAL_DESTINATION",
    "AUTHORIZED_DATA_TRANSFER",
    "DEVICE_OWNERSHIP",
)


def _compute_dedup_hash(customer: str, context_type: str, context_value: str, match_pattern: str) -> str:
    norm = f"{customer.strip().lower()}|{context_type.strip().upper()}|{context_value.strip().lower()}|{match_pattern.strip().lower()}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _ip_matches_pattern(ip_str: str, pattern: str) -> bool:
    ip_clean = str(ip_str or "").strip()
    pat_clean = str(pattern or "").strip()
    if not ip_clean or not pat_clean:
        return False
    if ip_clean == pat_clean:
        return True
    try:
        ip_obj = ipaddress.ip_address(ip_clean)
        if "/" in pat_clean:
            net = ipaddress.ip_network(pat_clean, strict=False)
            return ip_obj in net
        return ip_obj == ipaddress.ip_address(pat_clean)
    except ValueError:
        return False


class OrganizationalContextService:
    """Tenant-isolated, approval-governed organizational knowledge provider."""

    _REDIS_PREFIX = "ais32:org_ctx"

    @classmethod
    def _get_redis(cls):
        try:
            import redis  # type: ignore
            return redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1.0)
        except Exception:
            return None

    @classmethod
    def invalidate_tenant_cache(cls, customer: str) -> None:
        r = cls._get_redis()
        if not r:
            return
        try:
            cust = (customer or "DEFAULT").strip()
            r.delete(f"{cls._REDIS_PREFIX}:{cust}:approved")
        except Exception:
            pass

    @classmethod
    async def create_context_record(
        cls,
        db: AsyncSession,
        *,
        customer: str,
        context_type: str,
        context_value: str,
        match_pattern: str = "",
        description: str = "",
        source_system: str = "MANUAL_ADMIN",
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        created_by: str = "admin",
        auto_approve: bool = False,
    ) -> OrganizationalContextRecord:
        ctype = str(context_type or "").upper().strip()
        if ctype not in SUPPORTED_CONTEXT_TYPES:
            raise ValueError(f"Unsupported organizational context_type '{context_type}'.")
        cval = str(context_value or "").strip()
        if not cval:
            raise ValueError("context_value must not be empty.")
        # Prevent importing analyst verdicts as organizational context
        src_u = str(source_system or "").upper().strip()
        if any(bad in src_u for bad in ("ANALYST_VERDICT", "GROUND_TRUTH", "HOLDOUT", "BENCHMARK_LABEL")):
            raise ValueError("Prohibited source_system: historical analyst verdicts cannot become organizational context.")

        cust = str(customer or "DEFAULT").strip() or "DEFAULT"
        pat = str(match_pattern or cval).strip()
        dhash = _compute_dedup_hash(cust, ctype, cval, pat)

        dup = (
            await db.execute(
                select(OrganizationalContextRecord).where(
                    OrganizationalContextRecord.customer == cust,
                    OrganizationalContextRecord.context_type == ctype,
                    OrganizationalContextRecord.dedup_hash == dhash,
                )
            )
        ).scalar_one_or_none()
        if dup:
            raise ValueError(
                f"Duplicate organizational context record already exists for tenant '{cust}' ({ctype}: '{cval}')."
            )

        now = utc_now()
        rec = OrganizationalContextRecord(
            customer=cust,
            context_type=ctype,
            context_value=cval,
            match_pattern=pat,
            dedup_hash=dhash,
            description=str(description or "").strip(),
            source_system=str(source_system or "MANUAL_ADMIN").strip(),
            verification_status="VERIFIED",
            approval_status="APPROVED" if auto_approve else "PENDING",
            approved_by=created_by if auto_approve else None,
            approved_at=now if auto_approve else None,
            valid_from=valid_from,
            valid_until=valid_until,
            record_version=1,
            metadata_json=dict(metadata_json or {}),
            created_by=created_by,
        )
        db.add(rec)
        db.add(
            AuditLog(
                username=created_by,
                action="ORG_CONTEXT_CREATED",
                resource_type="ORGANIZATIONAL_CONTEXT",
                resource_id=rec.id,
                details={
                    "customer": cust,
                    "context_type": ctype,
                    "context_value": cval,
                    "approval_status": rec.approval_status,
                },
            )
        )
        await db.commit()
        await db.refresh(rec)
        cls.invalidate_tenant_cache(cust)
        return rec

    @classmethod
    async def approve_or_revoke_record(
        cls,
        db: AsyncSession,
        *,
        record_id: str,
        action: str,
        actor_username: str,
        actor_customer: Optional[str] = None,
        is_admin: bool = False,
        reason: str = "",
    ) -> OrganizationalContextRecord:
        rec = (
            await db.execute(
                select(OrganizationalContextRecord).where(OrganizationalContextRecord.id == record_id)
            )
        ).scalar_one_or_none()
        if not rec:
            raise ValueError(f"Organizational context record '{record_id}' not found.")
        if not is_admin:
            raise PermissionError("Only Administrators may approve or revoke organizational context records.")
        if actor_customer and actor_customer != "DEFAULT" and rec.customer != actor_customer:
            raise PermissionError("Cross-tenant organizational context modification denied.")

        act = str(action or "").upper().strip()
        if act == "APPROVE":
            rec.approval_status = "APPROVED"
            rec.verification_status = "VERIFIED"
            rec.approved_by = actor_username
            rec.approved_at = utc_now()
            rec.record_version += 1
        elif act in ("REJECT", "REVOKE"):
            rec.approval_status = "REVOKED" if act == "REVOKE" else "REJECTED"
            rec.record_version += 1
        else:
            raise ValueError(f"Unsupported approval action '{action}'.")

        db.add(rec)
        db.add(
            AuditLog(
                username=actor_username,
                action=f"ORG_CONTEXT_{act}",
                resource_type="ORGANIZATIONAL_CONTEXT",
                resource_id=rec.id,
                details={"customer": rec.customer, "context_type": rec.context_type, "reason": reason},
            )
        )
        await db.commit()
        await db.refresh(rec)
        cls.invalidate_tenant_cache(rec.customer)
        return rec

    @classmethod
    async def list_records(
        cls,
        db: AsyncSession,
        *,
        customer: Optional[str] = None,
        context_type: Optional[str] = None,
        only_approved: bool = False,
    ) -> List[OrganizationalContextRecord]:
        stmt = select(OrganizationalContextRecord).order_by(desc(OrganizationalContextRecord.updated_at))
        if customer:
            stmt = stmt.where(OrganizationalContextRecord.customer == customer)
        if context_type:
            stmt = stmt.where(OrganizationalContextRecord.context_type == context_type.upper().strip())
        if only_approved:
            stmt = stmt.where(
                OrganizationalContextRecord.approval_status == "APPROVED",
                OrganizationalContextRecord.verification_status == "VERIFIED",
            )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def resolve_relevant_context(
        cls,
        db: Optional[AsyncSession],
        *,
        customer: Optional[str],
        allowed_context_types: List[str],
        observed_entities: Dict[str, Any],
        incident_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Queries verified, approved, non-expired organizational context strictly scoped to `customer`
        (plus global 'DEFAULT' ONLY if customer itself is 'DEFAULT' — never cross-tenant).
        Returns `context_status: "VERIFIED_MATCH"` or `"UNKNOWN"`.
        """
        tenant = str(customer or "DEFAULT").strip() or "DEFAULT"
        now = incident_timestamp or utc_now()

        if db is None:
            return {
                "tenant": tenant,
                "context_status": "UNKNOWN",
                "matched_records": [],
                "authorizes_activity": False,
                "summary": "Organizational context store unavailable; context status is UNKNOWN.",
            }

        # Strict tenant isolation: only query exact tenant
        rows = (
            await db.execute(
                select(OrganizationalContextRecord).where(
                    OrganizationalContextRecord.customer == tenant,
                    OrganizationalContextRecord.approval_status == "APPROVED",
                    OrganizationalContextRecord.verification_status == "VERIFIED",
                )
            )
        ).scalars().all()

        # Filter by allowed types and temporal validity
        allowed_set = {t.upper().strip() for t in allowed_context_types}
        ips = [str(x).strip() for x in (observed_entities.get("ips") or []) if x]
        domains = [str(x).strip().lower() for x in (observed_entities.get("domains") or []) if x]
        hosts = [str(x).strip().lower() for x in (observed_entities.get("hosts") or []) if x]
        users = [str(x).strip().lower() for x in (observed_entities.get("users") or []) if x]
        processes = [str(x).strip().lower() for x in (observed_entities.get("processes") or []) if x]
        rule_id = str(observed_entities.get("rule_id") or "").strip().lower()

        matched: List[Dict[str, Any]] = []
        authorizes_activity = False

        for rec in rows:
            if allowed_set and rec.context_type.upper() not in allowed_set:
                continue
            if rec.valid_from and now < rec.valid_from:
                continue
            if rec.valid_until and now > rec.valid_until:
                continue

            pat = (rec.match_pattern or rec.context_value or "").strip()
            val_l = rec.context_value.strip().lower()
            pat_l = pat.lower()

            hit_reason = None
            if any(_ip_matches_pattern(ip, pat) for ip in ips):
                hit_reason = f"IP match ({pat})"
            elif any(d == pat_l or d.endswith("." + pat_l) or pat_l in d for d in domains if pat_l):
                hit_reason = f"Domain match ({pat})"
            elif any(h == pat_l or pat_l in h for h in hosts if pat_l):
                hit_reason = f"Host match ({pat})"
            elif any(u == pat_l for u in users if pat_l):
                hit_reason = f"Identity/service account match ({pat})"
            elif any(p == pat_l or pat_l in p for p in processes if pat_l):
                hit_reason = f"Approved software/tool match ({pat})"
            elif rec.context_type in ("MAINTENANCE_WINDOW", "CUSTOMER_EXCEPTION", "APPROVED_CONFIG_CHANGE"):
                meta_rule = str((rec.metadata_json or {}).get("rule_id") or "").strip().lower()
                if meta_rule and rule_id and meta_rule == rule_id:
                    hit_reason = f"Active {rec.context_type} for rule {rule_id}"
                elif pat_l == "*" or (rule_id and pat_l == rule_id):
                    hit_reason = f"Active {rec.context_type}"

            if hit_reason:
                # INTERNAL_IP_RANGE, ASSET_INVENTORY, CRITICAL_ASSET, NETWORK_ZONE provide enrichment,
                # NOT automatic benign authorization!
                grants_auth = rec.context_type in (
                    "AUTHORIZED_SCANNER",
                    "SECURITY_ASSESSMENT_SYSTEM",
                    "APPROVED_ADMIN_TOOL",
                    "APPROVED_SOFTWARE",
                    "CUSTOMER_EXCEPTION",
                    "MAINTENANCE_WINDOW",
                    "APPROVED_CONFIG_CHANGE",
                    "APPROVED_EXTERNAL_DESTINATION",
                    "AUTHORIZED_DATA_TRANSFER",
                )
                if grants_auth:
                    authorizes_activity = True
                matched.append(
                    {
                        "id": rec.id,
                        "customer": rec.customer,
                        "context_type": rec.context_type,
                        "context_value": rec.context_value,
                        "source_system": rec.source_system,
                        "verification_status": rec.verification_status,
                        "approval_status": rec.approval_status,
                        "record_version": rec.record_version,
                        "grants_authorization": grants_auth,
                        "match_reason": hit_reason,
                        "valid_until": rec.valid_until.isoformat() if rec.valid_until else None,
                    }
                )

        if not matched:
            return {
                "tenant": tenant,
                "context_status": "UNKNOWN",
                "matched_records": [],
                "authorizes_activity": False,
                "summary": f"No verified organizational context matched for tenant '{tenant}'; authorization context is UNKNOWN.",
            }

        return {
            "tenant": tenant,
            "context_status": "VERIFIED_MATCH",
            "matched_records": matched,
            "authorizes_activity": authorizes_activity,
            "summary": f"Matched {len(matched)} verified organizational context record(s) for tenant '{tenant}'.",
        }
