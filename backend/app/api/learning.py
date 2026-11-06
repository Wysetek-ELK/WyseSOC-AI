from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.services.learning_service import LearningService
from app.services.audit_service import AuditService
from app.schemas.learning import (
    LearningRecordResponse,
    LearningListResponse,
    SimilarCaseQuery,
    SimilarCaseMatch,
)

router = APIRouter(prefix="/learning", tags=["Learning History"])


@router.get("/records", response_model=LearningListResponse)
async def list_learning_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rule_id: Optional[str] = None,
    verification_status: Optional[str] = None,
    verdict: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = LearningService(db)
    items, total = await service.list_records(
        page=page,
        page_size=page_size,
        rule_id=rule_id,
        verification_status=verification_status,
        verdict=verdict,
        search=search,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return LearningListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/records/{id}", response_model=LearningRecordResponse)
async def get_learning_record(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = LearningService(db)
    rec = await service.get_record(id)
    if not rec:
        raise HTTPException(status_code=404, detail="Learning record not found")
    return rec


@router.post("/similar-cases", response_model=List[SimilarCaseMatch])
async def find_similar_cases(
    req: SimilarCaseQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = LearningService(db)
    matches = await service.find_similar_cases(req)
    return matches


@router.post("/seed-historical")
async def seed_historical_learning_records(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = LearningService(db)
    count = await service.seed_verified_cases_from_historical_incidents()

    audit = AuditService(db)
    await audit.log(
        action="HISTORICAL_LEARNING_CASES_SEEDED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="LearningRecord",
        entity_id="ALL",
        details={"seeded_count": count},
    )

    return {"status": "success", "seeded_count": count}

