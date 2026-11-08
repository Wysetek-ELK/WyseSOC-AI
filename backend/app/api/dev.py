"""
Development & Diagnostic API router.
Strictly disabled in production environments (REQ-08).
"""
from fastapi import APIRouter, HTTPException, status
from app.config import settings

router = APIRouter(prefix="/dev", tags=["Development Diagnostics"])


@router.get("/status")
async def dev_diagnostics():
    if settings.APP_ENV.lower() in ("production", "prod"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return {
        "status": "dev_mode_active",
        "env": settings.APP_ENV,
        "mock_fallback_allowed": settings.LOCAL_LLM_ALLOW_MOCK_FALLBACK,
    }

