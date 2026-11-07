from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.system_monitor_service import SystemMonitorService

router = APIRouter(prefix="/system/servers", tags=["System Server Telemetry"])


@router.get("/live")
async def get_live_server_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch live real-time utilization metrics for Server 1 and Server 2."""
    service = SystemMonitorService(db)
    return await service.get_live_metrics()


@router.get("/history")
async def get_historical_server_metrics(
    window: str = Query("24h", description="Time window: 1h, 6h, 24h, 7d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch historical utilization time-series for Server 1 and Server 2."""
    if window not in ("1h", "6h", "24h", "7d"):
        window = "24h"
    service = SystemMonitorService(db)
    return await service.get_historical_metrics(window=window)

