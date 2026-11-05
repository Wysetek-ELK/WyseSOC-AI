from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.api.deps import require_role

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if username:
        query = query.where(AuditLog.username.ilike(f"%{username}%"))

    # Count
    count_query = select(func.count(AuditLog.id))
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if username:
        count_query = count_query.where(AuditLog.username.ilike(f"%{username}%"))

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

