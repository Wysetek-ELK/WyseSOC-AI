from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.api.deps import require_role, get_current_user
from app.schemas.llm_config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMTestConnectionRequest,
    LLMTestConnectionResponse,
)
from app.services.llm_config_service import LLMConfigService

router = APIRouter(prefix="/llm", tags=["LLM Server 2 Configuration"])


@router.get("/config", response_model=LLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
):
    """
    Returns current Local LLM Server 2 configuration, active base URL, and reachability.
    Accessible to authenticated users.
    """
    return await LLMConfigService.get_config()


@router.post("/config", response_model=LLMConfigResponse)
async def update_llm_config(
    config: LLMConfigUpdate,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Updates the LLM Server 2 IP address, port, and inference settings dynamically and persists to .env.
    Restricted to Administrator role.
    """
    try:
        updated = LLMConfigService.update_config(config)
        try:
            from app.services.fortisiem_scheduler import fortisiem_scheduler
            if fortisiem_scheduler.auto_ai_verdict:
                fortisiem_scheduler.trigger_pending_reconciliation(username=current_user.username)
        except Exception:
            pass
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update LLM configuration: {str(e)}")


@router.post("/test-connection", response_model=LLMTestConnectionResponse)
async def test_llm_connection(
    req: LLMTestConnectionRequest,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Probes the specified LLM Server 2 endpoint to verify connectivity, latency, and available models.
    Restricted to Administrator role.
    """
    result = await LLMConfigService.test_connection(req)
    if result.success:
        try:
            from app.config import settings
            from app.services.fortisiem_scheduler import fortisiem_scheduler
            tested_base = LLMConfigService.parse_llm_url(
                raw_input=req.host,
                default_port=req.port or 8000,
                default_proto=req.protocol or "http",
            )["base_url"]
            active_base = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)["base_url"]
            if tested_base == active_base and fortisiem_scheduler.auto_ai_verdict:
                fortisiem_scheduler.trigger_pending_reconciliation(username=current_user.username)
        except Exception:
            pass
    return result
