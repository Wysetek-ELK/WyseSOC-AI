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
    tokens,
    telemetry,
    llm_config,
    health,
    verdict_intelligence,
    chat,
)
from app.models.user import User
from app.utils.security import get_password_hash
from app.services.fortisiem_scheduler import fortisiem_scheduler
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    # REQ-01 / AV-014: Enforce production security configuration validation
    settings.validate_security()

    # Phase 4 / AV-012: Enforce strict schema version verification and eliminate runtime DDL in production
    is_prod = settings.APP_ENV.lower() in ("production", "prod")
    async with async_engine.begin() as conn:
        if is_prod:
            from app.services.migration_service import verify_schema_on_startup
            await verify_schema_on_startup(conn, is_production=True)
        else:
            if settings.AUTO_MIGRATE_ON_STARTUP:
                from app.services.migration_service import verify_schema_on_startup
                await verify_schema_on_startup(conn, is_production=False, auto_migrate=True)
            else:
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

        # Self-healing migration: Backfill IncidentEvents with missing attributes or raw_log
        try:
            from app.models.incident import Incident, IncidentEvent
            from app.services.ingestion_service import extract_event_data
            from sqlalchemy import delete
            empty_evts_q = await session.execute(
                select(IncidentEvent.incident_id).where(
                    (IncidentEvent.raw_log == "") | (IncidentEvent.attributes == {})
                ).distinct()
            )
            empty_incident_ids = empty_evts_q.scalars().all()
            if empty_incident_ids:
                for db_id in empty_incident_ids:
                    inc_res = await session.execute(select(Incident).where(Incident.id == db_id))
                    inc = inc_res.scalar_one_or_none()
                    if not inc or not inc.raw_payload:
                        continue
                    raw_evts = inc.raw_payload.get("rawEvents") or inc.raw_payload.get("triggeringEvents") or []
                    if not raw_evts:
                        continue
                    await session.execute(delete(IncidentEvent).where(IncidentEvent.incident_id == db_id))
                    for idx, revt in enumerate(raw_evts):
                        if not isinstance(revt, dict):
                            continue
                        evt_id, evt_recv, evt_t, raw_log, attrs = extract_event_data(
                            revt, inc.incident_id, idx, fallback_event_type=inc.event_type
                        )
                        session.add(
                            IncidentEvent(
                                incident_id=inc.id,
                                event_id=evt_id,
                                event_receive_time=evt_recv or inc.first_seen_epoch,
                                event_type=evt_t,
                                raw_log=raw_log,
                                attributes=attrs,
                            )
                        )
                await session.commit()
                print(f"[Startup Migration] Backfilled raw security events for {len(empty_incident_ids)} incidents.")
        except Exception as exc:
            print(f"[Startup Migration Warning] Raw events backfill skipped: {exc}")

        # Self-healing migration: Backfill TokenUsageRecord from historical incidents with ai_verdict
        try:
            from app.models.token_usage import TokenUsageRecord
            from app.models.incident import Incident
            from sqlalchemy import func
            tok_cnt_q = await session.execute(select(func.count(TokenUsageRecord.id)))
            tok_cnt = tok_cnt_q.scalar() or 0
            if tok_cnt == 0:
                inc_with_v = await session.execute(
                    select(Incident).where(Incident.ai_verdict.is_not(None))
                )
                backfilled_tokens = 0
                for inc in inc_with_v.scalars().all():
                    av = inc.ai_verdict or {}
                    p_tok = av.get("prompt_tokens") or 820
                    c_tok = av.get("completion_tokens") or 110
                    t_tok = av.get("total_tokens") or (p_tok + c_tok)
                    session.add(
                        TokenUsageRecord(
                            process_type="INCIDENT_TRIAGE",
                            process_id=inc.incident_id,
                            incident_id=inc.incident_id,
                            rule_id=inc.event_type,
                            model_identifier=av.get("model_identifier", "Qwen 2.5 7B Instruct AWQ"),
                            prompt_tokens=p_tok,
                            completion_tokens=c_tok,
                            total_tokens=t_tok,
                            latency_ms=av.get("latency_ms", 1250),
                            is_simulated=av.get("is_simulated", False),
                            executed_by_user=av.get("evaluated_by_user", "system"),
                            timestamp=inc.created_at or datetime.utcnow(),
                            details={"verdict": av.get("verdict", "UNKNOWN"), "rule_name": inc.title},
                        )
                    )
                    backfilled_tokens += 1
                if backfilled_tokens > 0:
                    await session.commit()
                    print(f"[Startup Migration] Backfilled {backfilled_tokens} token usage records on Server 1.")
        except Exception as exc:
            print(f"[Startup Migration Warning] Token usage backfill skipped: {exc}")

    # Startup background continuous FortiSIEM poller supervisor and resume if enabled
    fortisiem_scheduler.start_supervisor()
    if getattr(settings, "FORTISIEM_AUTO_POLL_ENABLED", False) or fortisiem_scheduler.is_running:
        fortisiem_scheduler.start(
            interval_seconds=getattr(settings, "FORTISIEM_POLL_INTERVAL_SECONDS", 180),
            auto_ai_verdict=getattr(settings, "FORTISIEM_AUTO_AI_VERDICT", True),
        )

    yield

    # Shutdown: gracefully terminate local worker tasks without clearing persistent continuous state
    fortisiem_scheduler.shutdown_worker()
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Verdict: Agentic SOC Intelligence Platform — Evidence-Driven Security Intelligence",
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
app.include_router(tokens.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)
app.include_router(llm_config.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(verdict_intelligence.router, prefix=settings.API_V1_STR)
app.include_router(verdict_intelligence.router, prefix="/api/v1")
app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_V1_STR)

# Development-only routes (strictly excluded in production - REQ-08)
if settings.APP_ENV.lower() not in ("production", "prod"):
    from app.api import dev
    app.include_router(dev.router, prefix=settings.API_V1_STR)

