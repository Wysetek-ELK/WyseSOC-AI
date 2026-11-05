from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc

from app.database import get_db
from app.models.user import User
from app.models.rule import Rule
from app.models.incident import Incident
from app.schemas.rule import RuleResponse, RuleDetailResponse, RuleListResponse
from app.services.rule_parser import RuleParser
from app.api.deps import get_current_user

router = APIRouter(prefix="/rules", tags=["SIEM Rules"])


@router.get("", response_model=RuleListResponse)
async def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Subquery for incident count
    inc_count_subq = (
        select(Incident.rule_id, func.count(Incident.id).label("inc_count"))
        .group_by(Incident.rule_id)
        .subquery()
    )

    query = select(Rule, func.coalesce(inc_count_subq.c.inc_count, 0).label("incident_count")).outerjoin(
        inc_count_subq, Rule.id == inc_count_subq.c.rule_id
    )

    if severity:
        query = query.where(Rule.severity == severity.upper())

    if status:
        query = query.where(Rule.status == status.upper())

    if search:
        st = f"%{search.strip()}%"
        query = query.where(
            or_(
                Rule.name.ilike(st),
                Rule.rule_id.ilike(st),
                Rule.event_type.ilike(st),
                Rule.description.ilike(st),
                Rule.data_source.ilike(st),
            )
        )

    # Count total
    count_query = select(func.count(Rule.id))
    if severity:
        count_query = count_query.where(Rule.severity == severity.upper())
    if status:
        count_query = count_query.where(Rule.status == status.upper())
    if search:
        st = f"%{search.strip()}%"
        count_query = count_query.where(
            or_(
                Rule.name.ilike(st),
                Rule.rule_id.ilike(st),
                Rule.event_type.ilike(st),
                Rule.description.ilike(st),
                Rule.data_source.ilike(st),
            )
        )

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    query = query.order_by(desc(func.coalesce(inc_count_subq.c.inc_count, 0)), Rule.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items: List[RuleResponse] = []
    for rule, inc_count in rows:
        items.append(
            RuleResponse(
                id=rule.id,
                rule_id=rule.rule_id,
                name=rule.name,
                event_type=rule.event_type,
                description=rule.description,
                severity=rule.severity,
                status=rule.status,
                data_source=rule.data_source,
                detection_tech=rule.detection_tech,
                evaluation_mode=rule.evaluation_mode,
                pattern_logic=rule.pattern_logic,
                remediation=rule.remediation,
                raw_rule_text=rule.raw_rule_text,
                parsed_metadata=rule.parsed_metadata,
                incident_count=inc_count,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return RuleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{identifier}", response_model=RuleDetailResponse)
async def get_rule_detail(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Rule).where(
        or_(Rule.id == identifier, Rule.rule_id == identifier, Rule.event_type == identifier)
    )
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule '{identifier}' not found")

    # Get incident count
    inc_stmt = select(func.count(Incident.id)).where(
        or_(Incident.rule_id == rule.id, Incident.event_type == rule.event_type)
    )
    inc_count = (await db.execute(inc_stmt)).scalar_one()

    return RuleDetailResponse(
        id=rule.id,
        rule_id=rule.rule_id,
        name=rule.name,
        event_type=rule.event_type,
        description=rule.description,
        severity=rule.severity,
        status=rule.status,
        data_source=rule.data_source,
        detection_tech=rule.detection_tech,
        evaluation_mode=rule.evaluation_mode,
        pattern_logic=rule.pattern_logic,
        remediation=rule.remediation,
        raw_rule_text=rule.raw_rule_text,
        parsed_metadata=rule.parsed_metadata,
        incident_count=inc_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )
