from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import async_engine, Base, AsyncSessionLocal
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
)
from app.models.user import User
from app.utils.security import get_password_hash
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables if they do not exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    yield

    # Shutdown
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


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "phase": "Phase 3 - Dry-Run Engine & Evaluation Framework",
    }

