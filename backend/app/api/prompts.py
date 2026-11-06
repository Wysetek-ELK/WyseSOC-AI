from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.services.prompt_studio_service import PromptStudioService
from app.services.audit_service import AuditService
from app.schemas.prompt import (
    RulePromptResponse,
    PromptVersionResponse,
    PromptVersionCreate,
    PromptApprovalRequest,
    PromptRollbackRequest,
)

router = APIRouter(prefix="/prompts", tags=["Prompt Studio"])


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
                active_v = PromptVersionResponse.from_orm(v)
                break

    return RulePromptResponse(
        id=prompt.id,
        rule_id=prompt.rule_id,
        rule_name=prompt.rule.name if prompt.rule else None,
        rule_event_type=prompt.rule.event_type if prompt.rule else None,
        title=prompt.title,
        active_version_id=prompt.active_version_id,
        active_version=active_v,
        versions=[PromptVersionResponse.from_orm(v) for v in prompt.versions],
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


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

    return PromptVersionResponse.from_orm(ver)


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

    return PromptVersionResponse.from_orm(ver)


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
        details={"version_number": ver.version_number, "status": "APPROVED"},
    )

    return PromptVersionResponse.from_orm(ver)


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

    return PromptVersionResponse.from_orm(ver)

