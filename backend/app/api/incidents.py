from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
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
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.factory import get_model_provider
from app.services.prompt_studio_service import PromptStudioService, COMMON_SOC_BASELINE
from app.models.prompt import RulePrompt
from app.api.deps import get_current_user

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    resolution: Optional[str] = Query(None),
    blind_review: bool = Query(False, description="Hide ground truth for unbiased analyst review"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = IncidentService(db)
    items, total = await service.list_incidents(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        status=status,
        rule_id=rule_id,
        resolution=resolution,
        blind_review=blind_review,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return IncidentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
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
    incident = await service.get_incident(identifier, blind_review=blind_review)
    if not incident:
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

    return ModelFacingIncidentPayload(**payload_dict)


@router.post("/{identifier}/ai-verdict")
async def request_incident_ai_verdict(
    identifier: str,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand single incident AI evaluation against Server 2 Local LLM.
    Strictly sanitizes telemetry through the ground-truth isolation allowlist.
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

    # Auto-resolve Rule if incident is unmapped
    rule = incident.rule
    if not rule and incident.event_type:
        r_q = await db.execute(
            select(Rule).where((Rule.event_type == incident.event_type) | (Rule.rule_id == incident.event_type))
        )
        rule = r_q.scalars().first()

        if not rule:
            # Auto-provision Rule for unmapped SIEM event type
            rule = Rule(
                rule_id=incident.event_type,
                name=incident.title if incident.title and incident.title != "No description provided by SIEM." else incident.event_type,
                event_type=incident.event_type,
                severity=incident.severity or "MEDIUM",
                description=f"Auto-mapped SIEM detection rule for {incident.event_type}",
                status="ACTIVE",
            )
            db.add(rule)
            await db.commit()
            await db.refresh(rule)

        # Associate this incident with the resolved rule
        incident.rule_id = rule.id
        incident.rule = rule
        db.add(incident)
        await db.commit()

        # Also auto-link any sibling unmapped incidents sharing this event_type
        await db.execute(
            update(Incident)
            .where(Incident.event_type == incident.event_type, Incident.rule_id.is_(None))
            .values(rule_id=rule.id)
        )
        await db.commit()

    # 1. Build model-facing payload (sanitized of ground-truth closure fields)
    payload_dict = build_model_facing_payload(
        incident=incident,
        rule=rule,
        events=incident.events
    )

    # 2. Resolve prompt text with full Level-2 SOC criteria
    prompt_service = PromptStudioService(db)
    prompt_text = COMMON_SOC_BASELINE
    prompt_ver_num = 1

    if rule:
        rp = await prompt_service.get_or_create_rule_prompt(rule.id)
        if rp and rp.versions:
            active_v = next((v for v in rp.versions if v.id == rp.active_version_id), rp.versions[0])
            prompt_ver_num = active_v.version_number
            parts = [active_v.common_prompt or COMMON_SOC_BASELINE]
            if active_v.rule_specific_prompt:
                parts.append(active_v.rule_specific_prompt)
            if active_v.tp_indicators and active_v.tp_indicators not in (active_v.rule_specific_prompt or ""):
                parts.append(f"### TRUE POSITIVE CRITERIA (MALICIOUS ATTACK):\n{active_v.tp_indicators}")
            if active_v.fp_indicators and active_v.fp_indicators not in (active_v.rule_specific_prompt or ""):
                parts.append(f"### FALSE POSITIVE CRITERIA (BENIGN / OPERATIONAL NOISE):\n{active_v.fp_indicators}")
            if active_v.required_evidence and active_v.required_evidence not in (active_v.rule_specific_prompt or ""):
                parts.append(f"### REQUIRED EVIDENCE EVALUATION:\n{active_v.required_evidence}")
            if active_v.missing_info_criteria and active_v.missing_info_criteria not in (active_v.rule_specific_prompt or ""):
                parts.append(f"### WHEN TO VOTE REQUIRES_ATTENTION:\n{active_v.missing_info_criteria}")
            prompt_text = "\n\n".join(parts)

        # 3. Dynamic In-Context Learning (Few-Shot RAG from Verified Learning History)
        lr_q = await db.execute(
            select(LearningRecord)
            .where(
                (LearningRecord.rule_id == rule.id) |
                (LearningRecord.verification_status == "VERIFIED")
            )
            .order_by(desc(LearningRecord.feedback_timestamp))
            .limit(3)
        )
        learning_records = lr_q.scalars().all()
        if learning_records:
            few_shot_lines = ["\n\n### VERIFIED HISTORICAL PRECEDENTS (FEW-SHOT EXAMPLES):"]
            for lr in learning_records:
                prec_title = lr.incident.title if lr.incident else "Historical Alert"
                few_shot_lines.append(
                    f"- Precedent: {prec_title}\n"
                    f"  Verified Determination: {lr.verified_verdict}\n"
                    f"  Analyst Rationale: {lr.analyst_explanation[:250]}"
                )
            prompt_text += "\n".join(few_shot_lines)

    # 4. Call Server 2 Local LLM Provider
    rule_spec = {
        "id": rule.id if rule else (incident.rule_id or "UNKNOWN"),
        "name": rule.name if rule else incident.title,
        "severity": rule.severity if rule else incident.severity,
        "description": rule.description if rule else "",
    }

    provider = get_model_provider("OPENAI_COMPATIBLE")
    verdict = await provider.analyze_incident(
        incident_payload=payload_dict,
        rule_spec=rule_spec,
        prompt_text=prompt_text,
        prompt_version_number=prompt_ver_num,
    )

    verdict_data = {
        "incident_id": incident.incident_id,
        "verdict": verdict.verdict,
        "confidence": verdict.confidence,
        "reason": verdict.reason,
        "supporting_evidence": verdict.supporting_evidence,
        "missing_evidence": verdict.missing_evidence,
        "analyst_questions": verdict.analyst_questions,
        "latency_ms": verdict.latency_ms,
        "model_identifier": verdict.model_identifier,
        "prompt_tokens": getattr(verdict, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(verdict, "completion_tokens", 0) or 0,
        "total_tokens": getattr(verdict, "total_tokens", 0) or 0,
        "is_simulated": verdict.is_simulated,
        "rule_name": rule.name if rule else incident.title,
        "severity": incident.severity,
        "evaluated_at": datetime.utcnow().isoformat(),
        "evaluated_by_user": current_user.username,
    }

    # Store AI verdict on incident for future use
    incident.ai_verdict = verdict_data
    db.add(incident)
    await db.commit()

    # 5. Audit log the AI verdict request
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="AI_VERDICT_REQUEST",
        resource_type="INCIDENT",
        resource_id=incident.incident_id,
        details={
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "latency_ms": verdict.latency_ms,
            "model": verdict.model_identifier,
            "total_tokens": verdict_data["total_tokens"],
            "is_simulated": verdict.is_simulated,
        },
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(audit)
    await db.commit()

    return verdict_data

