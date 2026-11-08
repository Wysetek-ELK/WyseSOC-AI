from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.policy_drift import PolicyDriftEvent
from app.models.bulk_audit import BulkQualityAuditJobRecord
from app.services.prompt_studio_service import PromptStudioService
from app.services.audit_service import AuditService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.bulk_quality_audit_service import BulkQualityAuditService
from app.services.policy_lifecycle_monitor import PolicyLifecycleMonitor
from app.schemas.prompt import (
    RulePromptResponse,
    PromptVersionResponse,
    PromptVersionCreate,
    PromptApprovalRequest,
    PromptRollbackRequest,
    RulePromptSummaryItem,
)
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    ArchetypeClassificationResult,
)
from app.schemas.policy_quality import (
    PolicyQualityAssessmentResponse,
    QualitySummaryItem,
)

router = APIRouter(prefix="/prompts", tags=["Prompt Studio"])


@router.get("/summary", response_model=List[RulePromptSummaryItem])
async def get_rule_prompts_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns a unified summary of all SIEM detection rules alongside their
    current prompt engineering version status, detection archetype, quality score,
    validation status, and revalidation indicators.
    """
    rules_res = await db.execute(select(Rule).order_by(Rule.name.asc()))
    rules = rules_res.scalars().all()

    prompts_res = await db.execute(select(RulePrompt).options(selectinload(RulePrompt.versions)))
    prompts_by_rule_id = {rp.rule_id: rp for rp in prompts_res.scalars().all()}

    # Pre-fetch snapshots and drift events
    snaps_res = await db.execute(select(RuleIntelligenceSnapshot))
    snaps_by_rule_id = {s.rule_id: s for s in snaps_res.scalars().all()}

    drift_res = await db.execute(select(PolicyDriftEvent).where(PolicyDriftEvent.acknowledged == False))
    drift_rule_ids = {d.rule_id for d in drift_res.scalars().all()}

    items = []
    for r in rules:
        rp = prompts_by_rule_id.get(r.id)
        versions = rp.versions if (rp and rp.versions) else []
        active_v = next((v for v in versions if v.id == rp.active_version_id), None) if rp else None
        target_v = active_v or (versions[0] if versions else None)
        has_approved = any(v.status == "APPROVED" for v in versions)

        snap = snaps_by_rule_id.get(r.id)
        archetype = snap.primary_archetype if snap else "UNKNOWN"
        completeness = snap.definition_status if snap else "UNKNOWN"
        q_score = target_v.quality_score if target_v else None
        q_status = target_v.quality_status if target_v else "NOT_EVALUATED"

        revalidation_req = (r.id in drift_rule_ids) or (target_v and target_v.quality_status == "REVIEW_REQUIRED")

        items.append(
            RulePromptSummaryItem(
                rule_id=r.id,
                rule_name=r.name,
                event_type=r.event_type,
                severity=r.severity or "MEDIUM",
                status=r.status or "ACTIVE",
                data_source=r.data_source,
                prompt_id=rp.id if rp else None,
                active_version_number=active_v.version_number if active_v else (versions[0].version_number if versions else None),
                active_version_status=active_v.status if active_v else (versions[0].status if versions else None),
                total_versions=len(versions),
                has_approved_prompt=has_approved,
                last_updated=rp.updated_at if rp else r.updated_at,
                detection_archetype=archetype,
                definition_completeness=completeness,
                quality_score=q_score,
                quality_validation_status=q_status,
                blocking_issue_count=1 if (completeness == "INCOMPLETE" and not has_approved) else 0,
                simulation_status="NOT_EVALUATED",
                last_validated_date=snap.updated_at if snap else None,
                revalidation_required=revalidation_req,
            )
        )

    return items


@router.get("/export")
async def export_all_rule_prompts(
    format: str = Query("json", pattern="^(json|markdown|md)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Exports all SIEM detection rules alongside their active and historical
    investigative prompt configurations formatted rule-wise as JSON or Markdown.
    """
    service = PromptStudioService(db)
    content, media_type, filename = await service.export_all_rule_prompts(format=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/quality/summary", response_model=QualitySummaryItem)
async def get_policy_quality_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-09: Returns aggregated policy quality metrics, compliance distribution,
    and review backlog across the detection rule library.
    """
    bulk_svc = BulkQualityAuditService(db)
    return await bulk_svc.get_quality_summary()


@router.post("/quality/bulk-assess")
async def start_bulk_quality_audit(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Bulk audit trigger requires SOC Lead / Admin
):
    """
    REQ-09: Triggers a bounded, chunked bulk quality assessment across all 2,000+ SIEM detection rules.
    100% read-only with respect to active production policies.
    """
    bulk_svc = BulkQualityAuditService(db)
    job = await bulk_svc.execute_bulk_audit(user_id=current_user.id)
    return {
        "job_id": job.id,
        "status": job.status,
        "total_rules": job.total_rules,
        "processed_rules": job.processed_rules,
        "passed_count": job.passed_count,
        "review_required_count": job.review_required_count,
        "average_quality_score": job.average_quality_score,
        "summary_metrics": job.summary_metrics,
    }


@router.get("/quality/bulk-assess/{job_id}")
async def get_bulk_quality_audit_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-09: Returns the execution status and metrics of a bulk quality audit job.
    """
    q = select(BulkQualityAuditJobRecord).where(BulkQualityAuditJobRecord.id == job_id)
    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Bulk audit job {job_id} not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "total_rules": job.total_rules,
        "processed_rules": job.processed_rules,
        "passed_count": job.passed_count,
        "review_required_count": job.review_required_count,
        "critical_issues_count": job.critical_issues_count,
        "incomplete_definitions_count": job.incomplete_definitions_count,
        "missing_evidence_count": job.missing_evidence_count,
        "average_quality_score": job.average_quality_score,
        "summary_metrics": job.summary_metrics,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.get("/rule/{rule_id}", response_model=RulePromptResponse)
async def get_rule_prompt(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = PromptStudioService(db)
    try:
        prompt = await service.get_or_create_rule_prompt(rule_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    active_v = None
    if prompt.active_version_id and prompt.versions:
        for v in prompt.versions:
            if v.id == prompt.active_version_id:
                active_v = PromptVersionResponse.model_validate(v)
                break

    return RulePromptResponse(
        id=prompt.id,
        rule_id=prompt.rule_id,
        rule_name=prompt.rule.name if prompt.rule else None,
        rule_event_type=prompt.rule.event_type if prompt.rule else None,
        title=prompt.title,
        active_version_id=prompt.active_version_id,
        active_version=active_v,
        versions=[PromptVersionResponse.model_validate(v) for v in prompt.versions],
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.get("/rule/{rule_id}/intelligence")
async def get_rule_intelligence(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-01 / REQ-02: Returns structured detection semantics and archetype classification for a rule.
    """
    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)
    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def)

    return {
        "rule_id": rule.id,
        "rule_identifier": semantics.rule_identifier,
        "semantics": semantics.model_dump(mode="json"),
        "classification": classification.model_dump(mode="json"),
        "archetype_definition": archetype_def.model_dump(mode="json"),
        "candidate_evidence_contract": contract.model_dump(mode="json"),
    }


@router.post("/rule/{rule_id}/analyze")
async def analyze_rule_intelligence(
    rule_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    REQ-01: Re-analyzes rule semantics with optional authoritative SIEM rule definition.
    """
    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    authoritative_def = payload.get("authoritative_siem_definition") if payload else None
    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule, authoritative_siem_definition=authoritative_def)
    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)

    service = PromptStudioService(db)
    await service._persist_rule_intelligence_snapshot(rule, semantics)

    return {
        "rule_id": rule.id,
        "rule_identifier": semantics.rule_identifier,
        "semantics": semantics.model_dump(mode="json"),
        "classification": classification.model_dump(mode="json"),
    }


@router.post("/rule/{rule_id}/generate-intelligent-draft", response_model=PromptVersionResponse)
async def generate_intelligent_draft(
    rule_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    REQ-04: Synthesizes a detection-aware, archetype-aligned nine-section policy draft.
    Remains strictly in DRAFT status.
    """
    service = PromptStudioService(db)
    authoritative_def = payload.get("authoritative_siem_definition") if payload else None
    try:
        ver = await service.generate_template_draft(
            rule_id=rule_id,
            user_id=current_user.id,
            authoritative_siem_definition=authoritative_def,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="PROMPT_INTELLIGENT_DRAFT_GENERATED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="RulePrompt",
        entity_id=rule_id,
        details={"version_number": ver.version_number, "quality_status": ver.quality_status},
    )

    return PromptVersionResponse.model_validate(ver)


@router.post("/rule/{rule_id}/validate-quality", response_model=PolicyQualityAssessmentResponse)
async def validate_policy_quality(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-05 / REQ-06: Evaluates policy quality against 8 mandatory gates.
    Returns quality score, gate findings, blocking issues, and approval eligibility.
    """
    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    prompt_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
    prompt_res = await db.execute(prompt_q)
    rule_prompt = prompt_res.scalars().first()
    if not rule_prompt or not rule_prompt.versions:
        raise HTTPException(status_code=404, detail="No prompt versions found for this rule")

    target_ver = None
    if version_id:
        target_ver = next((v for v in rule_prompt.versions if v.id == version_id), None)
    else:
        target_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None) or rule_prompt.versions[0]

    if not target_ver:
        raise HTTPException(status_code=404, detail="Specified prompt version not found")

    # Evaluate contract and quality (check if authoritative snapshot exists)
    snap_q = select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
    snap_res = await db.execute(snap_q)
    snap = snap_res.scalar_one_or_none()
    auth_def = None
    if snap and snap.definition_status == "VERIFIED" and snap.threshold is not None:
        auth_def = {
            "threshold": snap.threshold,
            "threshold_unit": snap.threshold_unit,
            "aggregation_window": snap.aggregation_window,
        }

    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule, authoritative_siem_definition=auth_def)
    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, target_ver)

    assessment = PolicyQualityValidator.validate_policy_quality(
        rule=rule,
        prompt_version=target_ver,
        contract=contract,
        semantics=semantics,
    )

    # Update version status
    target_ver.quality_score = assessment.quality_score
    target_ver.quality_assessment_id = assessment.assessment_id
    if not target_ver.status == "APPROVED":
        target_ver.quality_status = "APPROVAL_ELIGIBLE" if assessment.approval_eligible else "REWORK_REQUIRED"
    await db.commit()

    return assessment


@router.post("/rule/{rule_id}/evaluate-simulation")
async def evaluate_policy_simulation(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    REQ-07: Executes historical regression simulation on candidate policy.
    Reports INSUFFICIENT_DATA if historical cases < 5.
    """
    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    prompt_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
    prompt_res = await db.execute(prompt_q)
    rule_prompt = prompt_res.scalars().first()
    if not rule_prompt or not rule_prompt.versions:
        raise HTTPException(status_code=404, detail="No prompt versions found for this rule")

    target_ver = None
    if version_id:
        target_ver = next((v for v in rule_prompt.versions if v.id == version_id), None)
    else:
        target_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None) or rule_prompt.versions[0]

    baseline_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None)

    sim_svc = PolicySimulationService(db)
    return await sim_svc.evaluate_candidate_policy(
        rule_id=rule.id,
        candidate_version=target_ver,
        baseline_version=baseline_ver,
    )


@router.get("/rule/{rule_id}/drift")
async def get_rule_drift_events(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-10: Returns policy drift notifications and revalidation triggers for a rule.
    """
    q = select(PolicyDriftEvent).where(PolicyDriftEvent.rule_id == rule_id).order_by(desc(PolicyDriftEvent.created_at))
    res = await db.execute(q)
    events = res.scalars().all()
    return [
        {
            "id": e.id,
            "trigger_type": e.trigger_type,
            "summary": e.summary,
            "changed_fields": e.changed_fields,
            "revalidation_required": e.revalidation_required,
            "acknowledged": e.acknowledged,
            "created_at": e.created_at,
        }
        for e in events
    ]


@router.post("/rule/{rule_id}/acknowledge-drift")
async def acknowledge_drift_events(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    REQ-10: Acknowledges drift events for a rule after administrative review.
    """
    q = select(PolicyDriftEvent).where(PolicyDriftEvent.rule_id == rule_id, PolicyDriftEvent.acknowledged == False)
    res = await db.execute(q)
    events = res.scalars().all()
    for e in events:
        e.acknowledged = True
        e.acknowledged_by_user_id = current_user.id
    await db.commit()
    return {"acknowledged_count": len(events)}


@router.get("/rule/{rule_id}/export")
async def export_single_rule_prompt(
    rule_id: str,
    format: str = Query("json", pattern="^(json|markdown|md)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Exports a single rule's prompt configuration with active version and version history.
    """
    service = PromptStudioService(db)
    try:
        content, media_type, filename = await service.export_single_rule_prompt(rule_id=rule_id, format=format)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rule/{rule_id}/generate-draft", response_model=PromptVersionResponse)
async def generate_template_draft(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = PromptStudioService(db)
    try:
        ver = await service.generate_template_draft(rule_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="PROMPT_TEMPLATE_DRAFT_GENERATED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="RulePrompt",
        entity_id=rule_id,
        details={"version_number": ver.version_number, "is_template_draft": True},
    )

    return PromptVersionResponse.model_validate(ver)


@router.post("/rule/{rule_id}/draft", response_model=PromptVersionResponse)
async def create_manual_draft(
    rule_id: str,
    req: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = PromptStudioService(db)
    try:
        ver = await service.create_draft_version(rule_id, req, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="PROMPT_MANUAL_DRAFT_CREATED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="RulePrompt",
        entity_id=rule_id,
        details={"version_number": ver.version_number},
    )

    return PromptVersionResponse.model_validate(ver)


@router.post("/rule/{rule_id}/approve/{version_id}", response_model=PromptVersionResponse)
async def approve_prompt_version(
    rule_id: str,
    version_id: str,
    req: Optional[PromptApprovalRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # Approval gating requires Lead / Administrator
):
    service = PromptStudioService(db)
    change_summary = req.change_summary if req else "Approved by Administrator"
    try:
        ver = await service.approve_version(rule_id, version_id, current_user.id, change_summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="PROMPT_VERSION_APPROVED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="RulePrompt",
        entity_id=rule_id,
        details={"version_number": ver.version_number, "status": "APPROVED", "quality_score": ver.quality_score},
    )

    return PromptVersionResponse.model_validate(ver)


@router.post("/rule/{rule_id}/rollback/{version_id}", response_model=PromptVersionResponse)
async def rollback_prompt_version(
    rule_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = PromptStudioService(db)
    try:
        ver = await service.rollback_version(rule_id, version_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit = AuditService(db)
    await audit.log(
        action="PROMPT_VERSION_ROLLEDBACK",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="RulePrompt",
        entity_id=rule_id,
        details={"new_active_version_number": ver.version_number},
    )

    return PromptVersionResponse.model_validate(ver)
