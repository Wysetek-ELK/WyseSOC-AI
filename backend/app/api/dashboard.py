from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardMetricsResponse
from app.services.dashboard_service import DashboardService
from app.services.model_provider.factory import get_model_provider
from app.services.provenance import classify_endpoint_status
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
    is_healthy = health.status == "HEALTHY"
    prov = classify_endpoint_status(
        is_healthy=is_healthy,
        raw_status=health.status,
        base_url=settings.LOCAL_LLM_BASE_URL,
        metrics_available=False,
        configured_provider="OPENAI_COMPATIBLE",
    )
    return {
        "status": health.status,
        "is_healthy": is_healthy,
        "model": settings.LOCAL_LLM_MODEL_NAME,
        "latency_ms": health.latency_ms,
        "message": health.message,
        "configured_provider": prov["configured_provider"],
        "endpoint_provenance": prov["endpoint_provenance"],
        "current_s2_health": prov["current_s2_health"],
        "gpu_telemetry_verified": prov["gpu_telemetry_verified"],
        "test_environment": prov["test_environment"],
    }

