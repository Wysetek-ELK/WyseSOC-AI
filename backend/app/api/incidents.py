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
from app.services.model_provider.factory import get_model_provider
from app.models.prompt import RulePrompt
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


@router.post("/{identifier}/ai-verdict")
async def request_incident_ai_verdict(
    identifier: str,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand single incident AI evaluation against Server 2 Local LLM.
    Strictly sanitizes telemetry through the ground-truth isolation allowlist.
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

    # 1. Build model-facing payload (sanitized of ground-truth closure fields)
    payload_dict = build_model_facing_payload(
        incident=incident,
        rule=incident.rule,
        events=incident.events
    )

    # 2. Resolve prompt text
    prompt_text = "Perform standard Level-2 SOC incident investigation and threat evaluation."
    prompt_ver_num = 1
    if incident.rule_id:
        rp_q = await db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == incident.rule_id).options(selectinload(RulePrompt.versions))
        )
        rp = rp_q.scalars().first()
        if rp and rp.versions:
            active_v = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])
            prompt_text = f"{active_v.common_prompt}\n\n{active_v.rule_specific_prompt}"
            prompt_ver_num = active_v.version_number

    # 3. Call Server 2 Local LLM Provider
    rule_spec = {
        "id": incident.rule.id if incident.rule else (incident.rule_id or "UNKNOWN"),
        "name": incident.rule.name if incident.rule else incident.title,
        "severity": incident.rule.severity if incident.rule else incident.severity,
        "description": incident.rule.description if incident.rule else "",
    }

    provider = get_model_provider("OPENAI_COMPATIBLE")
    verdict = await provider.analyze_incident(
        incident_payload=payload_dict,
        rule_spec=rule_spec,
        prompt_text=prompt_text,
        prompt_version_number=prompt_ver_num,
    )

    # 4. Audit log the AI verdict request
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="AI_VERDICT_REQUEST",
        resource_type="INCIDENT",
        resource_id=incident.incident_id,
        details={
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "latency_ms": verdict.latency_ms,
            "model": verdict.model_identifier,
            "is_simulated": verdict.is_simulated,
        },
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(audit)
    await db.commit()

    return {
        "incident_id": incident.incident_id,
        "verdict": verdict.verdict,
        "confidence": verdict.confidence,
        "reason": verdict.reason,
        "supporting_evidence": verdict.supporting_evidence,
        "missing_evidence": verdict.missing_evidence,
        "analyst_questions": verdict.analyst_questions,
        "latency_ms": verdict.latency_ms,
        "model_identifier": verdict.model_identifier,
        "is_simulated": verdict.is_simulated,
        "rule_name": incident.rule.name if incident.rule else incident.title,
        "severity": incident.severity,
    }

