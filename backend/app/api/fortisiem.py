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
