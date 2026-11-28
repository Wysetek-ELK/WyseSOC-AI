"""
AIS 3.2 — Universal Rule Intelligence, Dynamic Rule Contracts, Organizational Context,
Verdict Semantics, and Development Evaluation API Router.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_admin, require_analyst
from app.database import get_db
from app.models.ais32_intelligence import IntelligenceExecutionRecord, OrganizationalContextRecord, RuleContractRecord
from app.models.audit import AuditLog
from app.models.rule import Rule
from app.models.user import User
from app.services.ais32_benchmark_service import AIS32BenchmarkService, AIS_3_2_DEVELOPMENT_COHORT_ID
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.modular_verdict_validator import ModularVerdictValidator
from app.services.organizational_context_service import OrganizationalContextService, SUPPORTED_CONTEXT_TYPES
from app.services.policy_governance import resolve_canonical_rule
from app.services.rule_intelligence_engine import RuleIntelligenceEngine
from app.services.verdict_semantics_engine import VerdictSemanticsEngine

router = APIRouter(prefix="/ais32", tags=["AIS 3.2 Rule Intelligence"])


class ContractOverrideRequest(BaseModel):
    overrides: Dict[str, Any] = Field(default_factory=dict)
    approve: bool = False


class OrgContextCreateRequest(BaseModel):
    customer: str = "DEFAULT"
    context_type: str
    context_value: str
    match_pattern: str = ""
    description: str = ""
    source_system: str = "MANUAL_ADMIN"
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    auto_approve: bool = False


class OrgContextDecisionRequest(BaseModel):
    action: str  # APPROVE | REJECT | REVOKE
    reason: str = ""


@router.get("/overview")
async def get_ais32_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns compact Agent Intelligence Studio Overview metrics without leaking protected holdout answers."""
    rules = (await db.execute(select(Rule))).scalars().all()
    contracts = [await RuleIntelligenceEngine.get_or_build_contract_for_rule(db, r) for r in rules]
    mapped_count = sum(1 for c, _ in contracts if c.rule_archetype != "GENERIC_UNKNOWN")
    approved_count = sum(1 for c, rec in contracts if rec and rec.approval_state == "APPROVED")
    provisional_count = len(contracts) - approved_count

    protected = await AIS32BenchmarkService.verify_protected_cohorts_intact(db)
    latest_exec = (
        await db.execute(select(IntelligenceExecutionRecord).order_by(desc(IntelligenceExecutionRecord.created_at)).limit(1))
    ).scalar_one_or_none()

    latest_eval = None
    if latest_exec:
        try:
            latest_eval = await AIS32BenchmarkService.evaluate_run(db, run_key=latest_exec.run_key, mode=latest_exec.mode)
        except Exception:
            latest_eval = None

    return {
        "engine_version": RuleIntelligenceEngine.ENGINE_VERSION,
        "validator_version": ModularVerdictValidator.VALIDATOR_VERSION,
        "total_rules": len(rules),
        "mapped_rules": mapped_count,
        "approved_contracts": approved_count,
        "provisional_contracts": provisional_count,
        "archetype_count": 11,
        "protected_cohorts": protected,
        "latest_run_summary": {
            "run_key": latest_eval["run_key"],
            "cohort_key": latest_eval["cohort_key"],
            "mode": latest_eval["mode"],
            "raw_llm": latest_eval["raw_llm_metrics"],
            "validated_app": latest_eval["validated_app_metrics"],
            "effective_operational": latest_eval["effective_operational_metrics"],
        } if latest_eval else None,
        "ais33_readiness": AIS32BenchmarkService.compute_ais33_holdout_plan(),
    }


@router.get("/archetypes")
async def list_universal_archetypes(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "registry_version": DetectionArchetypeRegistry.REGISTRY_VERSION,
        "canonical_archetypes": list(VerdictSemanticsEngine.list_semantic_mappings()),
        "validator_modules": ModularVerdictValidator.get_module_registry(),
    }


@router.get("/semantics")
async def list_verdict_semantics(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "status": "PROVISIONAL_PENDING_SOC_APPROVAL",
        "mappings": VerdictSemanticsEngine.list_semantic_mappings(),
    }


@router.get("/contracts")
async def list_rule_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rules = (await db.execute(select(Rule).order_by(Rule.name.asc()))).scalars().all()
    items: List[Dict[str, Any]] = []
    for r in rules:
        contract, rec = await RuleIntelligenceEngine.get_or_build_contract_for_rule(db, r)
        items.append({
            "rule_db_id": r.id,
            "fortisiem_rule_id": contract.fortisiem_rule_id,
            "rule_name": contract.rule_name,
            "source_vendor": contract.source_vendor,
            "rule_archetype": contract.rule_archetype,
            "secondary_archetype": contract.secondary_archetype,
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "approval_state": contract.approval_state.value,
            "mandatory_evidence_fields": contract.mandatory_evidence_fields,
            "approved_organizational_context_types": contract.approved_organizational_context_types,
            "is_supported_rule": contract.is_supported_rule,
            "contract_hash": contract.contract_hash,
            "persisted": rec is not None,
        })
    return {"total": len(items), "items": items}


@router.get("/contracts/{rule_identifier}")
async def get_rule_contract_detail(
    rule_identifier: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rule = await resolve_canonical_rule(db, rule_identifier)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_identifier}' not found.")
    contract, _ = await RuleIntelligenceEngine.get_or_build_contract_for_rule(db, rule)
    return contract.model_dump(mode="json")


@router.post("/contracts/{rule_identifier}")
async def update_or_approve_rule_contract(
    rule_identifier: str,
    req: ContractOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rule = await resolve_canonical_rule(db, rule_identifier)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_identifier}' not found.")
    try:
        contract, rec = await RuleIntelligenceEngine.save_contract_version(
            db,
            rule=rule,
            overrides=req.overrides,
            created_by=current_user.username,
            approve=req.approve,
            reviewer=current_user.username if req.approve else None,
        )
        db.add(
            AuditLog(
                user_id=current_user.id,
                username=current_user.username,
                action="RULE_CONTRACT_SAVED",
                resource_type="RULE_CONTRACT",
                resource_id=rec.id,
                details={"rule_id": rule.rule_id, "version": contract.contract_version, "approved": req.approve},
            )
        )
        await db.commit()
        return contract.model_dump(mode="json")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/org-context/types")
async def list_org_context_types(
    current_user: User = Depends(get_current_active_user),
):
    return {"supported_types": list(SUPPORTED_CONTEXT_TYPES)}


@router.get("/org-context")
async def list_org_context(
    customer: Optional[str] = Query(None),
    context_type: Optional[str] = Query(None),
    only_approved: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user_cust = getattr(current_user, "customer", None)
    eff_customer = customer
    if current_user.role != "Administrator" and user_cust and user_cust != "DEFAULT":
        if customer and customer != user_cust:
            raise HTTPException(status_code=403, detail="Cross-tenant organizational context access denied.")
        eff_customer = user_cust
    rows = await OrganizationalContextService.list_records(
        db, customer=eff_customer, context_type=context_type, only_approved=only_approved
    )
    return {
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "customer": r.customer,
                "context_type": r.context_type,
                "context_value": r.context_value,
                "match_pattern": r.match_pattern,
                "description": r.description,
                "source_system": r.source_system,
                "verification_status": r.verification_status,
                "approval_status": r.approval_status,
                "approved_by": r.approved_by,
                "valid_from": r.valid_from.isoformat() if r.valid_from else None,
                "valid_until": r.valid_until.isoformat() if r.valid_until else None,
                "record_version": r.record_version,
            }
            for r in rows
        ],
    }


@router.post("/org-context", status_code=status.HTTP_201_CREATED)
async def create_org_context(
    req: OrgContextCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    user_cust = getattr(current_user, "customer", None)
    if current_user.role != "Administrator" and user_cust and user_cust != "DEFAULT" and req.customer != user_cust:
        raise HTTPException(status_code=403, detail="Cross-tenant organizational context creation denied.")
    if req.auto_approve and current_user.role != "Administrator":
        raise HTTPException(status_code=403, detail="Only Administrators may auto-approve organizational context.")
    try:
        rec = await OrganizationalContextService.create_context_record(
            db,
            customer=req.customer,
            context_type=req.context_type,
            context_value=req.context_value,
            match_pattern=req.match_pattern,
            description=req.description,
            source_system=req.source_system,
            valid_from=req.valid_from,
            valid_until=req.valid_until,
            metadata_json=req.metadata_json,
            created_by=current_user.username,
            auto_approve=req.auto_approve,
        )
        return {"id": rec.id, "approval_status": rec.approval_status, "customer": rec.customer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/org-context/{record_id}/decision")
async def decide_org_context(
    record_id: str,
    req: OrgContextDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        rec = await OrganizationalContextService.approve_or_revoke_record(
            db,
            record_id=record_id,
            action=req.action,
            actor_username=current_user.username,
            actor_customer=getattr(current_user, "customer", None),
            is_admin=(current_user.role == "Administrator"),
            reason=req.reason,
        )
        return {"id": rec.id, "approval_status": rec.approval_status, "record_version": rec.record_version}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/cohorts/development/ensure")
async def ensure_development_cohort(
    target_min: int = Query(60, ge=10, le=100),
    target_max: int = Query(100, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await AIS32BenchmarkService.build_development_cohort(
        db,
        cohort_key=AIS_3_2_DEVELOPMENT_COHORT_ID,
        target_min=target_min,
        target_max=target_max,
    )


@router.post("/runs/execute")
async def execute_ais32_run(
    cohort_key: str = Query(AIS_3_2_DEVELOPMENT_COHORT_ID),
    mode: str = Query("MODE_B", pattern="^(MODE_A|MODE_B|A|B)$"),
    run_key: Optional[str] = Query(None),
    incident_ids: Optional[str] = Query(None),
    max_incidents: Optional[int] = Query(None, ge=1, le=100),
    max_completion_tokens: int = Query(1024, ge=256, le=2048),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    target_fids = [x.strip() for x in incident_ids.split(",") if x.strip()] if incident_ids else None
    try:
        return await AIS32BenchmarkService.execute_mode_run(
            db,
            cohort_key=cohort_key,
            mode=mode,
            run_key=run_key,
            target_fids=target_fids,
            max_incidents=max_incidents,
            max_completion_tokens=max_completion_tokens,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except RuntimeError as re_err:
        raise HTTPException(status_code=503, detail=str(re_err))


@router.get("/runs/{run_key}/evaluate")
async def evaluate_ais32_run(
    run_key: str,
    mode: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        return await AIS32BenchmarkService.evaluate_run(db, run_key=run_key, mode=mode)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/ais33-readiness")
async def get_ais33_readiness(
    current_user: User = Depends(get_current_active_user),
):
    return AIS32BenchmarkService.compute_ais33_holdout_plan()
