from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import require_role, get_current_user
from app.config import settings
from app.schemas.fortisiem import (
    FortiSIEMPullRequest,
    FortiSIEMPullResponse,
    FortiSIEMStatusResponse,
    FortiSIEMConfigResponse,
    FortiSIEMConfigUpdate,
    FortiSIEMTestConnectionRequest,
    FortiSIEMTestConnectionResponse,
)
from app.services.fortisiem_service import FortiSIEMService

router = APIRouter(prefix="/fortisiem", tags=["FortiSIEM Live Connector"])


@router.get("/status", response_model=FortiSIEMStatusResponse)
async def get_fortisiem_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Checks FortiSIEM connection status and available fixture IDs for testing.
    """
    service = FortiSIEMService(db)
    is_configured = bool(settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip())
    mode = "LIVE" if is_configured else "FIXTURE_FALLBACK"
    sample_ids = service.get_available_fixture_ids()

    return FortiSIEMStatusResponse(
        is_configured=is_configured,
        host=settings.FORTISIEM_HOST if is_configured else "Not Configured (Using Fixture Mode)",
        username=settings.FORTISIEM_USERNAME if is_configured else "",
        verify_ssl=settings.FORTISIEM_VERIFY_SSL,
        mode=mode,
        sample_incident_ids=sample_ids,
    )


@router.get("/config", response_model=FortiSIEMConfigResponse)
async def get_fortisiem_config(
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Returns current FortiSIEM supervisor configuration with passwords masked.
    Restricted to Administrator role.
    """
    return FortiSIEMService.get_config()


@router.post("/config", response_model=FortiSIEMConfigResponse)
async def update_fortisiem_config(
    config: FortiSIEMConfigUpdate,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Updates FortiSIEM supervisor IP/URL, credentials, and settings dynamically and persists to .env.
    Restricted to Administrator role.
    """
    updated = FortiSIEMService.update_config(
        host=config.host,
        username=config.username,
        password=config.password,
        verify_ssl=config.verify_ssl,
        timeout=config.timeout,
        mock_fallback=config.mock_fallback,
    )
    return updated


@router.post("/test-connection", response_model=FortiSIEMTestConnectionResponse)
async def test_fortisiem_connection(
    req: FortiSIEMTestConnectionRequest,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Probes the specified FortiSIEM supervisor endpoint to verify connectivity and credentials.
    Restricted to Administrator role.
    """
    res = await FortiSIEMService.test_siem_connection(
        host=req.host,
        username=req.username,
        password=req.password,
        verify_ssl=req.verify_ssl,
        timeout=req.timeout,
    )
    return FortiSIEMTestConnectionResponse(**res)


@router.post("/fetch", response_model=FortiSIEMPullResponse)
async def fetch_incident(
    req: FortiSIEMPullRequest,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls an incident from FortiSIEM by Incident ID, ingests telemetry and raw events,
    safely isolates historical ground truth, and prepares it for AI investigation.
    """
    service = FortiSIEMService(db)
    try:
        result = await service.pull_and_ingest(
            incident_id=req.incident_id,
            force_refresh=req.force_refresh,
            username=current_user.username,
        )
        return FortiSIEMPullResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while pulling incident from FortiSIEM: {str(exc)}"
        )
