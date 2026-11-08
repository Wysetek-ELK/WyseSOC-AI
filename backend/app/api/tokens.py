from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.token_analytics_service import TokenAnalyticsService

router = APIRouter(prefix="/tokens", tags=["Token Analytics & Bifurcation"])


@router.get("/analytics")
async def get_token_analytics(
    window_days: int = Query(30, ge=1, le=365),
    process_type: Optional[str] = Query(None),
    model_identifier: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns bifurcated token consumption metrics across all processes:
    - Input (Prompt) Tokens vs Output (Completion) Tokens
    - Breakdown by Process Type (Incident Triage, Batch Triage, Simulation Replay, Policy Testing)
    - Breakdown by Model Identifier
    - Recent Token Transactions Ledger stored on Server 1.
    """
    svc = TokenAnalyticsService(db)
    return await svc.get_bifurcated_analytics(
        window_days=window_days,
        process_type=process_type,
        model_identifier=model_identifier,
    )

