import asyncio
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Response, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import psutil

from app.config import settings
from app.database import get_db, check_db_health, is_postgres
from app.workers.celery_app import is_redis_available, get_queue_depth
from app.services.gpu_manager import gpu_workload_manager
from app.services.ai_verdict_service import AIVerdictService
from app.models.incident import Incident
from app.models.dry_run import DryRunResult

router = APIRouter(tags=["Observability & Health"])


@router.get("/health")
@router.get("/api/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive Component-Level Health Check Endpoint (P4-REQ-07).
    Inspects real infrastructure health across Server 1 and Server 2:
    - Database connectivity, query latency, connection pool utilization.
    - Redis & Celery task broker status.
    - Local LLM GPU inference status and circuit breaker state.
    - Hardware system utilization (genuine psutil telemetry - ZERO fabricated numbers).
    """
    overall_status = "healthy"
    components: Dict[str, Any] = {}

    # 1. Database Health Check
    db_health = await check_db_health(db)
    components["database"] = db_health
    if not db_health.get("connected"):
        overall_status = "unhealthy"

    # 2. Redis / Celery Broker Health Check (skip blocking socket connect when disabled)
    if settings.USE_ASYNC_CELERY:
        redis_ok = is_redis_available()
        queue_depth = get_queue_depth("live_triage")
    else:
        redis_ok = False
        queue_depth = 0
    components["redis_celery"] = {
        "status": "healthy" if redis_ok else ("disabled" if not settings.USE_ASYNC_CELERY else "unreachable"),
        "reachable": redis_ok,
        "broker_url_redacted": settings.CELERY_BROKER_URL.split("@")[-1] if "@" in settings.CELERY_BROKER_URL else settings.CELERY_BROKER_URL,
        "live_triage_queue_depth": queue_depth,
    }
    if settings.USE_ASYNC_CELERY and not redis_ok:
        if overall_status == "healthy":
            overall_status = "degraded"

    # 3. Local LLM Server 2 & Circuit Breaker Health Check (bounded <= 2s so /api/health never times out)
    try:
        llm_online = await asyncio.wait_for(AIVerdictService.is_local_llm_available(), timeout=2.0)
    except Exception:
        llm_online = False
    gpu_telemetry = gpu_workload_manager.get_telemetry()
    cb_state = gpu_telemetry.get("circuit_breaker", {}).get("state", "CLOSED")
    components["local_llm"] = {
        "status": "healthy" if llm_online else "offline",
        "reachable": llm_online,
        "base_url": settings.LOCAL_LLM_BASE_URL,
        "model_name": settings.LOCAL_LLM_MODEL_NAME,
        "circuit_breaker_state": cb_state,
        "active_concurrent_slots": gpu_telemetry.get("active_requests", 0),
        "max_concurrent_slots": gpu_telemetry.get("max_concurrent_slots", 4),
    }
    if not llm_online or cb_state != "CLOSED":
        if overall_status == "healthy":
            overall_status = "degraded"

    # 4. Host Hardware Telemetry (psutil real measurements)
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/") if hasattr(psutil, "disk_usage") else None
        components["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024 ** 3), 2),
            "memory_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": disk.percent if disk else None,
        }
    except Exception as e:
        components["system"] = {"error": str(e)}

    return {
        "status": overall_status,
        "environment": settings.APP_ENV,
        "version": settings.VERSION,
        "timestamp": time.time(),
        "components": components,
    }


@router.get("/metrics")
@router.get("/api/metrics")
async def get_prometheus_metrics(
    format: Optional[str] = Query(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Prometheus and Structured Metrics Endpoint (P4-REQ-07).
    Exports operational counts, validation stats, latency, and queue depths.
    """
    accept_header = request.headers.get("accept", "") if request else ""
    wants_json = (format == "json") or ("application/json" in accept_header and "text/plain" not in accept_header)

    # Calculate real incident verdict statistics
    tp_count = 0
    fp_count = 0
    attn_count = 0
    try:
        inc_results = await db.execute(select(Incident.ai_verdict).where(Incident.ai_verdict.is_not(None)))
        for row in inc_results.scalars():
            if isinstance(row, dict):
                v = row.get("verdict", "")
                if v == "TRUE_POSITIVE":
                    tp_count += 1
                elif v == "FALSE_POSITIVE":
                    fp_count += 1
                elif v == "REQUIRES_ATTENTION":
                    attn_count += 1
    except Exception:
        pass

    db_health = await check_db_health(db)
    db_latency = db_health.get("latency_ms", 0.0) / 1000.0  # seconds
    queue_depth = get_queue_depth("live_triage")
    gpu_telem = gpu_workload_manager.get_telemetry()
    cb_trips = gpu_telem.get("circuit_breaker", {}).get("total_trips", 0)
    active_gpu = gpu_telem.get("active_requests", 0)

    try:
        cpu_pct = psutil.cpu_percent(interval=None)
        mem_pct = psutil.virtual_memory().percent
    except Exception:
        cpu_pct = 0.0
        mem_pct = 0.0

    if wants_json:
        return {
            "ai_verdict_incidents_total": {
                "true_positive": tp_count,
                "false_positive": fp_count,
                "requires_attention": attn_count,
            },
            "ai_verdict_db_latency_seconds": db_latency,
            "ai_verdict_queue_depth": queue_depth,
            "ai_verdict_circuit_breaker_trips_total": cb_trips,
            "ai_verdict_active_inference_requests": active_gpu,
            "ai_verdict_system_cpu_percent": cpu_pct,
            "ai_verdict_system_memory_percent": mem_pct,
        }

    # Prometheus Text Format
    lines = [
        "# HELP ai_verdict_incidents_total Total security incidents evaluated by AI Verdict engine",
        "# TYPE ai_verdict_incidents_total counter",
        f'ai_verdict_incidents_total{{verdict="true_positive"}} {tp_count}',
        f'ai_verdict_incidents_total{{verdict="false_positive"}} {fp_count}',
        f'ai_verdict_incidents_total{{verdict="requires_attention"}} {attn_count}',
        "",
        "# HELP ai_verdict_db_latency_seconds Database health check probe query latency in seconds",
        "# TYPE ai_verdict_db_latency_seconds gauge",
        f"ai_verdict_db_latency_seconds {db_latency:.4f}",
        "",
        "# HELP ai_verdict_queue_depth Pending triage tasks in live_triage queue",
        "# TYPE ai_verdict_queue_depth gauge",
        f"ai_verdict_queue_depth {queue_depth}",
        "",
        "# HELP ai_verdict_circuit_breaker_trips_total Total times GPU Server 2 circuit breaker tripped OPEN",
        "# TYPE ai_verdict_circuit_breaker_trips_total counter",
        f"ai_verdict_circuit_breaker_trips_total {cb_trips}",
        "",
        "# HELP ai_verdict_active_inference_requests Currently executing GPU inference requests",
        "# TYPE ai_verdict_active_inference_requests gauge",
        f"ai_verdict_active_inference_requests {active_gpu}",
        "",
        "# HELP ai_verdict_system_cpu_percent Host CPU utilization percent",
        "# TYPE ai_verdict_system_cpu_percent gauge",
        f"ai_verdict_system_cpu_percent {cpu_pct:.1f}",
        "",
        "# HELP ai_verdict_system_memory_percent Host memory utilization percent",
        "# TYPE ai_verdict_system_memory_percent gauge",
        f"ai_verdict_system_memory_percent {mem_pct:.1f}",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain; version=0.0.4; charset=utf-8")
