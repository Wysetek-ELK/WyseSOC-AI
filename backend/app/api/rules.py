from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.rule import Rule
from app.models.incident import Incident
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.rule_learning import RuleLearningProfile
from app.schemas.rule import RuleResponse, RuleDetailResponse, RuleListResponse, RuleStatsResponse
from app.schemas.fortisiem import FortiSIEMRuleSyncResponse
from app.services.rule_parser import RuleParser
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/rules", tags=["SIEM Rules"])


@router.get("", response_model=RuleListResponse)
async def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    readiness: Optional[str] = Query(None),
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

    rule_ids = [rule.id for rule, _ in rows]
    prompts_map: Dict[str, RulePrompt] = {}
    snaps_map: Dict[str, RuleIntelligenceSnapshot] = {}
    qa_map: Dict[str, PolicyQualityAssessmentRecord] = {}
    profiles_map: Dict[str, RuleLearningProfile] = {}

    if rule_ids:
        p_res = await db.execute(
            select(RulePrompt).where(RulePrompt.rule_id.in_(rule_ids)).options(selectinload(RulePrompt.versions))
        )
        for rp in p_res.scalars().all():
            prompts_map[rp.rule_id] = rp

        s_res = await db.execute(
            select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id.in_(rule_ids))
        )
        for snap in s_res.scalars().all():
            snaps_map[snap.rule_id] = snap

        qa_res = await db.execute(
            select(PolicyQualityAssessmentRecord)
            .where(PolicyQualityAssessmentRecord.rule_id.in_(rule_ids))
            .order_by(desc(PolicyQualityAssessmentRecord.evaluated_at))
        )
        for qa in qa_res.scalars().all():
            if qa.rule_id not in qa_map:
                qa_map[qa.rule_id] = qa

        prof_res = await db.execute(
            select(RuleLearningProfile).where(RuleLearningProfile.rule_id.in_(rule_ids))
        )
        for prof in prof_res.scalars().all():
            if prof.rule_id not in profiles_map:
                profiles_map[prof.rule_id] = prof

    items: List[RuleResponse] = []
    for rule, inc_count in rows:
        rp = prompts_map.get(rule.id)
        versions = rp.versions if (rp and rp.versions) else []
        has_approved = any(v.status == "APPROVED" for v in versions)
        snap = snaps_map.get(rule.id)
        latest_qa = qa_map.get(rule.id)
        prof = profiles_map.get(rule.id)

        is_incomplete = (
            (snap and snap.definition_status in ("INCOMPLETE", "UNKNOWN"))
            or (latest_qa and any("G1" in str(b) or "DEFINITION" in str(b) for b in (latest_qa.blocking_issues or [])))
        )

        if is_incomplete:
            readiness_status = "INCOMPLETE"
        elif latest_qa and latest_qa.blocking_issues and len(latest_qa.blocking_issues) > 0:
            readiness_status = "BLOCKED"
        elif has_approved and rule.status == "ACTIVE":
            readiness_status = "ACTIVE"
        elif has_approved:
            readiness_status = "APPROVED"
        elif latest_qa and latest_qa.approval_eligible:
            readiness_status = "READY_FOR_APPROVAL"
        elif prof and prof.total_analyst_reviews > 0:
            readiness_status = "LEARNING"
        else:
            readiness_status = "INCOMPLETE"

        gates_passed = 0
        if latest_qa and latest_qa.gate_results:
            gates_passed = sum(
                1 for g in latest_qa.gate_results.values()
                if (g.get("status") if isinstance(g, dict) else getattr(g, "status", "")) == "PASSED"
            )
        elif has_approved:
            gates_passed = 8

        missing_cnt = len(latest_qa.blocking_issues) if latest_qa and latest_qa.blocking_issues else (1 if is_incomplete else 0)

        # Apply readiness filter if requested
        if readiness and readiness.upper() != "ALL":
            target_r = readiness.upper().strip()
            if target_r == "BLOCKED" and readiness_status not in ("BLOCKED", "INCOMPLETE"):
                continue
            elif target_r != "BLOCKED" and readiness_status != target_r:
                continue

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
                production_readiness_status=readiness_status,
                gates_passed_count=gates_passed,
                missing_requirements_count=missing_cnt,
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


@router.get("/stats", response_model=RuleStatsResponse)
async def get_rule_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated detection rule registry metrics:
    total rules ingested, active/inactive distribution, severity counts,
    linked incident coverage, and Prompt Studio governance.
    """
    from app.models.prompt import RulePrompt

    # 1. Total, Active, Inactive
    tot_q = await db.execute(select(func.count(Rule.id)))
    total_rules = tot_q.scalar_one() or 0

    act_q = await db.execute(select(func.count(Rule.id)).where(Rule.status == "ACTIVE"))
    active_rules = act_q.scalar_one() or 0
    inactive_rules = max(0, total_rules - active_rules)

    # 2. Severities
    crit_q = await db.execute(select(func.count(Rule.id)).where(Rule.severity == "CRITICAL"))
    critical_rules = crit_q.scalar_one() or 0

    high_q = await db.execute(select(func.count(Rule.id)).where(Rule.severity == "HIGH"))
    high_rules = high_q.scalar_one() or 0

    med_q = await db.execute(select(func.count(Rule.id)).where(Rule.severity == "MEDIUM"))
    medium_rules = med_q.scalar_one() or 0

    low_q = await db.execute(select(func.count(Rule.id)).where(Rule.severity == "LOW"))
    low_rules = low_q.scalar_one() or 0

    # 3. Incident linkages
    inc_cov_q = await db.execute(
        select(
            func.count(func.distinct(Incident.rule_id)).label("covered_rules"),
            func.count(Incident.id).label("total_incidents"),
        ).where(Incident.rule_id.is_not(None))
    )
    inc_row = inc_cov_q.one()
    rules_with_incidents = inc_row.covered_rules or 0
    total_linked_incidents = inc_row.total_incidents or 0

    # 4. Prompt Studio Governance
    prompt_q = await db.execute(select(func.count(func.distinct(RulePrompt.rule_id))))
    rules_with_prompts = prompt_q.scalar_one() or 0

    return RuleStatsResponse(
        total_rules=total_rules,
        active_rules=active_rules,
        inactive_rules=inactive_rules,
        critical_rules=critical_rules,
        high_rules=high_rules,
        medium_rules=medium_rules,
        low_rules=low_rules,
        rules_with_incidents=rules_with_incidents,
        total_linked_incidents=total_linked_incidents,
        rules_with_prompt_templates=rules_with_prompts,
    )


@router.post("/sync/fortisiem", response_model=FortiSIEMRuleSyncResponse)
async def sync_rules_from_fortisiem(
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Route alias matching documented specification: POST /api/rules/sync/fortisiem (REQ-08 / AV-015).
    Synchronizes detection rules from FortiSIEM Supervisor.
    """
    from app.services.fortisiem_service import FortiSIEMService
    service = FortiSIEMService(db)
    result = await service.sync_all_rules_from_siem()
    return FortiSIEMRuleSyncResponse(**result)


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


@router.get("/{identifier}/compiled-policy")
async def get_rule_compiled_policy(
    identifier: str,
    execution_mode: str = Query("LIVE"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the unified nine-section compiled investigation policy (P3-REQ-01).
    """
    stmt = select(Rule).where(
        or_(Rule.id == identifier, Rule.rule_id == identifier, Rule.event_type == identifier)
    )
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule '{identifier}' not found")

    from app.services.prompt_studio_service import PromptStudioService
    svc = PromptStudioService(db)
    compiled = await svc.compile_active_policy(rule.id, execution_mode=execution_mode)
    return compiled.model_dump()


@router.get("/{identifier}/calibration-report")
async def get_rule_calibration_report(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the empirical evaluation and honest calibration report for a rule (P3-REQ-07).
    """
    stmt = select(Rule).where(
        or_(Rule.id == identifier, Rule.rule_id == identifier, Rule.event_type == identifier)
    )
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule '{identifier}' not found")

    from app.services.calibration_evaluation_service import CalibrationEvaluationService
    report = await CalibrationEvaluationService.generate_rule_calibration_report(db, rule.id)
    return report.model_dump()


class RuleDefinitionImportRequest(BaseModel):
    definition_text: str = Field(..., description="Authoritative XML or JSON rule definition content")
    format_type: str = Field("XML", description="Format: 'XML' or 'JSON'")


@router.post("/{identifier}/import-definition")
async def import_rule_definition(
    identifier: str,
    payload: RuleDefinitionImportRequest,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Imports authoritative FortiSIEM XML/JSON rule definition (P3-REQ-01 / Root Cause Remediation).
    Updates definition_status to VERIFIED and stores authoritative detection conditions.
    """
    from app.services.fortisiem_service import FortiSIEMService
    svc = FortiSIEMService(db)
    result = await svc.import_authoritative_rule_definition(
        rule_identifier=identifier,
        definition_text=payload.definition_text,
        format_type=payload.format_type,
    )
    if not result or not result.get("success"):
        raise HTTPException(status_code=400, detail="Failed to import authoritative rule definition.")
    return result


