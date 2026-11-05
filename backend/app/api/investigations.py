from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.services.investigation_service import InvestigationService
from app.services.audit_service import AuditService
from app.schemas.investigation import (
    InvestigationQueueResponse,
    InvestigationDetailResponse,
    InvestigationListItem,
    InvestigationQuestionResponse,
    InvestigationEvidenceResponse,
    InvestigationAssignRequest,
    InvestigationStatusUpdate,
    AnalystVerdictSubmit,
    QuestionCreate,
    QuestionAnswer,
    EvidenceAttach,
)

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.get("/queue", response_model=InvestigationQueueResponse)
async def list_investigations_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    verdict: Optional[str] = None,
    is_disputed: Optional[bool] = None,
    rule_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = InvestigationService(db)
    items, total = await service.list_queue(
        page=page,
        page_size=page_size,
        status=status,
        assigned_to_user_id=assigned_to,
        analyst_verdict=verdict,
        is_disputed=is_disputed,
        rule_id=rule_id,
        search=search,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return InvestigationQueueResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{id}", response_model=InvestigationDetailResponse)
async def get_investigation(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = InvestigationService(db)
    inv = await service.get_by_id(id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    inc = inv.incident
    rule = inc.rule if inc else None
    user = inv.assigned_user

    return InvestigationDetailResponse(
        id=inv.id,
        incident_id=inv.incident_id,
        assigned_to_user_id=inv.assigned_to_user_id,
        assigned_to_username=user.username if user else None,
        status=inv.status,
        analyst_verdict=inv.analyst_verdict,
        verdict_reason=inv.verdict_reason,
        analyst_notes=inv.analyst_notes,
        is_disputed=inv.is_disputed,
        is_independently_verified=inv.is_independently_verified,
        insufficient_evidence_reason=inv.insufficient_evidence_reason,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        incident_vendor_id=inc.incident_id if inc else None,
        title=inc.title if inc else None,
        rule_id=rule.id if rule else (inc.rule_id if inc else None),
        rule_name=rule.name if rule else (inc.event_type if inc else None),
        severity=inc.severity if inc else None,
        event_type=inc.event_type if inc else None,
        source_ip=inc.source_ip if inc else None,
        reporting_device=inc.reporting_device if inc else None,
        questions=[InvestigationQuestionResponse.from_orm(q) for q in inv.questions],
        evidence_items=[InvestigationEvidenceResponse.from_orm(e) for e in inv.evidence_items],
    )


@router.get("/by-incident/{incident_id}", response_model=InvestigationDetailResponse)
async def get_investigation_by_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = InvestigationService(db)
    inv = await service.get_by_incident_id(incident_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Incident or investigation not found")

    inc = inv.incident
    rule = inc.rule if inc else None
    user = inv.assigned_user

    return InvestigationDetailResponse(
        id=inv.id,
        incident_id=inv.incident_id,
        assigned_to_user_id=inv.assigned_to_user_id,
        assigned_to_username=user.username if user else None,
        status=inv.status,
        analyst_verdict=inv.analyst_verdict,
        verdict_reason=inv.verdict_reason,
        analyst_notes=inv.analyst_notes,
        is_disputed=inv.is_disputed,
        is_independently_verified=inv.is_independently_verified,
        insufficient_evidence_reason=inv.insufficient_evidence_reason,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        incident_vendor_id=inc.incident_id if inc else None,
        title=inc.title if inc else None,
        rule_id=rule.id if rule else (inc.rule_id if inc else None),
        rule_name=rule.name if rule else (inc.event_type if inc else None),
        severity=inc.severity if inc else None,
        event_type=inc.event_type if inc else None,
        source_ip=inc.source_ip if inc else None,
        reporting_device=inc.reporting_device if inc else None,
        questions=[InvestigationQuestionResponse.from_orm(q) for q in inv.questions],
        evidence_items=[InvestigationEvidenceResponse.from_orm(e) for e in inv.evidence_items],
    )


@router.post("/{id}/assign")
async def assign_investigation(
    id: str,
    req: InvestigationAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    inv = await service.assign_analyst(id, req.user_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    audit = AuditService(db)
    await audit.log(
        action="INVESTIGATION_ASSIGNED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="Investigation",
        entity_id=id,
        details={"assigned_to_user_id": req.user_id},
    )

    return {"status": "success", "investigation_id": id, "assigned_to_user_id": req.user_id, "investigation_status": inv.status}


@router.post("/{id}/status")
async def update_investigation_status(
    id: str,
    req: InvestigationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    try:
        inv = await service.update_status(id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    audit = AuditService(db)
    await audit.log(
        action="INVESTIGATION_STATUS_CHANGED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="Investigation",
        entity_id=id,
        details={"new_status": inv.status},
    )

    return {"status": "success", "investigation_id": id, "new_status": inv.status}


@router.post("/{id}/questions", response_model=InvestigationQuestionResponse)
async def add_investigation_question(
    id: str,
    req: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    try:
        q = await service.add_question(id, req.question, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return InvestigationQuestionResponse.from_orm(q)


@router.post("/questions/{question_id}/answer", response_model=InvestigationQuestionResponse)
async def answer_investigation_question(
    question_id: str,
    req: QuestionAnswer,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    q = await service.answer_question(question_id, req.answer, current_user.id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    return InvestigationQuestionResponse.from_orm(q)


@router.post("/{id}/evidence", response_model=InvestigationEvidenceResponse)
async def attach_investigation_evidence(
    id: str,
    req: EvidenceAttach,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    try:
        ev = await service.attach_evidence(
            id,
            req.evidence_type,
            req.reference_key,
            req.evidence_content,
            req.analyst_rationale,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return InvestigationEvidenceResponse.from_orm(ev)


@router.post("/{id}/verdict")
async def submit_investigation_verdict(
    id: str,
    req: AnalystVerdictSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = InvestigationService(db)
    try:
        inv = await service.submit_verdict(id, req, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="INVESTIGATION_VERDICT_SUBMITTED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="Investigation",
        entity_id=id,
        details={
            "verdict": inv.analyst_verdict,
            "is_disputed": inv.is_disputed,
            "is_independently_verified": inv.is_independently_verified,
        },
    )

    return {
        "status": "success",
        "investigation_id": id,
        "analyst_verdict": inv.analyst_verdict,
        "investigation_status": inv.status,
        "is_disputed": inv.is_disputed,
        "is_independently_verified": inv.is_independently_verified,
    }
