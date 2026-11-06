from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.dry_run import DryRunConfig, DryRunJob, DryRunResult
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.services.dry_run_service import DryRunService
from app.services.maturity_service import RuleMaturityService
from app.services.audit_service import AuditService
from app.schemas.dry_run import (
    DryRunConfigCreate,
    DryRunConfigResponse,
    DryRunJobResponse,
    DryRunResultResponse,
    DryRunTriggerRequest,
)

router = APIRouter(prefix="/dry-run", tags=["Dry-Run Testing"])


@router.post("/configs", response_model=DryRunConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_dry_run_config(
    data: DryRunConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = DryRunService(db)
    config = await service.create_config(data, user_id=current_user.id)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="DRY_RUN_CONFIG_CREATED",
        entity_type="DryRunConfig",
        entity_id=config.id,
        details={"name": config.name, "provider_type": config.provider_type, "split_strategy": config.split_strategy},
    )

    rule_name = None
    if config.rule_id:
        r_res = await db.execute(select(Rule).where(Rule.id == config.rule_id))
        r = r_res.scalars().first()
        if r:
            rule_name = r.name

    return DryRunConfigResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        rule_id=config.rule_id,
        rule_name=rule_name,
        prompt_version_id=config.prompt_version_id,
        provider_type=config.provider_type,
        split_strategy=config.split_strategy,
        dataset_filters=config.dataset_filters or {},
        created_by_user_id=config.created_by_user_id,
        created_at=config.created_at,
    )


@router.get("/configs", response_model=List[DryRunConfigResponse])
async def list_dry_run_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DryRunService(db)
    configs = await service.list_configs()
    responses = []
    for c in configs:
        responses.append(
            DryRunConfigResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                rule_id=c.rule_id,
                rule_name=c.rule.name if c.rule else None,
                prompt_version_id=c.prompt_version_id,
                provider_type=c.provider_type,
                split_strategy=c.split_strategy,
                dataset_filters=c.dataset_filters or {},
                created_by_user_id=c.created_by_user_id,
                created_at=c.created_at,
            )
        )
    return responses


@router.get("/configs/{config_id}", response_model=DryRunConfigResponse)
async def get_dry_run_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DryRunService(db)
    config = await service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Dry run configuration not found")

    return DryRunConfigResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        rule_id=config.rule_id,
        rule_name=config.rule.name if config.rule else None,
        prompt_version_id=config.prompt_version_id,
        provider_type=config.provider_type,
        split_strategy=config.split_strategy,
        dataset_filters=config.dataset_filters or {},
        created_by_user_id=config.created_by_user_id,
        created_at=config.created_at,
    )


@router.post("/trigger", response_model=DryRunJobResponse, status_code=status.HTTP_201_CREATED)
async def trigger_dry_run_job(
    req: DryRunTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    service = DryRunService(db)
    try:
        job = await service.execute_dry_run_job(
            config_id=req.config_id,
            custom_sample_limit=req.custom_sample_limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger rule maturity recalculation for affected rules
    maturity_service = RuleMaturityService(db)
    config = await service.get_config(req.config_id)
    if config and config.rule_id:
        await maturity_service.update_rule_maturity_from_results(config.rule_id)
    else:
        # Re-evaluate all rules
        rules_res = await db.execute(select(Rule))
        all_rules = rules_res.scalars().all()
        for r in all_rules:
            await maturity_service.update_rule_maturity_from_results(r.id)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="DRY_RUN_JOB_TRIGGERED",
        entity_type="DryRunJob",
        entity_id=job.id,
        details={
            "config_id": job.config_id,
            "total_items": job.total_items,
            "is_simulated": job.is_simulated,
            "error_count": job.error_count,
        },
    )

    return DryRunJobResponse(
        id=job.id,
        config_id=job.config_id,
        config_name=config.name if config else None,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        error_count=job.error_count,
        is_simulated=job.is_simulated,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs", response_model=List[DryRunJobResponse])
async def list_dry_run_jobs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DryRunService(db)
    jobs = await service.list_jobs(limit=limit)
    return [
        DryRunJobResponse(
            id=j.id,
            config_id=j.config_id,
            config_name=j.config.name if j.config else None,
            status=j.status,
            total_items=j.total_items,
            processed_items=j.processed_items,
            error_count=j.error_count,
            is_simulated=j.is_simulated,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=DryRunJobResponse)
async def get_dry_run_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DryRunService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Dry run job not found")

    return DryRunJobResponse(
        id=job.id,
        config_id=job.config_id,
        config_name=job.config.name if job.config else None,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        error_count=job.error_count,
        is_simulated=job.is_simulated,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/results", response_model=List[DryRunResultResponse])
async def get_dry_run_job_results(
    job_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = (
        select(DryRunResult)
        .where(DryRunResult.job_id == job_id)
        .options(
            selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
            selectinload(DryRunResult.incident).selectinload(Incident.rule),
        )
        .order_by(DryRunResult.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(query)
    results = res.scalars().all()

    formatted: List[DryRunResultResponse] = []
    for r in results:
        inc = r.incident
        gt = inc.ground_truth.resolution if (inc and inc.ground_truth) else None

        # Check agreement
        is_agreement = None
        if gt:
            gt_norm = None
            if "true positive" in gt.lower() or "malicious" in gt.lower():
                gt_norm = "TRUE_POSITIVE"
            elif "false positive" in gt.lower() or "benign" in gt.lower():
                gt_norm = "FALSE_POSITIVE"

            if gt_norm:
                if r.predicted_verdict == gt_norm:
                    is_agreement = True
                elif r.predicted_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                    is_agreement = False
                else:
                    is_agreement = False  # Abstention

        formatted.append(
            DryRunResultResponse(
                id=r.id,
                job_id=r.job_id,
                incident_id=r.incident_id,
                incident_vendor_id=inc.incident_id if inc else None,
                incident_title=inc.title if inc else None,
                rule_id=inc.rule_id if inc else None,
                rule_name=inc.rule.name if (inc and inc.rule) else (inc.event_type if inc else None),
                predicted_verdict=r.predicted_verdict,
                confidence=float(r.confidence),
                reasoning=r.reasoning,
                supporting_evidence=r.supporting_evidence or [],
                missing_evidence=r.missing_evidence or [],
                analyst_questions=r.analyst_questions or [],
                latency_ms=r.latency_ms,
                model_identifier=r.model_identifier,
                prompt_version_number=r.prompt_version_number,
                validation_status=r.validation_status,
                is_simulated=r.is_simulated,
                ground_truth_verdict=gt,
                is_agreement=is_agreement,
                created_at=r.created_at,
            )
        )

    return formatted
