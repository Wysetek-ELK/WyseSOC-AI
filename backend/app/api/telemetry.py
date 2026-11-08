from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.telemetry_timeline_service import TelemetryTimelineService

router = APIRouter(prefix="/telemetry", tags=["Historical Telemetry Timeline"])


@router.get("/timeline")
async def get_global_telemetry_timeline(
    limit: int = Query(50, ge=1, le=200),
    stage: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieves global historical telemetry timeline records stored on Server 1.
    """
    svc = TelemetryTimelineService(db)
    return await svc.get_global_telemetry_timeline(limit=limit, stage=stage)

