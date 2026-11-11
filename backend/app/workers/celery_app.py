import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("ai_verdict.workers")

try:
    from celery import Celery
    celery_app = Celery(
        "ai_verdict",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    # Production Celery Configuration for Server 1 Worker
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=settings.CELERY_TASK_TIMEOUT_SECONDS,
        task_soft_time_limit=max(10, settings.CELERY_TASK_TIMEOUT_SECONDS - 15),
        # Bounded concurrency per worker process
        worker_concurrency=4,
        worker_prefetch_multiplier=1,
        task_acks_late=True,  # Guarantee message redelivery if worker crashes before ack
        task_reject_on_worker_lost=True,
        # Priority queues
        task_queues={
            "live_triage": {
                "exchange": "ai_verdict",
                "routing_key": "incident.live",
            },
            "simulation_replay": {
                "exchange": "ai_verdict",
                "routing_key": "simulation.replay",
            },
            "maintenance": {
                "exchange": "ai_verdict",
                "routing_key": "system.maintenance",
            },
        },
        task_routes={
            "app.workers.tasks.triage_incident_task": {"queue": "live_triage"},
            "app.workers.tasks.run_policy_simulation_task": {"queue": "simulation_replay"},
        },
    )
except ImportError:
    logger.warning("Celery library is not installed. Background task queue running in in-process mode.")
    celery_app = None


def is_redis_available() -> bool:
    """Verifies active connectivity to Redis broker."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        return bool(r.ping())
    except Exception:
        return False


def get_queue_depth(queue_name: str = "live_triage") -> int:
    """Returns number of pending tasks in Redis queue."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        return r.llen(queue_name)
    except Exception:
        return 0
