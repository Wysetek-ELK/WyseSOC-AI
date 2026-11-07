from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import async_engine, Base, AsyncSessionLocal
import app.models
from app.api import (
    auth,
    incidents,
    rules,
    imports,
    dashboard,
    users,
    audit,
    investigations,
    prompts,
    learning,
    dry_run,
    evaluations,
    fortisiem,
    system_monitor,
)
from app.models.user import User
from app.utils.security import get_password_hash
from app.services.fortisiem_scheduler import fortisiem_scheduler
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables if they do not exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe migration: ensure ai_verdict column exists on incidents table
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE incidents ADD COLUMN ai_verdict JSON"))
        except Exception:
            pass

    # Seed initial administrator if no users exist
    async with AsyncSessionLocal() as session:
        stmt = select(User).limit(1)
        res = await session.execute(stmt)
        first_user = res.scalar_one_or_none()
        if not first_user:
            admin_user = User(
                username="admin",
                email="admin@ai-verdict.internal",
                hashed_password=get_password_hash("AdminPassword123!"),
                full_name="System Administrator",
                role="Administrator",
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            print("Default Administrator created (username: admin, default credentials)")

        # Self-healing migration: Backfill missing incident timestamps for existing records
        try:
            from app.models.incident import Incident
            from app.services.ingestion_service import extract_incident_timestamps
            from sqlalchemy import or_
            inc_stmt = select(Incident).where(
                or_(Incident.first_seen_epoch.is_(None), Incident.created_at_epoch.is_(None))
            )
            inc_res = await session.execute(inc_stmt)
            unfilled_incidents = inc_res.scalars().all()
            if unfilled_incidents:
                for inc in unfilled_incidents:
                    raw = inc.raw_payload or {}
                    fs, ls, ca, ua = extract_incident_timestamps(raw)
                    if not fs and not ca and inc.created_at:
                        fallback_ms = int(inc.created_at.timestamp() * 1000)
                        fs = fallback_ms
                        ca = fallback_ms
                    if fs and not inc.first_seen_epoch:
                        inc.first_seen_epoch = fs
                    if ca and not inc.created_at_epoch:
                        inc.created_at_epoch = ca
                    if ls and not inc.last_seen_epoch:
                        inc.last_seen_epoch = ls
                    if ua and not inc.updated_at_epoch:
                        inc.updated_at_epoch = ua
                await session.commit()
                print(f"[Startup Migration] Backfilled occurrence timestamps for {len(unfilled_incidents)} incidents.")
        except Exception as exc:
            print(f"[Startup Migration Warning] Timestamp backfill skipped: {exc}")

    # Startup background continuous FortiSIEM poller if enabled
    if getattr(settings, "FORTISIEM_AUTO_POLL_ENABLED", False):
        fortisiem_scheduler.start(
            interval_seconds=getattr(settings, "FORTISIEM_POLL_INTERVAL_SECONDS", 180),
            auto_ai_verdict=getattr(settings, "FORTISIEM_AUTO_AI_VERDICT", True),
        )

    yield

    # Shutdown
    fortisiem_scheduler.stop()
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Verdict: SOC Incident Analysis & SIEM Intelligence Platform",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(incidents.router, prefix=settings.API_V1_STR)
app.include_router(rules.router, prefix=settings.API_V1_STR)
app.include_router(imports.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(investigations.router, prefix=settings.API_V1_STR)
app.include_router(prompts.router, prefix=settings.API_V1_STR)
app.include_router(learning.router, prefix=settings.API_V1_STR)
app.include_router(dry_run.router, prefix=settings.API_V1_STR)
app.include_router(evaluations.router, prefix=settings.API_V1_STR)
app.include_router(fortisiem.router, prefix=settings.API_V1_STR)
app.include_router(system_monitor.router, prefix=settings.API_V1_STR)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "phase": "Phase 3 - Dry-Run Engine & Evaluation Framework",
    }

