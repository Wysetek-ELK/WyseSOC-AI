import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, BackgroundTasks
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.datetime_utils import utc_now
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.policy_drift import PolicyDriftEvent
from app.models.bulk_audit import BulkQualityAuditJobRecord
from app.models.verdict_intelligence import (
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.models.incident import Incident
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.services.actual_prompt_capture_service import ActualPromptCaptureService
from app.services.policy_compiler_service import PolicyCompilerService
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.prompt_inspector import (
    ActualPromptResponse,
    PromptExecutionSummary,
    PromptTechnicalDetails,
    PromptL1Explanation,
)
from app.services.policy_governance import (
    SIMULATED_PROVIDER_TOKENS,
    assess_policy_runtime_certification,
    get_rule_semantics_and_contract,
    resolve_canonical_rule,
)
from app.services.prompt_studio_service import PromptStudioService
from app.services.audit_service import AuditService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.bulk_quality_audit_service import BulkQualityAuditService
from app.services.policy_lifecycle_monitor import PolicyLifecycleMonitor
from app.services.production_readiness_service import ProductionReadinessService
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
    GateStatus,
    PolicyQualityAssessmentResponse,
    QualitySummaryItem,
    SimulationStatus,
)
from app.schemas.production_readiness import ProductionReadinessResponse

logger = logging.getLogger("ai_verdict.prompts")

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

    # Pre-fetch latest simulation run and quality assessment per rule
    sim_runs_res = await db.execute(
        select(HistoricalEvaluationRunRecord).order_by(desc(HistoricalEvaluationRunRecord.started_at))
    )
    sim_by_rule: Dict[str, HistoricalEvaluationRunRecord] = {}
    for srun in sim_runs_res.scalars().all():
        if srun.rule_id and srun.rule_id not in sim_by_rule:
            sim_by_rule[srun.rule_id] = srun

    qa_res = await db.execute(
        select(PolicyQualityAssessmentRecord).order_by(desc(PolicyQualityAssessmentRecord.evaluated_at))
    )
    qa_by_rule: Dict[str, PolicyQualityAssessmentRecord] = {}
    for qa in qa_res.scalars().all():
        if qa.rule_id and qa.rule_id not in qa_by_rule:
            qa_by_rule[qa.rule_id] = qa

    items = []
    for r in rules:
        rp = prompts_by_rule_id.get(r.id)
        versions = rp.versions if (rp and rp.versions) else []
        active_v = next((v for v in versions if v.id == rp.active_version_id), None) if rp else None
        target_v = active_v or (versions[0] if versions else None)
        has_approved = any(v.status == "APPROVED" for v in versions)

        snap = snaps_by_rule_id.get(r.id) or snaps_by_rule_id.get(r.rule_id)
        if snap:
            archetype = snap.primary_archetype
            completeness = snap.definition_status
        else:
            sem = RuleIntelligenceAnalyzer.analyze_rule(r)
            cls_res = DetectionArchetypeRegistry.classify_rule(sem, r)
            archetype = cls_res.primary_archetype
            completeness = sem.definition_status.value if hasattr(sem.definition_status, "value") else str(sem.definition_status)

        q_score = target_v.quality_score if target_v else None
        q_status = target_v.quality_status if target_v else "NOT_EVALUATED"

        latest_qa = qa_by_rule.get(r.id)
        latest_sim = sim_by_rule.get(r.id) or sim_by_rule.get(r.rule_id)
        real_sim_status = (
            latest_qa.simulation_status
            if latest_qa and latest_qa.simulation_status
            else (latest_sim.validation_state if latest_sim else "NOT_EVALUATED")
        )
        blocker_cnt = len(latest_qa.blocking_issues) if latest_qa and isinstance(latest_qa.blocking_issues, list) else (
            1 if (completeness == "INCOMPLETE" and not has_approved) else 0
        )

        revalidation_req = bool((r.id in drift_rule_ids) or (bool(target_v) and getattr(target_v, "quality_status", None) == "REVIEW_REQUIRED"))

        is_def_incomplete = (completeness in ("INCOMPLETE", "UNKNOWN")) or (
            latest_qa and any("G1" in str(b) or "DEFINITION" in str(b) for b in (latest_qa.blocking_issues or []))
        )
        if is_def_incomplete:
            readiness_status = "INCOMPLETE"
            action_title = "Verify FortiSIEM Detection Semantics"
        elif blocker_cnt > 0 or revalidation_req:
            readiness_status = "BLOCKED"
            action_title = "Resolve Quality Gate Blockers"
        elif has_approved and r.status == "ACTIVE":
            readiness_status = "ACTIVE"
            action_title = "Monitor Production Performance"
        elif has_approved:
            readiness_status = "APPROVED"
            action_title = "Activate Production Automation"
        elif q_status == "APPROVAL_ELIGIBLE" or (latest_qa and latest_qa.approval_eligible):
            readiness_status = "READY_FOR_APPROVAL"
            action_title = "Request Production Approval"
        else:
            readiness_status = "LEARNING"
            action_title = "Review Pending Incidents"

        gates_passed_count = 0
        if latest_qa and latest_qa.gate_results:
            gates_passed_count = sum(
                1 for g in latest_qa.gate_results.values()
                if (g.get("status") if isinstance(g, dict) else getattr(g, "status", "")) == "PASSED"
            )
        elif has_approved:
            gates_passed_count = 8
        elif not is_def_incomplete and q_score and q_score > 50:
            gates_passed_count = 2

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
                blocking_issue_count=blocker_cnt,
                simulation_status=real_sim_status,
                last_validated_date=(latest_qa.evaluated_at if latest_qa else (snap.updated_at if snap else None)),
                revalidation_required=revalidation_req,
                production_readiness_status=readiness_status,
                gates_passed_count=gates_passed_count,
                missing_requirements_count=blocker_cnt,
                recommended_action_title=action_title,
            )
        )

    return items


@router.get("/rule/{rule_id}/readiness", response_model=ProductionReadinessResponse)
async def get_rule_production_readiness(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ: Production Readiness Evaluation Endpoint.
    Returns authoritative, evidence-based production readiness evaluation for a detection rule.
    Separates Production Readiness from SIEM baseline deployment status.
    Maps technical quality criteria into 6 human-readable stages and one Smart Next Action.
    """
    try:
        return await ProductionReadinessService.evaluate_readiness(
            db=db,
            rule_identifier=rule_id,
            version_id=version_id,
            customer=customer or "DEFAULT",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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


async def _analyze_with_snapshot(db: AsyncSession, rule: Rule):
    semantics, contract, _ = await get_rule_semantics_and_contract(
        db, rule, for_quality_validation=True
    )
    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
    return semantics, classification, archetype_def, contract


@router.get("/rule/{rule_id}/intelligence")
async def get_rule_intelligence(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    REQ-01 / REQ-02: Returns structured detection semantics and archetype classification for a rule,
    honoring any persisted RuleIntelligenceSnapshot consistently with G1 and verdict execution.
    """
    rule = await resolve_canonical_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    semantics, classification, archetype_def, contract = await _analyze_with_snapshot(db, rule)

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
    rule = await resolve_canonical_rule(db, rule_id)
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


async def _compute_policy_quality_readonly(
    db: AsyncSession,
    rule_id: str,
    version_id: Optional[str] = None,
):
    """Evaluates policy G1-G8 quality without mutating database state."""
    rule = await resolve_canonical_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    prompt_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
    prompt_res = await db.execute(prompt_q)
    rule_prompt = prompt_res.scalars().first()
    if not rule_prompt or not rule_prompt.versions:
        raise HTTPException(status_code=404, detail="No prompt versions found for this rule")

    target_ver = None
    if version_id:
        target_ver = next((v for v in rule_prompt.versions if str(v.id) == str(version_id)), None)
    if not target_ver:
        target_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None) or (rule_prompt.versions[0] if rule_prompt.versions else None)

    if not target_ver:
        raise HTTPException(status_code=404, detail="Specified prompt version not found")

    semantics, contract, _ = await get_rule_semantics_and_contract(
        db, rule, prompt_version=target_ver, for_quality_validation=True
    )

    latest_run_q = (
        select(HistoricalEvaluationRunRecord)
        .where(
            HistoricalEvaluationRunRecord.rule_id.in_([rule.id, rule.rule_id]),
            HistoricalEvaluationRunRecord.policy_version_id == str(target_ver.id),
            HistoricalEvaluationRunRecord.status.in_(["COMPLETED", "FAILED"]),
        )
        .order_by(desc(HistoricalEvaluationRunRecord.completed_at), desc(HistoricalEvaluationRunRecord.started_at))
    )
    latest_run_res = await db.execute(latest_run_q)
    latest_run = latest_run_res.scalars().first()

    sim_results = None
    if latest_run:
        metrics_dict = getattr(latest_run, "metrics", {}) or getattr(latest_run, "metrics_payload", {}) or {}
        reg_summary = getattr(latest_run, "regression_summary", {}) or {}
        cfg_snapshot = getattr(latest_run, "config_snapshot", {}) or {}
        eligible_gt = metrics_dict.get("verified_ground_truth_cases")
        if eligible_gt is None:
            eligible_gt = getattr(latest_run, "verified_ground_truth_cases", 0)
        ba_val = metrics_dict.get("balanced_accuracy")
        if ba_val is None:
            ba_val = getattr(latest_run, "balanced_accuracy", None)
        ece_val = metrics_dict.get("ece")
        if ece_val is None:
            ece_val = getattr(latest_run, "ece", None)
        brier_val = metrics_dict.get("brier_score")
        if brier_val is None:
            brier_val = getattr(latest_run, "brier_score", None)

        provider_type = str(cfg_snapshot.get("provider_type") or "").upper().strip()
        exec_prov = str(cfg_snapshot.get("execution_provenance") or "").upper().strip()
        res_sim_q = await db.execute(
            select(HistoricalEvaluationResultRecord.claims_summary)
            .where(HistoricalEvaluationResultRecord.run_id == latest_run.id)
            .limit(20)
        )
        res_sim_summaries = res_sim_q.scalars().all()
        any_result_simulated = any(
            bool((cs or {}).get("is_simulated")) for cs in res_sim_summaries if isinstance(cs, dict)
        )
        is_simulated_run = bool(
            cfg_snapshot.get("is_simulated") is True
            or provider_type in SIMULATED_PROVIDER_TOKENS
            or exec_prov in SIMULATED_PROVIDER_TOKENS
            or any_result_simulated
            or (
                not provider_type
                and str(latest_run.validation_state or "").upper() != "EVALUATED_PASSED"
            )
        )

        sim_results = {
            "simulation_run_id": latest_run.id,
            "sample_count": getattr(latest_run, "total_cases", 0) or getattr(latest_run, "sample_size", 0),
            "eligible_ground_truth_count": eligible_gt,
            "verified_ground_truth_cases": eligible_gt,
            "simulation_status": latest_run.validation_state,
            "regression_status": reg_summary.get("regression_status") or ("NOT_ASSESSED" if not latest_run.baseline_run_id else latest_run.validation_state),
            "critical_regressions": 1 if latest_run.status == "FAILED" or metrics_dict.get("critical_false_negatives", 0) > 0 or latest_run.validation_state == "REGRESSION_DETECTED" else 0,
            "balanced_accuracy": ba_val,
            "overall_accuracy": metrics_dict.get("overall_accuracy"),
            "decision_coverage": metrics_dict.get("automatic_decision_coverage") if metrics_dict.get("automatic_decision_coverage") is not None else metrics_dict.get("decision_coverage"),
            "ece": ece_val,
            "brier_score": brier_val,
            "policy_digest": cfg_snapshot.get("policy_digest"),
            "provider_type": provider_type or ("SIMULATED" if is_simulated_run else "OPENAI_COMPATIBLE"),
            "model_identifier": cfg_snapshot.get("model_identifier"),
            "execution_provenance": exec_prov or ("SIMULATED" if is_simulated_run else "REAL_LOCAL_LLM"),
            "is_simulated": is_simulated_run,
            "metrics": metrics_dict,
        }

    assessment = PolicyQualityValidator.validate_policy_quality(
        rule=rule,
        prompt_version=target_ver,
        contract=contract,
        semantics=semantics,
        simulation_results=sim_results,
    )
    g8_gate = assessment.gate_results.get("G8_SIMULATION_REGRESSION")
    structural_eligible = bool(assessment.approval_eligible)
    empirical_eligible = bool(
        assessment.simulation_status == SimulationStatus.EVALUATED_PASSED
        and g8_gate is not None
        and g8_gate.status == GateStatus.PASSED
        and not (sim_results and sim_results.get("is_simulated"))
    )
    assessment.structural_approval_eligible = structural_eligible
    assessment.empirical_validation_eligible = empirical_eligible
    assessment.autonomous_operation_eligible = (
        structural_eligible and empirical_eligible and str(target_ver.status).upper() == "APPROVED"
    )
    if str(target_ver.status).upper() != "APPROVED":
        assessment.autonomous_operation_eligible = structural_eligible and empirical_eligible

    # Surface historical persisted assessment metadata read-only without rescoring old records
    persisted_q = (
        select(PolicyQualityAssessmentRecord)
        .where(
            PolicyQualityAssessmentRecord.rule_id == rule.id,
            PolicyQualityAssessmentRecord.prompt_version_id == str(target_ver.id),
        )
        .order_by(desc(PolicyQualityAssessmentRecord.evaluated_at))
        .limit(1)
    )
    persisted_rec = (await db.execute(persisted_q)).scalars().first()
    if persisted_rec is not None:
        assessment.historical_assessment_preserved = True
        assessment.persisted_validator_version = persisted_rec.validator_version
        assessment.persisted_quality_score = persisted_rec.quality_score
    return rule, target_ver, assessment


@router.get("/rule/{rule_id}/assessments")
async def list_stored_policy_assessments(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns persisted historical PolicyQualityAssessmentRecord rows verbatim without
    silently rescoring legacy scoring models (e.g., v2.0.0 -> v2.2.0).
    """
    rule = await resolve_canonical_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    q = (
        select(PolicyQualityAssessmentRecord)
        .where(PolicyQualityAssessmentRecord.rule_id == rule.id)
        .order_by(desc(PolicyQualityAssessmentRecord.evaluated_at))
    )
    if version_id:
        q = q.where(PolicyQualityAssessmentRecord.prompt_version_id == str(version_id))
    rows = (await db.execute(q)).scalars().all()
    return {
        "rule_id": rule.id,
        "rule_identifier": rule.rule_id,
        "current_validator_version": PolicyQualityValidator.VALIDATOR_VERSION,
        "assessments": [
            {
                "assessment_id": r.id,
                "rule_id": r.rule_id,
                "prompt_version_id": r.prompt_version_id,
                "version_number": r.version_number,
                "archetype": r.archetype,
                "quality_score": r.quality_score,
                "approval_eligible": r.approval_eligible,
                "simulation_status": r.simulation_status,
                "score_breakdown": r.score_breakdown,
                "gate_results": r.gate_results,
                "blocking_issues": r.blocking_issues,
                "warnings": r.warnings,
                "missing_evidence_mappings": r.missing_evidence_mappings,
                "recommendations": r.recommendations,
                "policy_digest": r.policy_digest,
                "contract_digest": r.contract_digest,
                "rule_digest": r.rule_digest,
                "validator_version": r.validator_version,
                "is_legacy_scoring_model": r.validator_version != PolicyQualityValidator.VALIDATOR_VERSION,
                "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
            }
            for r in rows
        ],
    }


@router.get("/rule/{rule_id}/quality-preview", response_model=PolicyQualityAssessmentResponse)
async def preview_policy_quality(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read-only G1-G8 quality assessment preview (permits Viewers without DB mutation)."""
    _, _, assessment = await _compute_policy_quality_readonly(db, rule_id, version_id)
    return assessment


@router.post("/rule/{rule_id}/validate-quality", response_model=PolicyQualityAssessmentResponse)
async def validate_policy_quality(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    REQ-05 / REQ-06: Evaluates policy quality against 8 mandatory gates and persists
    validated quality score/status to the prompt version (Analyst/Admin only).
    """
    rule, target_ver, assessment = await _compute_policy_quality_readonly(db, rule_id, version_id)

    # Persist quality metadata only for authorized mutating POST
    target_ver.quality_score = assessment.quality_score
    target_ver.quality_assessment_id = assessment.assessment_id
    if target_ver.status != "APPROVED":
        target_ver.quality_status = "APPROVAL_ELIGIBLE" if assessment.approval_eligible else "REWORK_REQUIRED"

    audit = AuditService(db)
    await audit.log(
        action="POLICY_QUALITY_VALIDATED",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="PromptVersion",
        entity_id=str(target_ver.id),
        details={
            "rule_id": rule.id,
            "quality_score": assessment.quality_score,
            "structural_approval_eligible": assessment.structural_approval_eligible,
            "empirical_validation_eligible": assessment.empirical_validation_eligible,
            "quality_status": target_ver.quality_status,
        },
    )
    await db.commit()

    return assessment


@router.post("/rule/{rule_id}/evaluate-simulation")
async def evaluate_policy_simulation(
    rule_id: str,
    version_id: Optional[str] = Query(None),
    provider_type: str = Query("SIMULATED"),
    sample_limit: Optional[int] = Query(500),
    include_unlabeled_replay: bool = Query(False),
    async_execution: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    REQ-07: Executes historical regression simulation on candidate policy.
    Supports explicit provider_type (`OPENAI_COMPATIBLE` or `SIMULATED`), paginated
    retrieval via sample_limit, optional isolated unlabeled replay, and Celery queueing.
    """
    from app.workers.tasks import dispatch_policy_simulation

    rule = await resolve_canonical_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"SIEM Rule {rule_id} not found")

    prompt_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
    prompt_res = await db.execute(prompt_q)
    rule_prompt = prompt_res.scalars().first()
    if not rule_prompt or not rule_prompt.versions:
        raise HTTPException(status_code=404, detail="No prompt versions found for this rule")

    target_ver = None
    if version_id:
        target_ver = next((v for v in rule_prompt.versions if str(v.id) == str(version_id)), None)
    if not target_ver:
        target_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None) or (rule_prompt.versions[0] if rule_prompt.versions else None)

    if not target_ver:
        raise HTTPException(status_code=404, detail="Specified prompt version not found")

    baseline_ver = next((v for v in rule_prompt.versions if v.id == rule_prompt.active_version_id), None)

    try:
        return await dispatch_policy_simulation(
            db=db,
            rule_id=rule.id,
            candidate_version=target_ver,
            baseline_version=baseline_ver,
            provider_type=provider_type,
            sample_limit=sample_limit,
            include_unlabeled_replay=include_unlabeled_replay,
            async_execution=async_execution,
        )
    except Exception as exc:
        logger.error(f"Error evaluating policy simulation for rule {rule_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation evaluation failed: {str(exc)}")


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


async def _trigger_bounded_rule_reevaluation(rule_id: str) -> None:
    """Safely triggers bounded reevaluation of deferred POLICY_NOT_APPROVED incidents upon policy approval."""
    from app.config import settings
    if getattr(settings, "APP_ENV", "development").lower() == "testing":
        return
    try:
        from app.database import AsyncSessionLocal
        from app.services.ai_verdict_service import VerdictTriageAgent
        async with AsyncSessionLocal() as bg_db:
            agent = VerdictTriageAgent(bg_db)
            await agent.reconcile_pending_triage(
                max_batch=15,
                username="policy_approval_reeval",
                include_reevaluation_eligible=True,
                rule_id=rule_id,
            )
    except Exception as exc:
        logger.warning(f"Bounded reevaluation trigger warning for rule {rule_id}: {exc}")


@router.post("/rule/{rule_id}/approve/{version_id}", response_model=PromptVersionResponse)
async def approve_prompt_version(
    rule_id: str,
    version_id: str,
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(_trigger_bounded_rule_reevaluation, rule_id)
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


# =========================================================================
# AIS 2.0: ACTUAL LLM PROMPT INSPECTOR ENDPOINTS
# =========================================================================

@router.get("/actual-prompt/incident/{incident_id}", response_model=ActualPromptResponse)
async def get_actual_prompt_for_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Returns the exact outbound prompt and request payload captured at the provider boundary
    immediately prior to Server 2 dispatch for an incident verdict.
    """
    import json
    # 1. Fetch incident
    inc_stmt = select(Incident).where(Incident.incident_id == incident_id)
    inc_res = await db.execute(inc_stmt)
    incident = inc_res.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    # 2. Query captured records
    stmt = (
        select(ActualLLMPromptCapture)
        .where(ActualLLMPromptCapture.incident_id == incident_id)
        .order_by(desc(ActualLLMPromptCapture.captured_at))
    )
    captures = (await db.execute(stmt)).scalars().all()

    # 3. Handle Historical Capture Unavailable
    if not captures:
        summary = PromptExecutionSummary(
            incident_id=incident.incident_id,
            rule_id=incident.rule_id or "UNKNOWN",
            rule_name=incident.title or "Unknown Detection Alert",
            model_name="N/A (Historical - Not Captured)",
            provider_type="N/A",
            captured_at=incident.created_at,
            policy_version_id=None,
            policy_version_number=None,
            policy_status="HISTORICAL_UNRECORDED",
            policy_source="NONE",
            dispatch_status="HISTORICAL_UNAVAILABLE",
            attempt_number=0,
            execution_id="HISTORICAL",
            latency_ms=0,
        )
        tech_details = PromptTechnicalDetails(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            request_sha256="0" * 64,
            generation_settings={},
            integrity_status="UNVERIFIED",
            integrity_details={"notice": "No provider boundary capture record exists for this historical incident."},
            execution_trace={"status": "HISTORICAL_RECORD_PRE_DATES_CAPTURE_ENGINE"},
        )
        l1_exp = PromptL1Explanation(
            headline="This incident was evaluated before the Actual LLM Prompt Capture engine was active.",
            policy_version_used="Historical / Unknown",
            mandatory_evidence_available=False,
            mandatory_evidence_summary="Historical record — telemetry not recorded at provider boundary",
            historical_precedents_included=0,
            verdict_returned=(incident.ai_verdict or {}).get("verdict", "UNKNOWN"),
            prompt_matches_approved_policy=False,
            prompt_integrity_status="UNVERIFIED",
            summary_text="Historical record. To inspect what instructions would be sent for this rule, open Policy Preview.",
        )
        return ActualPromptResponse(
            capture_id=None,
            capture_status="HISTORICAL_CAPTURE_UNAVAILABLE",
            integrity_status="UNVERIFIED",
            execution_summary=summary,
            system_prompt="[HISTORICAL CAPTURE UNAVAILABLE: This incident verdict was evaluated prior to the deployment of the Actual LLM Prompt Capture engine. Outbound prompt payload was not recorded in runtime storage.]",
            incident_payload=json.dumps(incident.raw_payload or {}, indent=2),
            rag_precedents=[],
            has_rag_precedents=False,
            evidence_requirements={},
            verdict_schema=PolicyCompilerService.MODEL_RESPONSE_SCHEMA,
            technical_details=tech_details,
            l1_explanation=l1_exp,
            raw_model_response=(incident.ai_verdict or {}).get("reason"),
            raw_request_payload=None,
            is_redacted=False,
        )

    # 4. Use latest captured attempt
    cap = captures[0]

    # Verify rule and active policy version provenance
    rule = await db.get(Rule, cap.rule_id) if cap.rule_id else None
    active_v = None
    if rule:
        rp_res = await db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rp = rp_res.scalars().first()
        if rp and rp.active_version_id:
            active_v = next((v for v in rp.versions if v.id == rp.active_version_id), None)

    integrity_status, integrity_details = ActualPromptCaptureService.verify_integrity(cap, rule, active_v)

    # Log audit entry
    audit = AuditService(db)
    await audit.log(
        action="VIEW_ACTUAL_LLM_PROMPT",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="IncidentPromptCapture",
        entity_id=cap.id,
        details={
            "incident_id": cap.incident_id,
            "rule_id": cap.rule_id,
            "dispatch_status": cap.dispatch_status,
            "integrity_status": integrity_status,
            "sha256": cap.request_sha256,
        },
    )

    summary = PromptExecutionSummary(
        incident_id=cap.incident_id,
        rule_id=cap.rule_id,
        rule_name=cap.rule_name,
        model_name=cap.model_name,
        provider_type=cap.provider_type,
        captured_at=cap.captured_at,
        policy_version_id=cap.policy_version_id,
        policy_version_number=cap.policy_version_number,
        policy_status=cap.policy_status,
        policy_source=cap.policy_source,
        dispatch_status=cap.dispatch_status,
        attempt_number=cap.attempt_number,
        execution_id=cap.execution_id,
        latency_ms=cap.latency_ms,
    )

    tech_details = PromptTechnicalDetails(
        prompt_tokens=cap.prompt_tokens,
        completion_tokens=cap.completion_tokens,
        total_tokens=cap.total_tokens,
        request_sha256=cap.request_sha256,
        generation_settings=cap.generation_settings or {},
        integrity_status=integrity_status,
        integrity_details=integrity_details,
        execution_trace={
            "total_attempts": len(captures),
            "current_attempt": cap.attempt_number,
            "dispatch_status": cap.dispatch_status,
            "error_message": cap.error_message,
        },
    )

    l1_raw = cap.l1_explanation or {}
    l1_exp = PromptL1Explanation(
        headline=l1_raw.get("headline") or "This is the investigation instruction and incident evidence that Verdictum AI sent to the Local LLM to generate this verdict.",
        policy_version_used=l1_raw.get("policy_version_used") or f"Version {cap.policy_version_number or 1} ({cap.policy_status})",
        mandatory_evidence_available=bool(l1_raw.get("mandatory_evidence_available", True)),
        mandatory_evidence_summary=l1_raw.get("mandatory_evidence_summary", "Core telemetry requirements verified"),
        historical_precedents_included=len(cap.rag_precedents or []),
        verdict_returned=cap.response_verdict or "REQUIRES_ATTENTION",
        prompt_matches_approved_policy=(cap.policy_status == "APPROVED"),
        prompt_integrity_status=integrity_status,
        summary_text=l1_raw.get("summary_text", f"Grounded under {cap.rule_name} specification."),
    )

    res_dict = {
        "capture_id": cap.id,
        "capture_status": "CAPTURED_RUNTIME",
        "integrity_status": integrity_status,
        "execution_summary": summary.model_dump(),
        "system_prompt": cap.compiled_system_prompt,
        "incident_payload": cap.user_message,
        "rag_precedents": cap.rag_precedents or [],
        "has_rag_precedents": bool(cap.has_rag_precedents),
        "evidence_requirements": cap.evidence_requirements or {},
        "verdict_schema": cap.verdict_schema or {},
        "technical_details": tech_details.model_dump(),
        "l1_explanation": l1_exp.model_dump(),
        "raw_model_response": cap.response_raw,
        "raw_request_payload": cap.raw_request_payload,
        "is_redacted": False,
    }

    redacted_dict = ActualPromptCaptureService.apply_role_redaction(res_dict, current_user)
    return ActualPromptResponse.model_validate(redacted_dict)


@router.get("/actual-prompt/rule/{rule_id}/preview", response_model=ActualPromptResponse)
async def get_prompt_preview_for_rule(
    rule_id: str,
    version_id: Optional[str] = None,
    incident_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Generates a live preview of the compiled prompt specification for a rule.
    Guaranteed and explicitly labeled with capture_status = PREVIEW_ONLY and integrity_status = UNVERIFIED.
    """
    import json
    rule = await resolve_canonical_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    target_v = None
    if version_id:
        target_v = await db.get(PromptVersion, version_id)
    else:
        rp_res = await db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rp = rp_res.scalars().first()
        if rp and rp.active_version_id:
            target_v = next((v for v in rp.versions if v.id == rp.active_version_id), None)
        if not target_v and rp and rp.versions:
            target_v = rp.versions[0]

    compiled = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=target_v,
        execution_mode=CompilationExecutionMode.SIMULATION,
        raise_on_unapproved=False,
    )

    sample_incident_payload = {
        "incident_id": incident_id or "INC-PREVIEW-SAMPLE",
        "title": f"Sample Telemetry for {rule.name}",
        "severity": rule.severity or "MEDIUM",
        "canonical_evidence": [
            {"evidence_id": "EV-01", "source_field": "security.event_type", "observed_value": rule.event_type},
            {"evidence_id": "EV-02", "source_field": "network.source_ip", "observed_value": "192.168.1.100"},
            {"evidence_id": "EV-03", "source_field": "network.destination_port", "observed_value": 445},
        ]
    }
    compact_json = json.dumps({"incident": sample_incident_payload, "rule": {"id": rule.id, "name": rule.name}}, separators=(",", ":"))
    sample_user_msg = f"<UNTRUSTED_INCIDENT_DATA>\n{compact_json}\n</UNTRUSTED_INCIDENT_DATA>"

    raw_req = {
        "model": "preview-compiler",
        "messages": [
            {"role": "system", "content": compiled.compiled_system_prompt},
            {"role": "user", "content": sample_user_msg},
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }
    req_hash = ActualPromptCaptureService.canonical_hash(raw_req)

    summary = PromptExecutionSummary(
        incident_id=incident_id or "INC-PREVIEW-SAMPLE",
        rule_id=rule.id,
        rule_name=rule.name,
        model_name="Preview Compiler",
        provider_type="PREVIEW",
        captured_at=utc_now(),
        policy_version_id=target_v.id if target_v else None,
        policy_version_number=target_v.version_number if target_v else 0,
        policy_status=target_v.status if target_v else "UNCONFIGURED",
        policy_source="PREVIEW_COMPILER",
        dispatch_status="PREVIEW_ONLY",
        attempt_number=1,
        execution_id="PREVIEW",
        latency_ms=0,
    )

    tech_details = PromptTechnicalDetails(
        prompt_tokens=compiled.total_estimated_tokens,
        completion_tokens=0,
        total_tokens=compiled.total_estimated_tokens,
        request_sha256=req_hash,
        generation_settings={"temperature": 0.1, "max_tokens": 1024},
        integrity_status="UNVERIFIED",
        integrity_details={"notice": "Preview compilation only. Not proof of historical runtime dispatch."},
        execution_trace={"mode": "PREVIEW_COMPILER"},
    )

    l1_exp = PromptL1Explanation(
        headline="This is a live Preview Representation of the investigation policy for this rule.",
        policy_version_used=f"Version {target_v.version_number if target_v else 0} ({target_v.status if target_v else 'UNCONFIGURED'})",
        mandatory_evidence_available=True,
        mandatory_evidence_summary="Simulated telemetry payload for preview inspection",
        historical_precedents_included=0,
        verdict_returned="PREVIEW_NOT_EXECUTED",
        prompt_matches_approved_policy=(target_v.status == "APPROVED" if target_v else False),
        prompt_integrity_status="UNVERIFIED",
        summary_text="Preview Only. This is regenerated from current policy specifications and was not dispatched to Server 2.",
    )

    return ActualPromptResponse(
        capture_id=None,
        capture_status="PREVIEW_ONLY",
        integrity_status="UNVERIFIED",
        execution_summary=summary,
        system_prompt=compiled.compiled_system_prompt,
        incident_payload=sample_user_msg,
        rag_precedents=[],
        has_rag_precedents=False,
        evidence_requirements={},
        verdict_schema=PolicyCompilerService.MODEL_RESPONSE_SCHEMA,
        technical_details=tech_details,
        l1_explanation=l1_exp,
        raw_model_response=None,
        raw_request_payload=raw_req,
        is_redacted=False,
    )


@router.get("/actual-prompt/incident/{incident_id}/export")
async def export_actual_prompt_for_incident(
    incident_id: str,
    format: str = Query("json", pattern="^(json|markdown)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Exports the captured outbound prompt for an incident as JSON or Markdown.
    Respects role-based sensitive data redaction.
    """
    import json
    prompt_res = await get_actual_prompt_for_incident(incident_id=incident_id, db=db, current_user=current_user)

    audit = AuditService(db)
    await audit.log(
        action="EXPORT_ACTUAL_LLM_PROMPT",
        user_id=current_user.id,
        username=current_user.username,
        entity_type="IncidentPromptCapture",
        entity_id=incident_id,
        details={"format": format, "capture_status": prompt_res.capture_status},
    )

    if format == "json":
        content = json.dumps(prompt_res.model_dump(), indent=2, default=str)
        filename = f"actual_prompt_{incident_id}.json"
        media_type = "application/json"
    else:
        # Generate Markdown export
        lines = [
            f"# Actual LLM Prompt Export — Incident {prompt_res.execution_summary.incident_id}",
            f"**Rule:** {prompt_res.execution_summary.rule_name} (ID: {prompt_res.execution_summary.rule_id})",
            f"**Execution Timestamp:** {prompt_res.execution_summary.captured_at}",
            f"**Status:** {prompt_res.capture_status} | **Integrity:** {prompt_res.integrity_status}",
            f"**Model:** {prompt_res.execution_summary.model_name} | **Provider:** {prompt_res.execution_summary.provider_type}",
            f"**Policy Version:** {prompt_res.execution_summary.policy_version_number} ({prompt_res.execution_summary.policy_status})",
            f"**Request SHA-256:** `{prompt_res.technical_details.request_sha256}`",
            "",
            "## 1. L1 Investigation Summary",
            f"> {prompt_res.l1_explanation.headline}",
            f"- **Policy Used:** {prompt_res.l1_explanation.policy_version_used}",
            f"- **Mandatory Evidence Available:** {prompt_res.l1_explanation.mandatory_evidence_available}",
            f"- **Precedents Included:** {prompt_res.l1_explanation.historical_precedents_included}",
            f"- **Returned Verdict:** {prompt_res.l1_explanation.verdict_returned}",
            f"- **Policy Approved:** {prompt_res.l1_explanation.prompt_matches_approved_policy}",
            "",
            "## 2. Compiled System Prompt (Outbound to Server 2)",
            "```text",
            prompt_res.system_prompt,
            "```",
            "",
            "## 3. Incident Telemetry Payload (<UNTRUSTED_INCIDENT_DATA>)",
            "```xml",
            prompt_res.incident_payload,
            "```",
            "",
            "## 4. Technical Details & Token Accounting",
            f"- **Prompt Tokens:** {prompt_res.technical_details.prompt_tokens}",
            f"- **Completion Tokens:** {prompt_res.technical_details.completion_tokens}",
            f"- **Total Tokens:** {prompt_res.technical_details.total_tokens}",
            f"- **Latency:** {prompt_res.execution_summary.latency_ms}ms",
            f"- **Generation Settings:** `{json.dumps(prompt_res.technical_details.generation_settings)}`",
        ]
        if prompt_res.raw_model_response:
            lines.extend([
                "",
                "## 5. Raw LLM Response",
                "```json",
                prompt_res.raw_model_response,
                "```",
            ])
        content = "\n".join(lines)
        filename = f"actual_prompt_{incident_id}.md"
        media_type = "text/markdown"

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)

