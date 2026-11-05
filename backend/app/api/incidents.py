from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.audit import AuditLog
from app.schemas.incident import (
    IncidentListResponse,
    IncidentDetailResponse,
    ModelFacingIncidentPayload,
)
from app.services.incident_service import IncidentService
from app.services.model_payload_allowlist import build_model_facing_payload
from app.api.deps import get_current_user

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    blind_review: bool = Query(False, description="Hide ground truth for unbiased analyst review"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = IncidentService(db)
    items, total = await service.list_incidents(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        status=status,
        rule_id=rule_id,
        resolution=resolution,
        blind_review=blind_review,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{identifier}", response_model=IncidentDetailResponse)
async def get_incident_detail(
    identifier: str,
    blind_review: bool = Query(False, description="Hide ground truth for unbiased analyst review"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = IncidentService(db)
    incident = await service.get_incident(identifier, blind_review=blind_review)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{identifier}' not found")

    # Audit incident inspection
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="VIEW_INCIDENT",
        resource_type="INCIDENT",
        resource_id=incident.incident_id,
        details={"blind_review": blind_review},
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(audit)
    await db.commit()

    return incident


@router.get("/{identifier}/model-payload", response_model=ModelFacingIncidentPayload)
async def get_incident_model_payload(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the strict allowlisted incident payload prepared for future model analysis.
    Verifies zero ground-truth leakage (excludes resolution, comments, clearedUser, clearedReason, etc.).
    """
    stmt = select(Incident).where(
        (Incident.id == identifier) | (Incident.incident_id == identifier)
    ).options(
        selectinload(Incident.rule),
        selectinload(Incident.events)
    )
    res = await db.execute(stmt)
    incident = res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{identifier}' not found")

    payload_dict = build_model_facing_payload(
        incident=incident,
        rule=incident.rule,
        events=incident.events
    )

    return ModelFacingIncidentPayload(**payload_dict)

