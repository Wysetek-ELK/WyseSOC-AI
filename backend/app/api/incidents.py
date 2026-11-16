from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.rule import Rule
from app.models.learning import LearningRecord
from app.models.audit import AuditLog
from app.schemas.incident import (
    IncidentListResponse,
    IncidentDetailResponse,
    ModelFacingIncidentPayload,
)
from app.services.incident_service import IncidentService
from app.services.ai_verdict_service import AIVerdictService, LocalLLMUnavailableError
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.factory import get_model_provider
from app.services.prompt_studio_service import PromptStudioService, COMMON_SOC_BASELINE
from app.models.prompt import RulePrompt
from app.api.deps import get_current_user, require_analyst

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    exact_rule_id: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    blind_review: bool = Query(False, description="Hide ground truth for unbiased analyst review"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = IncidentService(db)
    items, total, rule_meta = await service.list_incidents_with_rule_summary(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        status=status,
        rule_id=rule_id,
        exact_rule_id=exact_rule_id,
        resolution=resolution,
        blind_review=blind_review,
        current_user=current_user,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        **rule_meta,
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
    incident = await service.get_incident(identifier, blind_review=blind_review, current_user=current_user)
    if not incident:
        user_customer = getattr(current_user, "customer", None)
        user_role = getattr(current_user, "role", "")
        if user_customer and user_customer != "DEFAULT" and user_role not in ("Administrator", "SuperAdmin"):
            other_stmt = select(Incident).where(or_(Incident.id == identifier, Incident.incident_id == identifier))
            other_inc = (await db.execute(other_stmt)).scalars().first()
            if other_inc and other_inc.customer and other_inc.customer not in (user_customer, "DEFAULT", ""):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Incident {identifier} belongs to customer '{other_inc.customer}', but user is restricted to '{user_customer}'."
                )
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
    try:
        from app.services.evidence_normalization_service import EvidenceNormalizationService
        norm_res = EvidenceNormalizationService.normalize_incident_evidence(
            incident=incident,
            events=incident.events or [],
        )
        payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_res.records]
    except Exception:
        payload_dict["canonical_evidence"] = []

    return ModelFacingIncidentPayload(**payload_dict)


@router.post("/{identifier}/ai-verdict")
async def request_incident_ai_verdict(
    identifier: str,
    request: Request = None,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand single incident AI evaluation against Verdictum Cortex (Server 2 Local LLM).
    Strictly sanitizes telemetry through the ground-truth isolation allowlist.
    """
    # Guard against double-blind review bypass:
    if current_user.role == "SOC Analyst":
        from app.models.analyst_feedback import AnalystVerdictReview
        inc_stmt = select(Incident).where((Incident.id == identifier) | (Incident.incident_id == identifier))
        inc_obj = (await db.execute(inc_stmt)).scalar_one_or_none()
        if inc_obj:
            user_filters = [
                AnalystVerdictReview.reviewer_id == str(current_user.id),
                AnalystVerdictReview.reviewer_id == str(current_user.username)
            ]
            rev_stmt = select(AnalystVerdictReview.id).where(
                or_(
                    AnalystVerdictReview.incident_id == str(inc_obj.id),
                    AnalystVerdictReview.incident_id == str(inc_obj.incident_id)
                ),
                or_(*user_filters)
            ).limit(1)
            has_rev = (await db.execute(rev_stmt)).scalar_one_or_none() is not None
            if not has_rev:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cannot invoke direct on-demand AI verdict for an unreviewed incident in double-blind mode. Submit your independent analyst determination first."
                )

    ai_service = AIVerdictService(db)
    try:
        verdict_data = await ai_service.evaluate_incident(
            incident_id_or_obj=identifier,
            username=current_user.username,
            allow_simulated_fallback=False,
        )
        return verdict_data
    except LocalLLMUnavailableError as llm_err:
        raise HTTPException(
            status_code=503,
            detail=f"Verdictum Cortex (Server 2) is offline: {str(llm_err)}. Incident is queued for automatic processing once Verdictum Cortex comes online.",
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI verdict evaluation failed: {str(exc)}")


@router.get("/{identifier}/timeline")
async def get_incident_historical_timeline(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the complete Historical Telemetry Timeline for an incident from Verdictum Core (Server 1) persistent storage,
    including raw event progression, SIEM correlation, and bifurcated token metrics.
    """
    from app.services.telemetry_timeline_service import TelemetryTimelineService
    svc = TelemetryTimelineService(db)
    result = await svc.get_incident_timeline(identifier, current_user=current_user)
    if not result.get("success"):
        if result.get("access_denied"):
            raise HTTPException(status_code=403, detail=result.get("error"))
        raise HTTPException(status_code=404, detail=result.get("error", "Incident timeline not found"))
    return result


