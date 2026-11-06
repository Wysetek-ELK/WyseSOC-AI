import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.dry_run import DryRunJob, DryRunResult
from app.models.incident import Incident
from app.services.evaluation_service import EvaluationService
from app.services.maturity_service import RuleMaturityService
from app.services.audit_service import AuditService
from app.schemas.evaluation import (
    EvaluationMetricsResponse,
    PromptComparisonItem,
    RuleMaturityResponse,
    MaturityApprovalRequest,
)

router = APIRouter(prefix="/evaluations", tags=["Evaluation Framework"])


@router.get("/job/{job_id}/metrics", response_model=EvaluationMetricsResponse)
async def get_job_metrics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = EvaluationService(db)
    try:
        metrics = await service.calculate_job_metrics(job_id)
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/prompt-comparison/{rule_id}", response_model=List[PromptComparisonItem])
async def compare_prompts_for_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = EvaluationService(db)
    try:
        comparisons = await service.compare_prompt_versions(rule_id)
        return comparisons
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/rule-maturity", response_model=List[RuleMaturityResponse])
async def list_rule_maturity_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    maturity_service = RuleMaturityService(db)
    records = await maturity_service.list_all_evaluations()
    return records


@router.post("/rule-maturity/{rule_id}/approve", response_model=RuleMaturityResponse)
async def approve_rule_for_automation(
    rule_id: str,
    req: MaturityApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    maturity_service = RuleMaturityService(db)
    try:
        updated = await maturity_service.approve_rule_for_automation(
            rule_id=rule_id,
            user_id=current_user.id,
            approval_notes=req.approval_notes,
        )

        audit = AuditService(db)
        await audit.log(
            user_id=current_user.id,
            action="RULE_AUTOMATION_APPROVED",
            entity_type="RuleMaturityEvaluation",
            entity_id=updated.id,
            details={
                "rule_id": rule_id,
                "notes": req.approval_notes,
                "admin": current_user.username,
            },
        )

        # Re-fetch full response
        evals = await maturity_service.list_all_evaluations()
        matched = next((e for e in evals if e.rule_id == rule_id), None)
        if matched:
            return matched

        return RuleMaturityResponse(
            id=updated.id,
            rule_id=updated.rule_id,
            rule_name=updated.rule.name if updated.rule else None,
            event_type=updated.rule.event_type if updated.rule else None,
            maturity_status=updated.maturity_status,
            precision_score=round(updated.precision_score * 100.0, 1),
            recall_score=round(updated.recall_score * 100.0, 1),
            f1_score=round(updated.f1_score * 100.0, 1),
            coverage_score=round(updated.coverage_score * 100.0, 1),
            sample_size=updated.sample_size,
            unresolved_evidence_gaps=updated.unresolved_evidence_gaps or [],
            recommendation_explanation=updated.recommendation_explanation,
            is_admin_approved=updated.is_admin_approved,
            approved_by_username=current_user.username,
            approved_at=updated.approved_at,
            approval_notes=updated.approval_notes,
            latest_test_date=updated.latest_test_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/job/{job_id}/export/csv")
async def export_job_csv(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = EvaluationService(db)
    try:
        csv_content = await service.export_job_results_csv(job_id)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="evaluation_job_{job_id[:8]}.csv"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/job/{job_id}/export/json")
async def export_job_json(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = EvaluationService(db)
    try:
        metrics = await service.calculate_job_metrics(job_id)
        # Fetch raw results
        query = (
            select(DryRunResult)
            .where(DryRunResult.job_id == job_id)
            .options(
                selectinload(DryRunResult.incident).selectinload(Incident.ground_truth),
                selectinload(DryRunResult.incident).selectinload(Incident.rule),
            )
        )
        res = await db.execute(query)
        results = res.scalars().all()

        export_data = {
            "job_id": job_id,
            "exported_at": metrics.generated_at.isoformat(),
            "metrics": metrics.dict(),
            "results": [
                {
                    "result_id": r.id,
                    "incident_id": r.incident.incident_id if r.incident else r.incident_id,
                    "rule_id": r.incident.rule_id if r.incident else None,
                    "rule_name": r.incident.rule.name if (r.incident and r.incident.rule) else None,
                    "predicted_verdict": r.predicted_verdict,
                    "ground_truth_verdict": r.incident.ground_truth.resolution if (r.incident and r.incident.ground_truth) else None,
                    "confidence": r.confidence,
                    "latency_ms": r.latency_ms,
                    "model_identifier": r.model_identifier,
                    "validation_status": r.validation_status,
                    "is_simulated": r.is_simulated,
                    "reasoning": r.reasoning,
                    "supporting_evidence": r.supporting_evidence,
                    "missing_evidence": r.missing_evidence,
                    "analyst_questions": r.analyst_questions,
                }
                for r in results
            ],
        }

        return Response(
            content=json.dumps(export_data, default=str, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="evaluation_job_{job_id[:8]}.json"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
