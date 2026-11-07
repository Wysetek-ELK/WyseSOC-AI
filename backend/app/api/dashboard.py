from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardMetricsResponse
from app.services.dashboard_service import DashboardService
from app.services.model_provider.factory import get_model_provider
from app.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_metrics()


@router.get("/llm-status")
async def get_llm_status(
    current_user: User = Depends(get_current_user),
):
    provider = get_model_provider("OPENAI_COMPATIBLE")
    health = await provider.get_health()
    return {
        "status": health.status,
        "is_healthy": health.status == "HEALTHY",
        "model": settings.LOCAL_LLM_MODEL_NAME,
        "latency_ms": health.latency_ms,
        "message": health.message,
    }

